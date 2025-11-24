# 📈 Forecasting Module

Advanced inventory forecasting system based on Amazon sales data, implementing the methodology from `Forecast Test.xlsx`.

## 🎯 Features

- **Peak Envelope & Smoothing**: Advanced smoothing algorithms to identify trends
- **Velocity Adjustments**: Automatically adjust forecasts based on recent sales velocity and search volume trends
- **Inventory Planning**: Calculate DOI (Days of Inventory), runout dates, and manufacturing requirements
- **Editable Settings**: All parameters are configurable via JSON
- **Interactive Visualizations**: Beautiful charts showing historical data and forecasts
- **Database Integration**: Pulls data directly from your local SQLite database

## 📁 File Structure

```
forecasting/
├── __init__.py                 # Module initialization
├── settings.py                 # Editable forecast settings
├── engine.py                   # Core forecasting algorithms
├── data_loader.py              # Database data loading
├── generate_forecast.py        # Main forecast generator
├── visualize.py                # Chart generation
├── edit_settings.py            # Interactive settings editor
├── settings.json               # Saved settings (auto-generated)
├── output/                     # Generated forecasts and charts
│   ├── historical_*.csv
│   ├── forecast_*.csv
│   ├── inventory_plan_*.csv
│   └── *.png charts
└── README.md                   # This file
```

## 🚀 Quick Start

### 1. Generate Forecast for Hydrangea

```bash
python forecasting/generate_forecast.py --asin B0C73TDZCQ --start-date 2024-05-01
```

This will:
- ✅ Load historical sales data from database
- ✅ Calculate smoothing and velocity adjustments
- ✅ Generate 52-week forecast
- ✅ Calculate inventory requirements
- ✅ Export CSV files to `forecasting/output/`

### 2. Generate Forecast with Charts

```bash
python forecasting/visualize.py --asin B0C73TDZCQ --start-date 2024-05-01
```

This will:
- ✅ Generate complete forecast
- ✅ Create 4 interactive charts
- ✅ Save charts as PNG files
- ✅ Display charts in browser/matplotlib viewer

### 3. Edit Forecast Settings

```bash
python forecasting/edit_settings.py
```

Editable settings:
- Amazon DOI Goal (default: 120 days)
- Inbound Lead Time (default: 30 days)
- Manufacture Lead Time (default: 7 days)
- Market Adjustment (default: 0%)
- Sales Velocity Weight (default: 0.25)
- Search Volume Velocity Weight (default: 0.15)
- Forecast Horizon (default: 52 weeks)

## 📊 Forecast Algorithm

The forecasting algorithm follows this process:

### Step 1: Data Loading
```
Load from database:
├── Weekly sales (units_sold)
├── Weekly traffic (sessions, page views)
└── Current inventory (FBA, AWD, inbound)
```

### Step 2: Smoothing
```
For sales and search volume:
1. Calculate Peak Envelope (rolling max)
2. Calculate Smooth Envelope (rolling mean)
3. Calculate Final Curve (max of peak/smooth)
4. Calculate Final Smooth (exponential smoothing)
```

### Step 3: Velocity Adjustments
```
1. Sales Velocity = (recent_avg - long_term_avg) / long_term_avg
2. Search Volume Velocity = (recent_sv - long_term_sv) / long_term_sv
3. Weighted Adjustment = (sales_vel × weight) + (sv_vel × weight) + market_adj
```

### Step 4: Forecast Generation
```
1. Use last smoothed value as baseline
2. Project forward N weeks
3. Apply velocity adjustments
4. Adjusted Forecast = Base Forecast × (1 + adjustments)
```

### Step 5: Inventory Planning
```
1. Calculate DOI = inventory / avg_daily_forecast
2. Calculate Runout Date = date when cumulative forecast ≥ inventory
3. Calculate Units to Make = forecast(DOI + lead_time) - current_inventory
```

## 📈 Output Files

### 1. historical_*.csv
Historical sales data with all smoothing components:
- `week_end`: Week ending date
- `units_sold`: Actual units sold
- `units_peak_env`: Peak envelope
- `units_smooth_env`: Smooth envelope
- `units_final_smooth`: Final smoothed value
- `search_volume`: Search volume (or sessions proxy)
- `sv_final_smooth`: Search volume smoothed
- `sales_velocity_adj`: Sales velocity adjustment
- `sv_velocity_adj`: Search volume velocity adjustment

### 2. forecast_*.csv
Future forecast data:
- `week_end`: Week ending date
- `forecast_base`: Base forecast (unadjusted)
- `forecast_adjusted`: Adjusted forecast with velocity multipliers
- `is_forecast`: Always `True`

### 3. inventory_plan_*.csv
Inventory planning metrics:
- `current_inventory`: Total inventory units
- `runout_date_total`: Date when total inventory runs out
- `doi_total`: Days of inventory (total)
- `runout_date_fba_available`: Date when available FBA runs out
- `doi_fba_available`: Days of inventory (FBA available only)
- `units_to_make`: Units to manufacture to hit DOI goal
- `doi_goal`: Target days of inventory
- `total_lead_time`: Manufacturing + inbound lead time

## 📊 Charts Generated

### 1. Sales Forecast Chart
Shows:
- Historical actual sales
- Historical smoothed data
- Future forecast (base and adjusted)
- Forecast start line

### 2. Smoothing Detail Chart
Shows:
- Raw data
- Peak envelope
- Smooth envelope
- Final smooth curve
- (Separate panels for sales and search volume)

### 3. Inventory Plan Chart
Shows:
- Cumulative forecast
- Current inventory levels
- Runout dates
- Weekly forecast breakdown

### 4. Inventory Breakdown Pie Chart
Shows:
- Available FBA
- Reserved FBA
- Inbound FBA
- Researching/AWD

## ⚙️ Settings Explained

### Amazon DOI Goal (120 days)
How many days of inventory you want to maintain on Amazon. Higher = more safety stock.

### Inbound Lead Time (30 days)
How many days it takes to ship from your warehouse to Amazon FBA.

### Manufacture Lead Time (7 days)
How many days it takes to manufacture the product.

### Market Adjustment (0%)
Manual adjustment to account for known market changes (e.g., seasonality, promotions).
- Positive = increase forecast
- Negative = decrease forecast
- Example: `0.10` = +10% adjustment

### Sales Velocity Weight (0.25)
How much to weight recent sales trends in the forecast.
- Higher = more responsive to recent changes
- Lower = more stable, less reactive

### Search Volume Velocity Weight (0.15)
How much to weight search volume trends.
- Helps predict demand changes before they appear in sales

### Forecast Horizon (52 weeks)
How many weeks to forecast into the future.

## 🔧 Advanced Usage

### Use Different Database
Edit `config.py`:
```python
USE_SQLITE = True   # Use local SQLite
# or
USE_SQLITE = False  # Use PostgreSQL/RDS
```

### Programmatic Usage
```python
from forecasting.generate_forecast import ForecastGenerator
from forecasting.settings import ForecastSettings

# Custom settings
settings = ForecastSettings(
    amazon_doi_goal=90,
    sales_velocity_weight=0.3
)

# Generate forecast
generator = ForecastGenerator(asin='B0C73TDZCQ', settings=settings)
hist_df, forecast_df, inv_plan = generator.generate(start_date='2024-05-01')

# Access results
print(f"Units to make: {inv_plan['units_to_make']}")
print(f"Runout date: {inv_plan['runout_date_total']}")
```

### Export to Excel
```python
from forecasting.visualize import visualize_forecast

# Generate forecast and charts
visualizer, charts = visualize_forecast(
    asin='B0C73TDZCQ',
    start_date='2024-05-01',
    export_path='forecasting/output',
    show_charts=False
)

# Combine all data into Excel
import pandas as pd
with pd.ExcelWriter('forecasting/output/full_forecast.xlsx') as writer:
    visualizer.historical_df.to_excel(writer, sheet_name='Historical', index=False)
    visualizer.forecast_df.to_excel(writer, sheet_name='Forecast', index=False)
    pd.DataFrame([visualizer.inventory_plan]).to_excel(writer, sheet_name='Inventory Plan', index=False)
```

## 🧪 Testing

Test individual components:

```bash
# Test settings
python forecasting/settings.py

# Test engine
python forecasting/engine.py

# Test data loader
python forecasting/data_loader.py
```

## 📝 Notes

- **Search Volume**: Currently uses sessions as a proxy. For more accurate forecasts, integrate actual Amazon search volume data from Brand Analytics.
- **Seasonality**: Current implementation doesn't explicitly model seasonality. For seasonal products, adjust the `market_adjustment` setting or implement SARIMA/Prophet models.
- **Multiple Products**: Run separately for each ASIN/SKU. Future version could support batch forecasting.

## 🎓 Formula Reference

All formulas match `Forecast Test.xlsx`:

| Component | Formula |
|-----------|---------|
| Peak Envelope | `MAX(current, window)` |
| Smooth Envelope | `AVERAGE(window)` |
| Final Curve | `MAX(peak_env, smooth_env)` |
| Final Smooth | `α × current + (1-α) × previous` |
| Velocity Adj | `(last - avg) / avg` |
| Adjusted Forecast | `base × (1 + weighted_adj)` |
| DOI | `inventory / (forecast / 7)` |
| Runout Date | `week_start + (remaining / week_units) × 7` |
| Units to Make | `forecast(DOI + lead_time) - inventory` |

## 🐛 Troubleshooting

**No data found:**
- Ensure product ASIN exists in database
- Check start_date isn't too recent
- Run `python scripts/db_summary.py` to verify data

**Charts not showing:**
- Install matplotlib: `pip install matplotlib`
- Use `--no-show` flag to save without displaying

**Forecast looks wrong:**
- Check settings with `python forecasting/edit_settings.py`
- Review historical data for anomalies
- Adjust velocity weights

## 📞 Support

For issues or questions, check:
1. Database has data: `python scripts/db_summary.py`
2. Settings are correct: `cat forecasting/settings.json`
3. Review generated CSV files for data quality

---

**Made with 📊 for data-driven inventory planning**


