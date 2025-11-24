"""
Core Forecasting Engine - Implements EXACT Excel formulas from Forecast Test.xlsx
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple
import sys
from pathlib import Path

# Add parent directory to path for imports
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from forecasting.settings import ForecastSettings
else:
    from .settings import ForecastSettings


class ForecastEngine:
    """
    Implements the EXACT forecasting algorithms from Forecast Test.xlsx
    
    Excel Formula Mapping:
    - Peak Envelope: =MAX(OFFSET(B10,-2,0,5)) - looks 2 before, current, 2 after
    - Smooth Envelope: =AVERAGE(OFFSET(C10,-1,0,3)) - looks 1 before, current, 1 after  
    - Final Curve: =MAX(B10,C10,D10) - max of actual, peak, smooth
    - Final Smooth: Weighted average with weights [1,2,4,7,11,13,11,7,4,2,1] (11-point symmetric)
    - Forecast: Continues the pattern using final smooth as baseline
    """
    
    def __init__(self, settings: Optional[ForecastSettings] = None):
        self.settings = settings or ForecastSettings()
        
        # Weighted moving average weights (from Excel F10 formula)
        # Positions: -5, -4, -3, -2, -1, 0, +1, +2, +3, +4, +5
        self.wma_weights = np.array([1, 2, 4, 7, 11, 13, 11, 7, 4, 2, 1])
        
        # Forecast baseline smoothing weights (column I in Excel)
        # Positions: -3, -2, -1, 0, +1, +2, +3
        self.forecast_wma_weights = np.array([1, 3, 5, 7, 5, 3, 1])
    
    def calculate_peak_envelope(self, series: pd.Series, combined_data: bool = False) -> pd.Series:
        """
        Calculate peak envelope - EXACT Excel formula
        
        Excel: =MAX(OFFSET(B10,-2,0,5))
        Looks at 5 values: 2 before, current, 2 after
        
        Args:
            series: Input series
            combined_data: If True, series contains both historical and forecast
        """
        result = []
        values = series.values
        
        for i in range(len(values)):
            # Window: 2 before, current, 2 after (5 total)
            start_idx = max(0, i - 2)
            end_idx = min(len(values), i + 3)  # +3 because range is exclusive
            
            window_vals = values[start_idx:end_idx]
            if len(window_vals) > 0:
                result.append(np.max(window_vals))
            else:
                result.append(np.nan)
        
        return pd.Series(result, index=series.index)
    
    def calculate_smooth_envelope(self, peak_series: pd.Series) -> pd.Series:
        """
        Calculate smoothed envelope - EXACT Excel formula
        
        Excel: =AVERAGE(OFFSET(C10,-1,0,3))
        Looks at 3 values: 1 before, current, 1 after
        """
        result = []
        values = peak_series.values
        
        for i in range(len(values)):
            # Window: 1 before, current, 1 after (3 total)
            start_idx = max(0, i - 1)
            end_idx = min(len(values), i + 2)  # +2 because range is exclusive
            
            window_vals = values[start_idx:end_idx]
            if len(window_vals) > 0:
                result.append(np.mean(window_vals))
            else:
                result.append(np.nan)
        
        return pd.Series(result, index=peak_series.index)
    
    def calculate_final_curve(self, units: pd.Series, peak_env: pd.Series, 
                             smooth_env: pd.Series) -> pd.Series:
        """
        Calculate final curve - EXACT Excel formula
        
        Excel: =MAX(B10,C10,D10)
        Takes max of actual, peak envelope, smooth envelope
        """
        return pd.DataFrame({
            'units': units,
            'peak': peak_env,
            'smooth': smooth_env
        }).max(axis=1)
    
    def calculate_final_smooth(self, final_curve: pd.Series) -> pd.Series:
        """
        Calculate final smooth - EXACT Excel formula (11-point weighted moving average)
        
        Excel F10: Weighted average with weights [1,2,4,7,11,13,11,7,4,2,1]
        Positions: -5, -4, -3, -2, -1, 0, +1, +2, +3, +4, +5
        
        This is a SYMMETRIC weighted moving average, NOT exponential smoothing!
        """
        result = []
        values = final_curve.values
        weights = self.wma_weights
        
        for i in range(len(values)):
            # Window: 5 before, current, 5 after (11 total)
            start_idx = i - 5
            end_idx = i + 6  # +6 because range is exclusive
            
            # Get available values and corresponding weights
            available_values = []
            available_weights = []
            
            for j, w in zip(range(start_idx, end_idx), weights):
                if 0 <= j < len(values) and not np.isnan(values[j]):
                    available_values.append(values[j])
                    available_weights.append(w)
            
            if len(available_values) > 0:
                # Weighted average
                weighted_sum = sum(v * w for v, w in zip(available_values, available_weights))
                weight_sum = sum(available_weights)
                result.append(weighted_sum / weight_sum)
            else:
                result.append(np.nan)
        
        return pd.Series(result, index=final_curve.index)
    
    def calculate_velocity_adjustment(self, values: pd.Series, 
                                     lookback_weeks: int = 12) -> float:
        """
        Calculate velocity adjustment - trend over recent weeks
        
        Formula: (last_value - avg_of_lookback) / avg_of_lookback
        
        Returns:
            Multiplier adjustment (e.g., -0.096 means -9.6% decline)
        """
        if len(values) < 2:
            return 0.0
        
        # Get last N weeks
        recent = values.tail(lookback_weeks)
        recent = recent.dropna()
        
        if len(recent) < 2:
            return 0.0
        
        last_value = recent.iloc[-1]
        avg_value = recent.mean()
        
        if avg_value == 0:
            return 0.0
        
        # Calculate percentage change
        velocity = (last_value - avg_value) / avg_value
        
        return velocity
    
    def build_seasonal_baseline(self, final_smooth: pd.Series,
                                lag_weeks: int = 52) -> pd.Series:
        """
        Build seasonal baseline by referencing values lag_weeks in the past
        
        Matches Excel column G (forecast) which references F row - 52
        """
        baseline = pd.Series(np.nan, index=final_smooth.index, dtype=float)
        
        if len(final_smooth) <= lag_weeks:
            return baseline
        
        baseline.iloc[lag_weeks:] = final_smooth.iloc[:-lag_weeks].values
        return baseline
    
    def calculate_forecast_peak_envelope(self, baseline: pd.Series) -> pd.Series:
        """
        Calculate forecast peak envelope (Excel column H)
        
        Excel: =IFERROR(MAX(OFFSET($Gn,-2,0,2)),"0")
        Uses the two prior rows of the seasonal baseline.
        """
        peak = baseline.shift(1).rolling(window=2, min_periods=1).max()
        return peak.fillna(0.0)
    
    def calculate_forecast_final_smooth(self, forecast_peak: pd.Series) -> pd.Series:
        """
        Calculate forecast final smooth (Excel column I)
        
        Weighted moving average with weights [1,3,5,7,5,3,1]
        """
        values = forecast_peak.values
        weights = self.forecast_wma_weights
        radius = len(weights) // 2
        result = []
        
        for i in range(len(values)):
            available_values = []
            available_weights = []
            
            for offset, weight in zip(range(-radius, radius + 1), weights):
                idx = i + offset
                if 0 <= idx < len(values) and not np.isnan(values[idx]):
                    available_values.append(values[idx])
                    available_weights.append(weight)
            
            if available_values:
                weighted_sum = sum(v * w for v, w in zip(available_values, available_weights))
                weight_sum = sum(available_weights)
                result.append(weighted_sum / weight_sum if weight_sum else np.nan)
            else:
                result.append(np.nan)
        
        return pd.Series(result, index=forecast_peak.index)
    
    def calculate_sales_velocity_ratio(self, actual_smooth: pd.Series,
                                       baseline_smooth: pd.Series) -> float:
        """
        Calculate sales velocity adjustment using Excel's new ratio:
        (weighted avg of actual final smooth) / (weighted avg of seasonal baseline) - 1
        """
        combined = pd.DataFrame({
            'actual': actual_smooth,
            'baseline': baseline_smooth
        }).dropna()
        
        if len(combined) < 6:
            return 0.0
        
        tail = combined.tail(6)
        numerator = self._weighted_daily_average(tail['actual'])
        denominator = self._weighted_daily_average(tail['baseline'])
        
        if numerator is None or denominator is None or denominator == 0:
            return 0.0
        
        return (numerator / denominator) - 1
    
    def _weighted_daily_average(self, series: pd.Series) -> Optional[float]:
        """
        Apply Excel's 1/2/4/6-week weighted daily average calculation
        """
        windows = [1, 2, 4, 6]
        totals = []
        
        for weeks in windows:
            if len(series) >= weeks:
                window_sum = series.tail(weeks).sum()
                totals.append(window_sum / (7 * weeks))
            else:
                return None
        
        return 0.25 * sum(totals)
    
    def apply_adjustments(self, forecast: pd.Series,
                         sales_velocity_adj: float,
                         sv_velocity_adj: float) -> pd.Series:
        """
        Apply velocity adjustments to forecast
        
        Formula: forecast * (1 + weighted_adjustments + market_adj)
        """
        # Weighted adjustments
        sales_weighted = sales_velocity_adj * self.settings.sales_velocity_weight
        sv_weighted = sv_velocity_adj * self.settings.search_volume_velocity_weight
        market_adj = self.settings.market_adjustment
        
        # Total multiplier
        total_adjustment = 1.0 + sales_weighted + sv_weighted + market_adj
        
        # Apply to forecast
        adjusted = forecast * total_adjustment
        
        return adjusted
    
    def generate_forecast_continuation(self, combined_series: pd.Series, 
                                      historical_length: int) -> pd.Series:
        """
        Generate forecast by continuing the smoothed pattern
        
        The forecast is the continuation of the final_smooth values,
        which will be smoothed again with the same weighted average
        """
        # For now, use the last smoothed value as baseline
        # The seasonality will be applied during the full smoothing pass
        historical_smooth = combined_series.iloc[:historical_length]
        last_value = historical_smooth.dropna().iloc[-1] if len(historical_smooth.dropna()) > 0 else 0
        
        # Generate forecast values (will be smoothed in full pass)
        forecast_length = len(combined_series) - historical_length
        forecast_values = [last_value] * forecast_length
        
        return pd.Series(forecast_values, index=combined_series.index[historical_length:])
    
    def calculate_cumulative_forecast(self, forecast: pd.Series,
                                     start_date: Optional[datetime] = None) -> pd.Series:
        """
        Calculate cumulative forecast from start_date forward
        
        Used for inventory planning
        """
        if start_date is None:
            start_date = datetime.now()
        
        # Filter to future dates
        future_forecast = forecast[forecast.index >= pd.Timestamp(start_date)]
        
        # Calculate cumulative sum
        cumulative = future_forecast.cumsum()
        
        return cumulative
    
    def calculate_runout_date(self, current_inventory: float,
                             forecast: pd.Series,
                             start_date: Optional[datetime] = None) -> Tuple[datetime, float]:
        """
        Calculate exact runout date based on inventory and forecast
        
        Returns:
            (runout_date, days_of_inventory)
        
        Algorithm (from Excel):
        1. Find week where cumulative >= inventory
        2. Calculate fraction of week before runout
        3. Return exact date = week_start + (fraction * 7 days)
        """
        if start_date is None:
            start_date = datetime.now()
        
        # Get cumulative forecast
        cumulative = self.calculate_cumulative_forecast(forecast, start_date)
        
        if len(cumulative) == 0 or current_inventory <= 0:
            return start_date, 0.0
        
        # Find first week where cumulative >= inventory
        runout_idx = cumulative[cumulative >= current_inventory].index
        
        if len(runout_idx) == 0:
            # Inventory lasts beyond forecast horizon
            last_date = cumulative.index[-1]
            doi = (last_date - pd.Timestamp(start_date)).days
            return last_date, doi
        
        runout_week = runout_idx[0]
        runout_week_idx = cumulative.index.get_loc(runout_week)
        
        # Get cumulative before and at runout week
        cum_at_runout = cumulative.iloc[runout_week_idx]
        cum_before = cumulative.iloc[runout_week_idx - 1] if runout_week_idx > 0 else 0
        
        # Calculate units needed within the week
        remaining = current_inventory - cum_before
        week_units = cum_at_runout - cum_before
        
        # Fraction of week before runout
        fraction = remaining / week_units if week_units > 0 else 0
        
        # Calculate exact runout date
        week_end = runout_week
        week_start = week_end - timedelta(days=7)
        runout_date = week_start + timedelta(days=fraction * 7)
        
        # Calculate DOI
        doi = (runout_date - pd.Timestamp(start_date)).days
        
        return runout_date, doi
    
    def calculate_units_to_make(self, current_inventory: float,
                               adjusted_forecast: pd.Series,
                               start_date: Optional[datetime] = None) -> float:
        """
        Calculate how many units to manufacture
        
        Formula:
        1. Calculate total units needed for (DOI_goal + lead_time) days
        2. Subtract current inventory
        3. Return max(0, result)
        """
        if start_date is None:
            start_date = datetime.now()
        
        # Calculate target date (today + DOI goal + lead time)
        target_days = self.settings.total_doi_with_lead_time
        target_date = start_date + timedelta(days=target_days)
        
        # Get cumulative forecast from now to target date
        future_forecast = adjusted_forecast[adjusted_forecast.index >= pd.Timestamp(start_date)]
        future_forecast = future_forecast[future_forecast.index <= pd.Timestamp(target_date)]
        
        if len(future_forecast) == 0:
            return 0.0
        
        # Handle partial week at the end
        last_week_end = future_forecast.index[-1]
        
        if last_week_end < pd.Timestamp(target_date):
            # Need to pro-rate the last week
            extra_days = (pd.Timestamp(target_date) - last_week_end).days
            last_week_units = future_forecast.iloc[-1]
            partial_units = (extra_days / 7.0) * last_week_units
            
            # Sum of full weeks + partial week
            full_weeks_sum = future_forecast.iloc[:-1].sum() if len(future_forecast) > 1 else 0
            total_needed = full_weeks_sum + last_week_units + partial_units
        else:
            total_needed = future_forecast.sum()
        
        # Subtract current inventory
        units_to_make = total_needed - current_inventory
        
        # Can't make negative units
        return max(0.0, units_to_make)


if __name__ == '__main__':
    # Test the engine
    print("Testing Forecast Engine with EXACT Excel formulas...")
    print("=" * 60)
    
    # Create sample data matching Excel
    dates = pd.date_range('2024-01-01', periods=20, freq='7D')
    units = pd.Series([24, 28, 43, 50, 53, 41, 5, 117, 144, 150, 
                       145, 137, 27, 1, 1, 129, 147, 247, 247, 294], index=dates)
    
    # Initialize engine
    engine = ForecastEngine()
    
    # Test calculations (need to combine with forecast first for forward-looking)
    # Extend series with forecast placeholder
    future_dates = pd.date_range(dates[-1] + timedelta(days=7), periods=12, freq='7D')
    forecast_placeholder = pd.Series([150] * 12, index=future_dates)
    combined = pd.concat([units, forecast_placeholder])
    
    print("\nCalculating with forward-looking formulas...")
    peak_env = engine.calculate_peak_envelope(combined)
    smooth_env = engine.calculate_smooth_envelope(peak_env)
    final_curve = engine.calculate_final_curve(combined, peak_env, smooth_env)
    final_smooth = engine.calculate_final_smooth(final_curve)
    
    print("\nSample Results (first 10 weeks):")
    print("-" * 60)
    df = pd.DataFrame({
        'date': combined.index[:10],
        'units': combined.values[:10],
        'peak_env': peak_env.values[:10],
        'smooth_env': smooth_env.values[:10],
        'final_smooth': final_smooth.values[:10]
    })
    print(df.to_string(index=False))
    
    # Test velocity adjustment
    velocity = engine.calculate_velocity_adjustment(units)
    print(f"\nVelocity Adjustment: {velocity:.4f} ({velocity*100:.2f}%)")
    
    print("\n[OK] Engine tests complete!")
