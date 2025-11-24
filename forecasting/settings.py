"""
Forecasting Settings - All editable parameters
"""
from dataclasses import dataclass, field
from typing import Dict, Any
import json
from pathlib import Path


@dataclass
class ForecastSettings:
    """Editable forecast settings matching Forecast Test.xlsx"""
    
    # Lead Times
    amazon_doi_goal: float = 120.0  # Days of Inventory goal on Amazon
    inbound_lead_time: float = 30.0  # Days to ship to Amazon
    manufacture_lead_time: float = 7.0  # Days to manufacture
    
    # Adjustments
    market_adjustment: float = 0.0  # Manual market adjustment (%)
    
    # Velocity Adjustment Weights
    sales_velocity_weight: float = 0.25  # Weight for sales velocity adjustment
    search_volume_velocity_weight: float = 0.15  # Weight for search volume adjustment
    
    # Smoothing Parameters
    peak_envelope_window: int = 3  # Window for peak envelope (weeks)
    smooth_envelope_window: int = 3  # Window for smoothed envelope (weeks)
    
    # Forecast Horizon
    forecast_weeks_ahead: int = 52  # How many weeks to forecast ahead (max 104 for 2 years)
    
    # Seasonality
    seasonality_lag_weeks: int = 52  # Weeks to look back for seasonal baseline (column G)
    
    @property
    def total_lead_time(self) -> float:
        """Total lead time in days"""
        return self.inbound_lead_time + self.manufacture_lead_time
    
    @property
    def total_doi_with_lead_time(self) -> float:
        """Total DOI goal + lead time"""
        return self.amazon_doi_goal + self.total_lead_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'amazon_doi_goal': self.amazon_doi_goal,
            'inbound_lead_time': self.inbound_lead_time,
            'manufacture_lead_time': self.manufacture_lead_time,
            'total_lead_time': self.total_lead_time,
            'market_adjustment': self.market_adjustment,
            'sales_velocity_weight': self.sales_velocity_weight,
            'search_volume_velocity_weight': self.search_volume_velocity_weight,
            'peak_envelope_window': self.peak_envelope_window,
            'smooth_envelope_window': self.smooth_envelope_window,
            'forecast_weeks_ahead': self.forecast_weeks_ahead,
            'seasonality_lag_weeks': self.seasonality_lag_weeks,
        }
    
    def save(self, filepath: str = 'forecasting/settings.json'):
        """Save settings to JSON file"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        print(f"[OK] Settings saved to {filepath}")
    
    @classmethod
    def load(cls, filepath: str = 'forecasting/settings.json') -> 'ForecastSettings':
        """Load settings from JSON file"""
        if not Path(filepath).exists():
            print(f"[WARN] No settings file found at {filepath}, using defaults")
            return cls()
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Remove computed properties
        data.pop('total_lead_time', None)
        
        settings = cls(**data)
        print(f"[OK] Settings loaded from {filepath}")
        return settings


# Global settings instance
settings = ForecastSettings()


if __name__ == '__main__':
    # Test settings
    print("Default Settings:")
    print("-" * 50)
    for key, value in settings.to_dict().items():
        print(f"{key:40s}: {value}")
    
    # Save default settings
    settings.save()

