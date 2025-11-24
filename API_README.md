# The 1000 Bananas - API Documentation

Simple REST API for Amazon product metrics, forecasting, and inventory planning.

## Base URL
```
https://sl2r0ip8zl.execute-api.ap-southeast-2.amazonaws.com
```

---

## Endpoints

### 1. Get All Products
**GET** `/products`

Returns a list of all products with basic info.

**Response:**
```json
{
  "products": [
    {
      "asin": "B0BRTK1P8Z",
      "brand": "TPS Nutrients",
      "name": "Monstera Plant Food",
      "size": "8oz"
    }
  ]
}
```

---

### 2. Get Product Details + Inventory
**GET** `/product/{asin}`

Returns detailed product info and current inventory levels.

**Example:** `GET /product/B0BRTK1P8Z`

**Response:**
```json
{
  "product": {
    "asin": "B0BRTK1P8Z",
    "sku": "MNST-8OZ",
    "name": "Monstera Plant Food",
    "brand": "TPS Nutrients",
    "size": "8oz"
  },
  "inventory": {
    "fba": {
      "total": 6018,
      "available": 2825,
      "reserved": 1132,
      "inbound": 2285
    },
    "awd": {
      "total": 0,
      "outbound_to_fba": 0,
      "available": 0,
      "reserved": 0
    }
  },
  "latest_date": "2025-11-14"
}
```

---

### 3. Get Product Metrics (Dashboard)
**GET** `/metrics/{asin}`

Returns aggregated metrics for a date range with prior period comparison.

**⚡ Optimized:** Uses pre-aggregated daily_product_metrics table for sub-second response times.

**Query Parameters:**
- `days` (default: 30) - Number of days for current period

**Example:** `GET /metrics/B0BRTK1P8Z?days=30`

**Response:**
```json
{
  "product": {
    "asin": "B0BRTK1P8Z",
    "name": "Monstera Plant Food",
    "brand": "TPS Nutrients",
    "size": "8oz"
  },
  "date_range": {
    "current_start": "2025-10-17",
    "current_end": "2025-11-16",
    "prior_start": "2025-09-17",
    "prior_end": "2025-10-16",
    "days": 30
  },
  "current_period": {
    "units_sold": 2738,
    "sales": 28457.00,
    "sessions": 9139,
    "conversion_rate": 30.0,
    "page_views": 15234,
    "tacos": 20.2,
    "price": 11.99,
    "profit_margin": 15.6,
    "profit_total": 5825.00,
    "organic_sales_pct": 39.0,
    "ad_spend": 5750.00,
    "ad_sales": 17339.00,
    "ad_clicks": 1250,
    "ad_impressions": 45000,
    "organic_sales": 11118.00
  },
  "prior_period": {
    "units_sold": 2190,
    "sales": 24745.00,
    "sessions": 7810,
    "conversion_rate": 28.0,
    "tacos": 18.9,
    "price": 10.90,
    "profit_margin": 18.6,
    "profit_total": 4976.00
  },
  "changes": {
    "units_sold": 25.0,
    "sales": 15.0,
    "sessions": 17.0,
    "conversion_rate": 7.1,
    "tacos": 6.9,
    "price": 10.0,
    "profit_margin": -16.1,
    "profit_total": 17.1,
    "organic_sales_pct": 5.4
  }
}
```

---

### 4. Get Forecast Metrics
**GET** `/forecast/{asin}`

Returns forecast calculations including DOI, runout date, and units to make.

**⚡ Optimized:** Uses the new `weekly_forecast_metrics` table (Excel-accurate smoothing + velocity).

**Query Parameters (optional):**
- `doi_goal` (default: 120) - Target days of inventory
- `lead_time` (default: 37) - Manufacturing + shipping days

**Example:** `GET /forecast/B0BRTK1P8Z`

**Response:**
```json
{
  "current_date": "2025-11-16",
  "doi_goal_date": "2025-12-14",
  "doi_goal": 120,
  "lead_time": 37,
  "fba_available_days": 13,
  "total_days": 28,
  "forecast_days": 92,
  "weekly_forecast_avg": 1471.7,
  "daily_forecast_avg": 210.2,
  "runout_date": "2025-11-29",
  "units_to_make": 18542,
  "avg_daily_sales": 210.2,
  "inventory": {
    "total": 6018,
    "available_fba": 2825
  },
  "doi_fba_available": 13,
  "doi_total": 28
}
```

---

### 5. Get Chart Data (Historical + Forecast)
**GET** `/chart/{asin}`

Returns historical sales and forecast data for graphing with adjustable velocity weights.

**⚡ Real-Time Calculation:** Generates Excel-accurate smoothing on the fly. Supports adjustable velocity weights for interactive forecasting.

**Query Parameters:**
- `weeks` (default: 52) - Number of weeks to forecast ahead (max: 104)
- `sales_velocity_weight` (optional, default: 25) - Sales velocity adjustment weight (0-100% or 0-1 decimal)
- `sv_velocity_weight` (optional, default: 15) - Search volume velocity adjustment weight (0-100% or 0-1 decimal)

**Examples:** 
- Default: `GET /chart/B0BRTK1P8Z?weeks=52`
- Custom weights: `GET /chart/B0BRTK1P8Z?weeks=52&sales_velocity_weight=30&sv_velocity_weight=20`
- Decimal format: `GET /chart/B0BRTK1P8Z?weeks=52&sales_velocity_weight=0.3&sv_velocity_weight=0.2`

**Response:**
```json
{
  "historical": [
    {
      "week_end": "2024-11-17",
      "units_sold": 182.0,
      "units_smooth": 560.7
    },
    {
      "week_end": "2024-11-24",
      "units_sold": 774.0,
      "units_smooth": 591.5
    }
  ],
  "forecast": [
    {
      "week_end": "2025-11-23",
      "forecast_base": 774.0,
      "forecast_adjusted": 794.4
    },
    {
      "week_end": "2025-11-30",
      "forecast_base": 726.0,
      "forecast_adjusted": 745.2
    }
  ],
  "metadata": {
    "sales_velocity_adj": 0.0856,
    "sv_velocity_adj": 0.0421,
    "total_adjustment": 0.1056,
    "sales_velocity_weight": 0.25,
    "sv_velocity_weight": 0.15,
    "forecast_weeks": 52,
    "avg_weekly_sales": 1353.2
  }
}
```

**Frontend Usage:**
- Implement sliders for `sales_velocity_weight` and `sv_velocity_weight` (0-100%)
- When user clicks "Apply", call endpoint with new weights
- Chart updates in real-time with adjusted forecast
- Show individual velocity adjustments in metadata

---

### 6. Get Sales Chart Data (Daily Time Series) - ALL METRICS
**GET** `/sales-chart/{asin}`

Returns daily sales time series data with **ALL sales metrics** for clickable chart selection, plus summary metrics comparing current vs prior period.

**⚡ Optimized:** Uses pre-aggregated data for instant response.

**Query Parameters:**
- `days` (default: 30) - Number of days to show (range: 7-365 days, also used for prior period comparison)

**Example:** `GET /sales-chart/B0BRTK1P8Z?days=90`

**Recommended Presets:**
- 7 days - Last week
- 30 days - Last month (default)
- 60 days - Last 2 months
- 90 days - Last quarter
- 365 days - Last year

**Response:**
```json
{
  "asin": "B0BRTK1P8Z",
  "date_range": {
    "start": "2025-10-18",
    "end": "2025-11-16",
    "days": 30
  },
  "chart_data": [
    {
      "date": "2025-10-18",
      "units_sold": 160.0,
      "sales": 1915.20,
      "sessions": 450.0,
      "conversion_rate": 1.49,
      "price": 11.13
    }
  ],
  "summary": {
    "units_sold": {
      "current": 252,
      "prior": 769,
      "change_percent": -65.2
    },
    "sales": {
      "current": 2806.26,
      "prior": 8298.12,
      "change_percent": -63.9
    },
    "sessions": {
      "current": 2084,
      "prior": 2943,
      "change_percent": -29.2
    },
    "conversion_rate": {
      "current": 1.49,
      "prior": 1.01,
      "change_percent": 101.4
    },
    "price": {
      "current": 11.13,
      "prior": 10.79,
      "change_percent": 3.8
    },
    "ad_sales_percent": {
      "current": 55.6,
      "prior": 58.9,
      "change_percent": -5.6
    }
  }
}
```

**Available Metrics (for clickable selection):**
- `units_sold` - Units sold
- `sales` - Sales revenue
- `sessions` - Product page sessions
- `conversion_rate` - Conversion rate (%)
- `price` - Average selling price
- `ad_sales_percent` - Ad sales as % of total sales

**Frontend Usage:**
- Display ALL metrics as clickable cards
- Show/hide chart lines dynamically when user clicks cards
- Default visible: Units Sold (blue) + Sales (orange)
- See `CLICKABLE_METRICS_GUIDE.md` for full implementation

---

### 7. Get Ads Chart Data (Daily Time Series) - ALL AD METRICS
**GET** `/ads-chart/{asin}`

Returns daily advertising performance data with **ALL ad metrics** for clickable chart selection, plus summary metrics comparing current vs prior period.

**⚡ Optimized:** Uses pre-aggregated data for instant response.

**Query Parameters:**
- `days` (default: 30) - Number of days to show (range: 7-365 days, also used for prior period comparison)

**Example:** `GET /ads-chart/B0BRTK1P8Z?days=90`

**Recommended Presets:**
- 7 days - Last week
- 30 days - Last month (default)
- 60 days - Last 2 months
- 90 days - Last quarter
- 365 days - Last year

**Response:**
```json
{
  "asin": "B0BRTK1P8Z",
  "date_range": {
    "start": "2025-10-18",
    "end": "2025-11-16",
    "days": 30
  },
  "chart_data": [
    {
      "date": "2025-10-18",
      "total_sales": 1915.20,
      "ad_sales": 890.42,
      "ad_units": 78,
      "ad_spend": 489.42,
      "ad_clicks": 365,
      "ad_impressions": 12450,
      "tacos": 17.4,
      "acos": 54.9,
      "cpc": 1.34
    }
  ],
  "summary": {
    "total_sales": {
      "current": 2806.26,
      "prior": 8298.12,
      "change_percent": -63.9
    },
    "ad_sales": {
      "current": 1560.80,
      "prior": 4892.33,
      "change_percent": -68.1
    },
    "ad_units": {
      "current": 140,
      "prior": 441,
      "change_percent": -68.3
    },
    "ad_spend": {
      "current": 489.42,
      "prior": 1423.55,
      "change_percent": -65.6
    },
    "ad_clicks": {
      "current": 365,
      "prior": 1062,
      "change_percent": -65.6
    },
    "ad_impressions": {
      "current": 45200,
      "prior": 128400,
      "change_percent": -64.8
    },
    "tacos": {
      "current": 17.4,
      "prior": 17.2,
      "change_percent": 1.2
    },
    "acos": {
      "current": 31.4,
      "prior": 29.1,
      "change_percent": 7.9
    },
    "cpc": {
      "current": 1.34,
      "prior": 1.34,
      "change_percent": 0.0
    }
  }
}
```

**Available Metrics (for clickable selection):**
- `total_sales` - Total sales revenue
- `ad_sales` - Ad-attributed sales
- `ad_units` - Ad-attributed units
- `ad_spend` - Total ad spend
- `ad_clicks` - Total ad clicks
- `ad_impressions` - Total impressions
- `tacos` - Total ACOS (Ad Spend / Total Sales × 100)
- `acos` - ACOS (Ad Spend / Ad Sales × 100)
- `cpc` - Cost Per Click (Ad Spend / Clicks)

**Frontend Usage:**
- Display ALL ad metrics as clickable cards
- Show/hide chart lines dynamically when user clicks cards
- Default visible: Total Sales (blue) + TACOS (orange)
- See `CLICKABLE_METRICS_GUIDE.md` for full implementation

---

### 8. Get Planning Table
**GET** `/planning`

Returns paginated product planning data with inventory and sales metrics.

**Query Parameters:**
- `page` (default: 1) - Page number
- `limit` (default: 20) - Items per page

**Example:** `GET /planning?page=1&limit=20`

**Response:**
```json
{
  "products": [
    {
      "asin": "B0BZB814JM",
      "brand": "Bloom City",
      "product": "Acid Loving Plants",
      "size": "1 Gallon",
      "doi_fba": 6,
      "doi_total": 6,
      "inventory": 36.0,
      "forecast": 37,
      "sales_7_day": 0,
      "sales_30_day": 24,
      "formula": ""
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 593,
    "total_pages": 30
  }
}
```

---

## Error Responses

All errors return appropriate HTTP status codes with JSON body:

```json
{
  "error": "Product not found"
}
```

**Common Status Codes:**
- `200` - Success
- `400` - Bad Request (missing parameters)
- `404` - Not Found
- `500` - Internal Server Error

---

## Notes

- All dates are in `YYYY-MM-DD` format
- Currency values are in USD
- Inventory quantities are integers
- DOI (Days of Inventory) = Current Inventory / Daily Sales Rate
- Forecast uses 12-week historical average

---

## Data Sources

The API aggregates data from:
- **Sales:** Fulfilled Shipments
- **Traffic:** Amazon Detail Page Traffic Reports
- **Advertising:** Sponsored Products Performance
- **Inventory:** FBA/AWD Inventory Reports
- **COGS:** Product cost data

---

## Data Maintenance

### Daily Updates

The `/metrics` endpoint uses a pre-aggregated `daily_product_metrics` table for fast performance.

**Update daily after importing fresh data:**
```bash
# Windows
update_metrics_daily.bat

# Or direct Python
python scripts/update_daily_metrics.py --days 7
```

**What it does:**
- Aggregates last 7 days of data from source tables
- Updates `daily_product_metrics` table
- Handles late-arriving data (ads attribution, etc.)
- Takes ~30-60 seconds to run

**Cron Setup (Linux/Mac):**
```bash
# Add to crontab - run daily at 6 AM
0 6 * * * cd /path/to/The1000backend && python scripts/update_daily_metrics.py
```

**Windows Task Scheduler:**
```
Action: Start a Program
Program: C:\Users\User\OneDrive\Desktop\The 1000 bananas\The1000backend\update_metrics_daily.bat
Trigger: Daily at 6:00 AM
```

### Weekly Forecast Updates

`/forecast` + `/chart` use the Excel-accurate `weekly_forecast_metrics` table.

**One-time setup:**
```bash
python scripts/create_forecast_tables.py
```

**Update forecast data (per ASIN or for all):**
```bash
# Single ASIN
python scripts/update_weekly_forecast_metrics.py --asin B0BRTK1P8Z --no-export

# All ASINs (skip failures and no CSV export)
python scripts/update_weekly_forecast_metrics.py --skip-errors --no-export
```

**Tip:** run this after major data imports or weekly to refresh the smoothing + velocity adjustments that Lambda serves.

### Performance Metrics

| Endpoint | Without Pre-Aggregation | With Pre-Aggregation |
|----------|------------------------|---------------------|
| `/metrics/{asin}?days=30` | 20-30 seconds | **0.5-2 seconds** ⚡ |
| Data freshness | Real-time | Daily updates |
| Database load | High (full scans) | Low (index seeks) |

---

### 9. Get Weekly Metrics by Gregorian Calendar
**GET** `/weekly-metrics/{asin}`

Returns weekly aggregated metrics organized by Gregorian calendar weeks (ISO week standard).  
Perfect for dashboard tables showing sales metrics by week number.

**Parameters:**
- `year` (optional) - Year to query (default: current year)

**Example:** `GET /weekly-metrics/B0BRTK1P8Z?year=2025`

**Response:**
```json
{
  "success": true,
  "year": 2025,
  "asin": "B0BRTK1P8Z",
  "product": {
    "asin": "B0BRTK1P8Z",
    "name": "Monstera Plant Food",
    "size": "8oz",
    "brand": "TPS Nutrients"
  },
  "weeks": [
    {
      "week_number": 38,
      "week_start": "2025-09-15",
      "total_sales": 1234.56,
      "units_sold": 12,
      "avg_price": 102.88,
      "sessions": 32,
      "conversion_rate": 37.5,
      "ad_spend": 45.67,
      "ad_sales": 456.78,
      "ad_orders": 5,
      "ad_impressions": 240,
      "ad_clicks": 15,
      "tacos": 3.7,
      "acos": 10.0,
      "cpc": 3.04
    },
    {
      "week_number": 39,
      "week_start": "2025-09-22",
      "total_sales": 1567.89,
      "units_sold": 15,
      "avg_price": 104.53,
      "sessions": 45,
      "conversion_rate": 33.33,
      "ad_spend": 52.34,
      "ad_sales": 523.45,
      "ad_orders": 6,
      "ad_impressions": 310,
      "ad_clicks": 18,
      "tacos": 3.34,
      "acos": 10.0,
      "cpc": 2.91
    }
  ],
  "total_weeks": 42,
  "summary": {
    "total_sales": 52345.67,
    "total_units": 512,
    "total_sessions": 1456,
    "total_ad_spend": 1890.45,
    "total_ad_impressions": 12450,
    "avg_conversion_rate": 35.21,
    "avg_tacos": 3.61
  }
}
```

**Metrics Included:**
- **Total Sales** - Revenue for the week
- **Units Sold** - Number of units sold
- **Sessions** - Total page visits
- **Conversion Rate** - (Units / Sessions) × 100
- **TACOS** - Total Ad Cost of Sales (Ad Spend / Total Sales × 100)
- **Ad Impressions** - Total ad impressions

**Use Case:**
Perfect for populating dashboard tables that show weekly performance metrics organized by calendar week. Data starts from week 1 of the specified year and goes up to the current week (or end of year for past years).

---

Last Updated: November 2025

