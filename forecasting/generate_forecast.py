"""
Main Forecast Generator - Generates complete forecast with all components
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Tuple
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from forecasting.settings import ForecastSettings
from forecasting.engine import ForecastEngine
from forecasting.data_loader import ForecastDataLoader


class ForecastGenerator:
    """
    Main forecast generator that orchestrates the entire forecasting process
    """
    
    def __init__(self, asin: Optional[str] = None, sku: Optional[str] = None,
                 settings: Optional[ForecastSettings] = None):
        """
        Initialize forecast generator
        
        Args:
            asin: Product ASIN to forecast
            sku: Product SKU to forecast
            settings: Forecast settings (uses defaults if not provided)
        """
        self.asin = asin
        self.sku = sku
        self.settings = settings or ForecastSettings.load()
        self.engine = ForecastEngine(self.settings)
        self.loader = ForecastDataLoader(asin=asin, sku=sku)
        self.velocity_adjustments = None
        
        # Results storage
        self.historical_df = None
        self.forecast_df = None
        self.inventory_plan = None
        self.product_info = None
    
    def load_historical_data(self, start_date: Optional[str] = None) -> pd.DataFrame:
        """
        Load and process historical data
        
        Returns:
            DataFrame with historical sales, traffic, and calculated fields
        """
        print("\n" + "=" * 70)
        print(" LOADING HISTORICAL DATA")
        print("=" * 70)
        
        # Load product info
        self.product_info = self.loader.get_product_info()
        print(f"\nProduct: {self.product_info.get('title', 'Unknown')[:60]}")
        print(f"ASIN: {self.product_info['asin']}")
        
        # Load sales data
        print("\n" + "-" * 70)
        sales = self.loader.load_weekly_sales(start_date=start_date)
        
        if len(sales) == 0:
            raise ValueError("No sales data found! Cannot generate forecast.")
        
        # Load search volume (proxy from sessions)
        print("\n" + "-" * 70)
        search_vol = self.loader.load_search_volume(
            search_terms=[],  # Placeholder
            start_date=start_date
        )
        
        # Merge data
        df = sales.copy()
        
        if len(search_vol) > 0:
            df = df.merge(search_vol, on='week_end', how='left')
        else:
            df['search_volume'] = np.nan
        
        # Fill missing weeks
        date_range = pd.date_range(
            start=df['week_end'].min(),
            end=df['week_end'].max(),
            freq='7D'
        )
        df = df.set_index('week_end').reindex(date_range).reset_index()
        df.rename(columns={'index': 'week_end'}, inplace=True)
        df['units_sold'].fillna(0, inplace=True)
        df['search_volume'].fillna(0, inplace=True)
        
        print(f"\n Historical data prepared: {len(df)} weeks")
        
        return df
    
    def calculate_smoothed_curves(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all smoothed curves using EXACT Excel formulas
        
        Key: Excel formulas look FORWARD and BACKWARD, so we need to:
        1. Generate placeholder forecast first
        2. Combine historical + forecast
        3. Apply smoothing to entire combined series
        4. This gives proper forward-looking smoothing for historical data
        
        Adds columns:
        - units_peak_env, units_smooth_env, units_final_curve, units_final_smooth
        - sv_peak_env, sv_smooth_env, sv_final_curve, sv_final_smooth
        """
        print("\n" + "=" * 70)
        print(" CALCULATING SMOOTHED CURVES (Excel-accurate forward-looking)")
        print("=" * 70)
        
        # Calculate baseline for forecast (use average of recent smoothed, not last value)
        recent_smooth_units = df['units_sold'].dropna().tail(26)  # Last 6 months
        baseline_units = recent_smooth_units.mean() if len(recent_smooth_units) > 0 else 0
        
        recent_smooth_sv = df['search_volume'].dropna().tail(26)
        baseline_sv = recent_smooth_sv.mean() if len(recent_smooth_sv) > 0 else 0
        
        # Create extended series with seasonal forecast pattern
        future_dates = pd.date_range(
            df['week_end'].max() + timedelta(days=7),
            periods=self.settings.forecast_weeks_ahead,
            freq='7D'
        )
        
        # Generate seasonal forecast pattern (repeat historical pattern)
        hist_units = df['units_sold'].dropna()
        hist_sv = df['search_volume'].dropna()
        
        if len(hist_units) >= 13:
            # Use last year's pattern (52 weeks or available)
            seasonal_period = min(52, len(hist_units))
            seasonal_units = hist_units.iloc[-seasonal_period:].values
            seasonal_sv = hist_sv.iloc[-seasonal_period:].values if len(hist_sv) >= seasonal_period else hist_sv.values
            
            # Normalize to get seasonal factors
            avg_units = seasonal_units.mean()
            avg_sv = seasonal_sv.mean()
            
            if avg_units > 0:
                seasonal_factors_units = seasonal_units / avg_units
            else:
                seasonal_factors_units = np.ones(len(seasonal_units))
            
            if avg_sv > 0:
                seasonal_factors_sv = seasonal_sv / avg_sv
            else:
                seasonal_factors_sv = np.ones(len(seasonal_sv))
            
            # Extend pattern to forecast period (repeat the cycle)
            num_cycles = int(np.ceil(len(future_dates) / len(seasonal_factors_units)))
            extended_factors_units = np.tile(seasonal_factors_units, num_cycles)[:len(future_dates)]
            extended_factors_sv = np.tile(seasonal_factors_sv, num_cycles)[:len(future_dates)]
            
            # Apply seasonal pattern to baseline
            forecast_placeholder_units = pd.Series(baseline_units * extended_factors_units, index=future_dates)
            forecast_placeholder_sv = pd.Series(baseline_sv * extended_factors_sv, index=future_dates)
        else:
            # Not enough data for seasonality, use baseline
            forecast_placeholder_units = pd.Series([baseline_units] * len(future_dates), index=future_dates)
            forecast_placeholder_sv = pd.Series([baseline_sv] * len(future_dates), index=future_dates)
        
        # Combine historical + placeholder
        combined_units = pd.concat([df.set_index('week_end')['units_sold'], forecast_placeholder_units])
        combined_sv = pd.concat([df.set_index('week_end')['search_volume'], forecast_placeholder_sv])
        
        print(f"\nProcessing {len(df)} historical + {len(future_dates)} forecast weeks...")
        print("  (Forward-looking smoothing requires future values)")
        
        # Sales smoothing on combined series
        print("\nProcessing sales data...")
        units_peak_env = self.engine.calculate_peak_envelope(combined_units, combined_data=True)
        units_smooth_env = self.engine.calculate_smooth_envelope(units_peak_env)
        units_final_curve = self.engine.calculate_final_curve(combined_units, units_peak_env, units_smooth_env)
        units_final_smooth = self.engine.calculate_final_smooth(units_final_curve)
        
        # Search volume smoothing on combined series
        print("Processing search volume data...")
        sv_peak_env = self.engine.calculate_peak_envelope(combined_sv, combined_data=True)
        sv_smooth_env = self.engine.calculate_smooth_envelope(sv_peak_env)
        sv_final_curve = self.engine.calculate_final_curve(combined_sv, sv_peak_env, sv_smooth_env)
        sv_final_smooth = self.engine.calculate_final_smooth(sv_final_curve)
        
        # Extract historical portion only (forecast will be recalculated)
        hist_length = len(df)
        df['units_peak_env'] = units_peak_env.iloc[:hist_length].values
        df['units_smooth_env'] = units_smooth_env.iloc[:hist_length].values
        df['units_final_curve'] = units_final_curve.iloc[:hist_length].values
        df['units_final_smooth'] = units_final_smooth.iloc[:hist_length].values
        
        df['sv_peak_env'] = sv_peak_env.iloc[:hist_length].values
        df['sv_smooth_env'] = sv_smooth_env.iloc[:hist_length].values
        df['sv_final_curve'] = sv_final_curve.iloc[:hist_length].values
        df['sv_final_smooth'] = sv_final_smooth.iloc[:hist_length].values
        
        # Store combined smooth for forecast generation
        self._combined_units_smooth = units_final_smooth
        self._combined_sv_smooth = sv_final_smooth
        self._hist_length = hist_length

        # Seasonal baseline (Excel columns G-I) for velocity calc
        lag_weeks = min(self.settings.seasonality_lag_weeks, len(df))
        final_smooth_series = pd.Series(
            df['units_final_smooth'].values,
            index=df.index
        )
        forecast_baseline = self.engine.build_seasonal_baseline(
            final_smooth_series,
            lag_weeks=lag_weeks
        )
        forecast_peak_env = self.engine.calculate_forecast_peak_envelope(forecast_baseline)
        forecast_final_smooth = self.engine.calculate_forecast_final_smooth(forecast_peak_env)
        df['forecast_baseline'] = forecast_baseline.values
        df['forecast_peak_env'] = forecast_peak_env.values
        df['forecast_final_smooth'] = forecast_final_smooth.values
        self._forecast_final_smooth = forecast_final_smooth
        
        print(" Smoothing complete (Excel-accurate)")
        
        return df
    
    def calculate_velocity_adjustments(self, df: pd.DataFrame) -> dict:
        """
        Calculate velocity adjustments
        
        Returns:
            dict with sales_velocity_adj and sv_velocity_adj
        """
        print("\n" + "=" * 70)
        print(" CALCULATING VELOCITY ADJUSTMENTS")
        print("=" * 70)
        
        # Sales velocity (Excel column J ratio)
        sales_velocity = self.engine.calculate_sales_velocity_ratio(
            df['units_final_smooth'],
            df['forecast_final_smooth']
        )
        
        # Search volume velocity
        sv_velocity = self.engine.calculate_velocity_adjustment(
            df['search_volume'],
            lookback_weeks=12
        )
        
        print(f"\nSales Velocity Adjustment: {sales_velocity:+.4f} ({sales_velocity*100:+.2f}%)")
        print(f"  Weight: {self.settings.sales_velocity_weight:.2f}")
        print(f"  Weighted Impact: {sales_velocity * self.settings.sales_velocity_weight:+.4f}")
        
        print(f"\nSearch Volume Velocity Adjustment: {sv_velocity:+.4f} ({sv_velocity*100:+.2f}%)")
        print(f"  Weight: {self.settings.search_volume_velocity_weight:.2f}")
        print(f"  Weighted Impact: {sv_velocity * self.settings.search_volume_velocity_weight:+.4f}")
        
        print(f"\nMarket Adjustment: {self.settings.market_adjustment:+.4f}")
        
        total_adj = (
            sales_velocity * self.settings.sales_velocity_weight +
            sv_velocity * self.settings.search_volume_velocity_weight +
            self.settings.market_adjustment
        )
        print(f"\nTotal Adjustment Multiplier: {total_adj:+.4f} ({total_adj*100:+.2f}%)")
        
        return {
            'sales_velocity_adj': sales_velocity,
            'sv_velocity_adj': sv_velocity,
            'sales_velocity_weighted': sales_velocity * self.settings.sales_velocity_weight,
            'sv_velocity_weighted': sv_velocity * self.settings.search_volume_velocity_weight,
            'total_adjustment': total_adj
        }
    
    def generate_future_forecast(self, df: pd.DataFrame,
                                 velocity_adjustments: dict) -> pd.DataFrame:
        """
        Generate future forecast with adjustments
        
        Returns:
            DataFrame with future forecast
        """
        print("\n" + "=" * 70)
        print(" GENERATING FUTURE FORECAST")
        print("=" * 70)
        
        # Generate base forecast from the combined smooth
        # (Already includes forward-looking smoothing from historical calc)
        forecast_smooth = self._combined_units_smooth.iloc[self._hist_length:]
        base_forecast = forecast_smooth
        
        # Apply adjustments
        adjusted_forecast = self.engine.apply_adjustments(
            base_forecast,
            velocity_adjustments['sales_velocity_adj'],
            velocity_adjustments['sv_velocity_adj']
        )
        
        # Create forecast DataFrame
        forecast_df = pd.DataFrame({
            'week_end': adjusted_forecast.index,
            'forecast_base': base_forecast.values,
            'forecast_adjusted': adjusted_forecast.values,
            'is_forecast': True
        })
        
        print(f"\n Generated {len(forecast_df)} weeks of forecast")
        print(f"   Base forecast avg: {forecast_df['forecast_base'].mean():.1f} units/week")
        print(f"   Adjusted forecast avg: {forecast_df['forecast_adjusted'].mean():.1f} units/week")
        
        return forecast_df
    
    def calculate_inventory_plan(self, forecast_df: pd.DataFrame) -> dict:
        """
        Calculate inventory planning metrics
        
        Returns:
            dict with inventory plan details
        """
        print("\n" + "=" * 70)
        print(" CALCULATING INVENTORY PLAN")
        print("=" * 70)
        
        # Load current inventory
        total_inv, inv_breakdown = self.loader.load_current_inventory()
        
        if total_inv == 0:
            print("  No inventory data available")
            return {
                'current_inventory': 0,
                'inventory_breakdown': {},
                'runout_date': None,
                'doi_total': 0,
                'doi_fba_available': 0,
                'units_to_make': 0
            }
        
        # Create forecast series
        forecast_series = pd.Series(
            forecast_df['forecast_adjusted'].values,
            index=forecast_df['week_end']
        )
        
        # Calculate runout for total inventory
        runout_date_total, doi_total = self.engine.calculate_runout_date(
            total_inv,
            forecast_series
        )
        
        # Calculate runout for available FBA only
        available_fba = inv_breakdown.get('available_fba', 0)
        runout_date_fba, doi_fba = self.engine.calculate_runout_date(
            available_fba,
            forecast_series
        )
        
        # Calculate units to make
        units_to_make = self.engine.calculate_units_to_make(
            total_inv,
            forecast_series
        )
        
        plan = {
            'current_inventory': total_inv,
            'inventory_breakdown': inv_breakdown,
            'runout_date_total': runout_date_total,
            'doi_total': doi_total,
            'runout_date_fba_available': runout_date_fba,
            'doi_fba_available': doi_fba,
            'units_to_make': units_to_make,
            'doi_goal': self.settings.amazon_doi_goal,
            'total_lead_time': self.settings.total_lead_time,
        }
        
        print(f"\n Inventory Summary:")
        print(f"   Total Inventory: {total_inv:,.0f} units")
        print(f"   Available FBA: {available_fba:,.0f} units")
        
        print(f"\n Runout Dates:")
        print(f"   Total Inventory Runout: {runout_date_total.strftime('%Y-%m-%d')}")
        print(f"   DOI (Total): {doi_total:.1f} days")
        print(f"   FBA Available Runout: {runout_date_fba.strftime('%Y-%m-%d')}")
        print(f"   DOI (FBA Available): {doi_fba:.1f} days")
        
        print(f"\n Manufacturing Plan:")
        print(f"   DOI Goal: {self.settings.amazon_doi_goal:.0f} days")
        print(f"   Lead Time: {self.settings.total_lead_time:.0f} days")
        print(f"   Units to Make: {units_to_make:,.0f} units")
        
        return plan
    
    def generate(self, start_date: Optional[str] = None,
                export_csv: bool = True,
                export_path: Optional[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
        """
        Generate complete forecast
        
        Returns:
            (historical_df, forecast_df, inventory_plan)
        """
        print("\n" + "=" * 70)
        print(" STARTING FORECAST GENERATION")
        print("=" * 70)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 1: Load historical data
        df = self.load_historical_data(start_date)
        
        # Step 2: Calculate smoothed curves
        df = self.calculate_smoothed_curves(df)
        
        # Step 3: Calculate velocity adjustments
        velocity_adj = self.calculate_velocity_adjustments(df)
        self.velocity_adjustments = velocity_adj.copy()
        
        # Store velocity adjustments in df
        for key, value in velocity_adj.items():
            df[key] = value
        
        # Step 4: Generate future forecast
        forecast_df = self.generate_future_forecast(df, velocity_adj)
        
        # Step 5: Calculate inventory plan
        inventory_plan = self.calculate_inventory_plan(forecast_df)
        
        # Store results
        self.historical_df = df
        self.forecast_df = forecast_df
        self.inventory_plan = inventory_plan
        
        # Export if requested
        if export_csv:
            self._export_results(export_path)
        
        print("\n" + "=" * 70)
        print(" FORECAST GENERATION COMPLETE!")
        print("=" * 70)
        
        return df, forecast_df, inventory_plan
    
    def _export_results(self, export_path: Optional[str] = None):
        """Export results to CSV files"""
        if export_path is None:
            export_path = 'forecasting/output'
        
        Path(export_path).mkdir(parents=True, exist_ok=True)
        
        # Generate filename with ASIN and timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        asin = self.asin or self.sku or 'unknown'
        
        # Export historical data
        historical_file = f"{export_path}/historical_{asin}_{timestamp}.csv"
        self.historical_df.to_csv(historical_file, index=False)
        print(f"\n Saved: {historical_file}")
        
        # Export forecast
        forecast_file = f"{export_path}/forecast_{asin}_{timestamp}.csv"
        self.forecast_df.to_csv(forecast_file, index=False)
        print(f" Saved: {forecast_file}")
        
        # Export inventory plan
        plan_file = f"{export_path}/inventory_plan_{asin}_{timestamp}.csv"
        plan_df = pd.DataFrame([self.inventory_plan])
        plan_df.to_csv(plan_file, index=False)
        print(f" Saved: {plan_file}")


def main():
    """Main entry point for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate product forecast')
    parser.add_argument('--asin', type=str, help='Product ASIN to forecast')
    parser.add_argument('--sku', type=str, help='Product SKU to forecast')
    parser.add_argument('--start-date', type=str, help='Start date for historical data (YYYY-MM-DD)')
    parser.add_argument('--no-export', action='store_true', help='Skip CSV export')
    
    args = parser.parse_args()
    
    if not args.asin and not args.sku:
        print(" Error: Must provide either --asin or --sku")
        return
    
    # Generate forecast
    generator = ForecastGenerator(asin=args.asin, sku=args.sku)
    generator.generate(
        start_date=args.start_date,
        export_csv=not args.no_export
    )


if __name__ == '__main__':
    main()

