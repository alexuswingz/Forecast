# Calculation Formulas & Logic

This document explains how all metrics are calculated in The 1000 Bananas system.

---

## Core Metrics

### 1. Sales & Units
**Data Source:** `order_items` table (Fulfilled Shipments)

```
Total Units = SUM(quantity)
Total Sales = SUM(item_price × quantity)
Average Order Value = Total Sales / Number of Orders
```

**Example:**
- 100 units sold at $25 each
- Total Sales = $2,500
- Average Order Value = $2,500 / 50 orders = $50

---

### 2. Traffic & Conversion

**Data Source:** `child_traffic_metrics` table

```
Sessions = Total page visits
Page Views = Total pages viewed
Session-to-Unit = (Units Ordered / Sessions) × 100

Organic Conversion Rate = (Organic Units / Sessions) × 100
```

**Example:**
- 1,000 sessions, 50 units sold
- Organic Conversion Rate = (50 / 1,000) × 100 = 5%

---

### 3. Advertising Metrics

**Data Source:** `ad_product_performance` table

```
Ad Clicks = Total clicks on ads
Ad Spend = Total advertising cost
Ad Sales = 7-day attributed sales from ads
Ad Orders = 7-day attributed orders from ads

Ad Conversion Rate = (Ad Orders / Ad Clicks) × 100
CPC (Cost Per Click) = Ad Spend / Ad Clicks
ACOS = (Ad Spend / Ad Sales) × 100
ROAS = Ad Sales / Ad Spend
TACOS = (Ad Spend / Total Sales) × 100
```

**Example:**
- Ad Spend: $100
- Ad Sales: $500
- Ad Clicks: 200
- Ad Orders: 20
- ACOS = ($100 / $500) × 100 = 20%
- CPC = $100 / 200 = $0.50
- Ad Conversion Rate = (20 / 200) × 100 = 10%

---

### 4. Organic vs Paid Split

```
Organic Sales = Total Sales - Ad Sales
Organic Sales % = (Organic Sales / Total Sales) × 100
Paid Sales % = (Ad Sales / Total Sales) × 100
```

**Example:**
- Total Sales: $1,000
- Ad Sales: $300
- Organic Sales = $1,000 - $300 = $700
- Organic Sales % = 70%

---

## Inventory Metrics

### 5. Days of Inventory (DOI)

**Data Source:** `inventory_snapshots` table

```
Daily Sales Rate = Weekly Forecast / 7
DOI (Days) = Current Inventory / Daily Sales Rate

DOI FBA Available = Available FBA Units / Daily Sales Rate
DOI Total = Total Units (FBA + AWD + Inbound) / Daily Sales Rate
```

**Example:**
- Current Inventory: 2,825 units
- Weekly Forecast: 1,472 units
- Daily Sales Rate = 1,472 / 7 = 210.3 units/day
- DOI = 2,825 / 210.3 = 13 days

---

### 6. Inventory Breakdown

```
Total Inventory = FBA + AWD + Inbound + Research

FBA Inventory = Available + Reserved
AWD Inventory = Available + Reserved + Outbound to FBA

Inbound = Inbound Working + Inbound Shipped + Inbound Receiving
Available = Units ready to ship
Reserved = Units reserved for orders
Research = Units under investigation
```

---

## Forecasting

### 7. Weekly Forecast (Planning Table & Lambda)

**Data Source:** `weekly_forecast_metrics` (generated via `scripts/update_weekly_forecast_metrics.py`)

```
Weekly Forecast = AVG(forecast_adjusted for first 12 future weeks)
Daily Forecast  = Weekly Forecast / 7
```

This is the same number you see in the AUTOFORECAST workbook and is what `/forecast`, `/chart`, and the planning table use for DOI calculations.

---

### 8. Advanced Forecast (Excel-Accurate Smoothing)

**Used everywhere forecasts are shown (Lambda + Excel).**

Pipeline:

1. **Peak Envelope (C):** `=MAX(OFFSET(Bn,-2,0,5))`
2. **Smooth Envelope (D):** `=AVERAGE(OFFSET(Cn,-1,0,3))`
3. **Final Curve (E):** `=MAX(Bn, Cn, Dn)`
4. **Final Smooth (F):** 11-point weighted average with weights `[1,2,4,7,11,13,11,7,4,2,1]`
5. **Seasonal Baseline (G):** `=OFFSET(Fn,-52,0)` (repeat last year's smooth curve)
6. **Baseline Peak/Smooth (H/I):** 2-week peak followed by 7-point weights `[1,3,5,7,5,3,1]`
7. **Sales Velocity (J):** Ratio of Column F vs Column I using weighted 1/2/4/6-week daily averages  
   `Velocity = (WeightedAvg(F) / WeightedAvg(I)) - 1`
8. **Forecast (Future rows):**  
   `forecast_base = continued final smooth`  
   `forecast_adjusted = forecast_base × (1 + sales_velocity_weight + sv_velocity_weight + market_adj)`

All intermediate and future values land in `weekly_forecast_metrics`, so Lambda returns exactly what the workbook shows.

---

## Planning Metrics

### 9. Runout Date

```
Runout Date = Current Date + DOI (days)
```

**Example:**
- Today: Nov 16, 2025
- DOI: 13 days
- Runout Date = Nov 29, 2025

---

### 10. Units to Make

```
DOI Goal = Target days of inventory (e.g., 120 days)
Lead Time = Manufacturing + shipping time (e.g., 37 days)
Forecast Days = DOI Goal + Lead Time

Units to Make = (Daily Sales Rate × Forecast Days) - Current Inventory
```

**Example:**
- DOI Goal: 120 days
- Lead Time: 37 days
- Forecast Days = 157 days
- Daily Sales Rate: 210 units/day
- Current Inventory: 6,018 units
- Units to Make = (210 × 157) - 6,018 = 32,970 - 6,018 = 26,952 units

---

### 11. DOI Goal Date

```
DOI Goal Date = Current Date + DOI Goal (days)
```

**Example:**
- Today: Nov 16, 2025
- DOI Goal: 120 days
- DOI Goal Date = Mar 16, 2026

---

## Profit Metrics

### 12. Cost & Margin

**Data Source:** `product_cogs` table

```
Unit Cost = Manufacturing cost per unit
Gross Profit = Sales - (Units × Unit Cost)
Gross Margin % = (Gross Profit / Sales) × 100

Net Profit = Sales - Unit Cost - Ad Spend - FBA Fees
Net Margin % = (Net Profit / Sales) × 100
```

**Example:**
- Sales: $1,000
- Units: 40
- Unit Cost: $10
- Ad Spend: $200
- Gross Profit = $1,000 - (40 × $10) = $600
- Gross Margin = 60%
- Net Profit = $1,000 - $400 - $200 = $400
- Net Margin = 40%

---

## Weekly Aggregation

All daily/transactional data is aggregated to weeks (Monday-Sunday):

```sql
Week Start = date_trunc('week', date) 
  -- Returns Monday of that week

Week End = Week Start + 6 days
  -- Returns Sunday of that week
```

**Aggregation Rules:**
- **Sales/Units:** SUM across the week
- **Conversion Rate:** AVERAGE across days with traffic
- **Inventory:** Most recent snapshot in the week
- **Ad Metrics:** SUM of spend/sales, AVERAGE of rates

---

## Data Freshness

**Update Frequency:**
- Sales Data: Daily (from Fulfilled Shipments)
- Traffic Data: Daily (from SP-API)
- Inventory: Daily (from FBA/AWD reports)
- Advertising: Daily (from Ads API)
- Forecasts: Rebuilt via `scripts/update_weekly_forecast_metrics.py` (run weekly or after major imports)

**Historical Range:**
- Metrics: Up to 2 years of history
- Forecasts: Up to 2 years ahead (104 weeks)

---

## Notes

- All calculations use **UTC timestamps** converted to your marketplace timezone
- **Weekday 0** = Monday (ISO standard)
- Division by zero is handled (returns 0 or null)
- Null values are treated as 0 in aggregations
- Percentages are returned as decimals (e.g., 0.15 = 15%)

---

Last Updated: November 2025

