# Forecasting System - Quick Start Guide

## What You Have

A complete forecasting system that:
- Loads historical sales data from your database
- Applies advanced smoothing algorithms (peak envelope + exponential smoothing)
- Calculates velocity adjustments based on recent trends
- Generates 52-week forecasts with adjustments
- Calculates inventory requirements (DOI, runout dates, units to make)
- Creates beautiful charts automatically

## Quick Start Commands

### 1. Generate Forecast with Charts (Recommended)
```bash
forecasting/run_forecast_with_charts.bat
```
This will:
- Generate complete forecast for Hydrangea
- Create 4 PNG charts automatically
- Save CSV data files
- Takes ~10 seconds

### 2. Generate Forecast Only (No Charts)
```bash
forecasting/run_forecast.bat
```
Faster, only generates CSV files.

### 3. Command Line (Any Product)
```bash
# With charts
python forecasting/visualize.py --asin YOUR_ASIN --start-date 2024-05-01

# Without charts (faster)
python forecasting/generate_forecast.py --asin YOUR_ASIN --start-date 2024-05-01
```

## Output Files

All files saved to: `forecasting/output/`

### CSV Files
- `historical_*.csv` - Historical sales with smoothing calculations
- `forecast_*.csv` - 52-week future forecast (base + adjusted)
- `inventory_plan_*.csv` - DOI, runout dates, units to make

### Chart Files (PNG)
1. **sales_forecast_*.png** - Main forecast chart
   - Historical actual sales
   - Smoothed historical trend
   - 52-week future forecast (base and adjusted)

2. **smoothing_detail_*.png** - Detailed smoothing components
   - Peak envelope calculations
   - Smooth envelope calculations
   - Final smoothed curves
   - Separate panels for sales and search volume

3. **inventory_plan_*.png** - Inventory planning
   - Cumulative forecast
   - Current inventory levels
   - Runout dates marked
   - Weekly forecast breakdown

4. **inventory_breakdown_*.png** - Current inventory pie chart
   - Available FBA
   - Reserved FBA
   - Inbound FBA
   - Researching/AWD

## Understanding Your Forecast

### Current Results for Hydrangea (B0C73TDZCQ)

**Historical Data:**
- 78 weeks of sales (May 2024 - Nov 2025)
- Total units sold: 32,753
- 20 weeks of traffic data

**Velocity Adjustments:**
- Sales Velocity: -85.06% (declining trend)
- Search Volume Velocity: +14.34% (increasing interest)
- **Net Adjustment: -19.11%** (forecast reduced due to sales decline)

**Forecast:**
- Base forecast: 79.3 units/week average
- **Adjusted forecast: 64.1 units/week** (after velocity adjustment)
- 52 weeks ahead

**Inventory Status:**
- Current inventory: 2,392,331 units
- Available FBA: 2,392,267 units
- **Runout date: Nov 16, 2026**
- **Days of inventory: 363 days**
- Units to make: 0 (inventory exceeds DOI goal)

## Customizing Settings

### Edit Forecast Settings
```bash
python forecasting/edit_settings.py
```

**Editable Settings:**
- Amazon DOI Goal (default: 120 days)
- Inbound Lead Time (default: 30 days)
- Manufacture Lead Time (default: 7 days)
- Market Adjustment (default: 0%, can adjust up/down)
- Sales Velocity Weight (default: 0.25)
- Search Volume Velocity Weight (default: 0.15)
- Forecast Horizon (default: 52 weeks)

**To increase forecast sensitivity to recent trends:**
- Increase `sales_velocity_weight` (e.g., 0.35)
- Decrease `smoothing_window` (e.g., 2 weeks)

**To add manual market adjustment:**
- Set `market_adjustment` to 0.10 for +10% forecast
- Set to -0.10 for -10% forecast (e.g., expected market decline)

### View Current Settings
```bash
python forecasting/edit_settings.py --show
```

## Forecast Formula Breakdown

### Step 1: Smoothing
```
1. Peak Envelope = rolling_max(sales, 3 weeks)
2. Smooth Envelope = rolling_mean(sales, 3 weeks)
3. Final Curve = max(peak_envelope, smooth_envelope)
4. Final Smooth = exponential_moving_average(final_curve, alpha=0.3)
```

### Step 2: Velocity Adjustments
```
Sales Velocity = (recent_12_week_avg - overall_avg) / overall_avg
Search Volume Velocity = (recent_12_week_sv - overall_sv) / overall_sv

Weighted Adjustment = 
  (sales_velocity × 0.25) + 
  (sv_velocity × 0.15) + 
  market_adjustment
```

### Step 3: Final Forecast
```
Adjusted Forecast = Base Forecast × (1 + Weighted Adjustment)
```

### Step 4: Inventory Planning
```
DOI = Current Inventory / (Forecast Per Day)
Runout Date = Today + DOI
Units to Make = Forecast(DOI Goal + Lead Time) - Current Inventory
```

## Forecasting for Other Products

```bash
# By ASIN
python forecasting/visualize.py --asin B0XXXXXXXXX --start-date 2024-01-01

# By SKU
python forecasting/visualize.py --sku YOUR-SKU-HERE --start-date 2024-01-01
```

## Troubleshooting

**No data found:**
- Check ASIN exists in database: `python scripts/db_summary.py`
- Verify start date has data
- Check that `order_items` table has data for that ASIN

**Forecast looks wrong:**
- Review velocity adjustments in output
- Check if recent sales are anomalous (promo, stockout, etc.)
- Adjust settings to reduce weight of recent trends
- Add manual market adjustment

**Charts not generating:**
- Ensure matplotlib is installed: `pip install matplotlib`
- Use `--no-show` flag to save without displaying
- Check `forecasting/output/` for PNG files

**High inventory warning:**
- Your DOI exceeds goal (good problem to have!)
- Consider reducing orders
- Review if inventory data is correct
- Check for duplicate inventory entries

## Advanced: Python API

```python
from forecasting.generate_forecast import ForecastGenerator
from forecasting.settings import ForecastSettings

# Custom settings
settings = ForecastSettings(
    amazon_doi_goal=90,
    market_adjustment=0.15  # Expect 15% growth
)

# Generate forecast
gen = ForecastGenerator(asin='B0C73TDZCQ', settings=settings)
hist_df, forecast_df, plan = gen.generate(start_date='2024-05-01')

# Access results
print(f"Average forecast: {forecast_df['forecast_adjusted'].mean():.0f} units/week")
print(f"Units to make: {plan['units_to_make']:,.0f}")
print(f"Runout date: {plan['runout_date_total']}")

# Export to Excel
import pandas as pd
with pd.ExcelWriter('my_forecast.xlsx') as writer:
    hist_df.to_excel(writer, sheet_name='Historical', index=False)
    forecast_df.to_excel(writer, sheet_name='Forecast', index=False)
```

## Files Structure

```
forecasting/
├── __init__.py
├── settings.py              # Settings management
├── engine.py                # Core forecasting algorithms
├── data_loader.py           # Database data loading
├── generate_forecast.py     # Main forecast generator
├── visualize.py             # Chart generation
├── edit_settings.py         # Interactive settings editor
├── settings.json            # Your saved settings
├── output/                  # Generated files
│   ├── *.csv               # Data files
│   └── *.png               # Chart images
├── run_forecast.bat         # Quick start (CSV only)
├── run_forecast_with_charts.bat  # Quick start (with charts)
└── README.md               # Full documentation
```

## Next Steps

1. ✅ Review generated charts in `forecasting/output/`
2. ✅ Check if forecast makes sense for your business
3. ✅ Adjust settings if needed (`python forecasting/edit_settings.py`)
4. ✅ Set up scheduled task to run weekly
5. ✅ Export to Excel and share with team

## Support

- Full documentation: `forecasting/README.md`
- Check database: `python scripts/db_summary.py`
- Test components: `python forecasting/engine.py`

---

**Built with data-driven forecasting for Amazon sellers!**


