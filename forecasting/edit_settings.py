"""
Interactive Settings Editor
"""
from forecasting.settings import ForecastSettings


def edit_settings_interactive():
    """Interactive command-line settings editor"""
    
    # Load current settings
    settings = ForecastSettings.load()
    
    print("\n" + "=" * 70)
    print("  FORECAST SETTINGS EDITOR")
    print("=" * 70)
    
    print("\nCurrent Settings:")
    print("-" * 70)
    for key, value in settings.to_dict().items():
        print(f"  {key:40s}: {value}")
    
    print("\n" + "=" * 70)
    print("Edit settings below (press Enter to keep current value)")
    print("=" * 70)
    
    # Edit each setting
    def get_float_input(prompt: str, current: float) -> float:
        while True:
            response = input(f"\n{prompt}\n  Current: {current}\n  New value: ").strip()
            if not response:
                return current
            try:
                return float(response)
            except ValueError:
                print("   Invalid number, try again")
    
    def get_int_input(prompt: str, current: int) -> int:
        while True:
            response = input(f"\n{prompt}\n  Current: {current}\n  New value: ").strip()
            if not response:
                return current
            try:
                return int(response)
            except ValueError:
                print("   Invalid number, try again")
    
    # Lead Times
    print("\n" + "-" * 70)
    print(" LEAD TIMES")
    print("-" * 70)
    
    settings.amazon_doi_goal = get_float_input(
        "Amazon DOI Goal (days of inventory to maintain):",
        settings.amazon_doi_goal
    )
    
    settings.inbound_lead_time = get_float_input(
        "Inbound Lead Time (days to ship to Amazon FBA):",
        settings.inbound_lead_time
    )
    
    settings.manufacture_lead_time = get_float_input(
        "Manufacture Lead Time (days to produce):",
        settings.manufacture_lead_time
    )
    
    # Adjustments
    print("\n" + "-" * 70)
    print(" ADJUSTMENTS")
    print("-" * 70)
    
    settings.market_adjustment = get_float_input(
        "Market Adjustment (manual adjustment, e.g., 0.10 for +10%):",
        settings.market_adjustment
    )
    
    # Velocity Weights
    print("\n" + "-" * 70)
    print("  VELOCITY WEIGHTS")
    print("-" * 70)
    
    settings.sales_velocity_weight = get_float_input(
        "Sales Velocity Weight (0.0 to 1.0):",
        settings.sales_velocity_weight
    )
    
    settings.search_volume_velocity_weight = get_float_input(
        "Search Volume Velocity Weight (0.0 to 1.0):",
        settings.search_volume_velocity_weight
    )
    
    # Smoothing
    print("\n" + "-" * 70)
    print(" SMOOTHING PARAMETERS")
    print("-" * 70)
    
    settings.peak_envelope_window = get_int_input(
        "Peak Envelope Window (weeks):",
        settings.peak_envelope_window
    )
    
    settings.smooth_envelope_window = get_int_input(
        "Smooth Envelope Window (weeks):",
        settings.smooth_envelope_window
    )
    
    # Forecast Horizon
    print("\n" + "-" * 70)
    print(" FORECAST HORIZON")
    print("-" * 70)
    
    settings.forecast_weeks_ahead = get_int_input(
        "Forecast Weeks Ahead:",
        settings.forecast_weeks_ahead
    )
    
    # Summary
    print("\n" + "=" * 70)
    print(" NEW SETTINGS SUMMARY")
    print("=" * 70)
    for key, value in settings.to_dict().items():
        print(f"  {key:40s}: {value}")
    
    # Confirm
    print("\n" + "=" * 70)
    response = input("Save these settings? (y/n): ").strip().lower()
    
    if response == 'y':
        settings.save()
        print("\n Settings saved successfully!")
    else:
        print("\n Settings not saved")
    
    return settings


def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--show':
        # Just show current settings
        settings = ForecastSettings.load()
        print("\nCurrent Settings:")
        print("-" * 70)
        for key, value in settings.to_dict().items():
            print(f"  {key:40s}: {value}")
    else:
        # Interactive edit
        edit_settings_interactive()


if __name__ == '__main__':
    main()


