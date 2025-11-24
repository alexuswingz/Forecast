# DBeaver Setup Guide for SQLite Database

## 📊 Quick Setup

### Step 1: Initialize the Database

```bash
# Navigate to project folder
cd "C:\Users\User\OneDrive\Desktop\The 1000 bananas\The1000backend"

# Activate virtual environment
venv\Scripts\activate

# Create database with sample data (30 days)
python setup_database.py

# Or create without sample data
python setup_database.py no-samples

# Or create with custom number of days
python setup_database.py 60
```

This creates: `kpi_metrics.db` in your project folder

---

### Step 2: Open DBeaver

1. Launch DBeaver
2. Click **"New Database Connection"** or press `Ctrl+Shift+N`

---

### Step 3: Select SQLite

1. In the connection wizard, find and select **SQLite**
2. Click **Next**

---

### Step 4: Configure Connection

**Connection Settings:**
- **Path**: Click "Browse" or paste:
  ```
  C:\Users\User\OneDrive\Desktop\The 1000 bananas\The1000backend\kpi_metrics.db
  ```
- **Connection name** (optional): `KPI Metrics Dev DB`

Click **Test Connection**
- If prompted to download drivers, click **Download**

---

### Step 5: Connect

Click **Finish**

You should now see the database in DBeaver's Database Navigator!

---

## 🔍 Exploring the Database

### View Tables

Expand the connection:
```
KPI Metrics Dev DB
  └── main
      └── Tables
          ├── kpi_metrics          (Aggregate KPIs)
          ├── metric_definitions   (Metric metadata)
          ├── child_traffic_metrics (Child ASIN sessions/sales)
          └── inventory_snapshots  (FBA + AWD buckets)
```

### Query Examples

Right-click table → **View Data** or open SQL Editor and run:

```sql
-- View all metrics
SELECT * FROM kpi_metrics ORDER BY date DESC LIMIT 100;

-- View metrics by category
SELECT * FROM kpi_metrics WHERE metric_category = 'Sales' ORDER BY date DESC;

-- Get daily sales totals
SELECT 
    date, 
    metric_name, 
    value, 
    unit
FROM kpi_metrics 
WHERE metric_category = 'Sales' 
ORDER BY date DESC, metric_name;

-- Get advertising performance
SELECT 
    date,
    metric_name,
    value,
    target,
    unit
FROM kpi_metrics
WHERE metric_category = 'Advertising'
ORDER BY date DESC;

SELECT 
    metric_name,
    metric_category,
    COUNT(*) as data_points,
    AVG(value) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value
FROM kpi_metrics
GROUP BY metric_name, metric_category
ORDER BY metric_category, metric_name;

-- View metric definitions
SELECT * FROM metric_definitions;

-- Join metrics with their definitions
SELECT 
    m.date,
    m.metric_name,
    m.value,
    m.unit,
    d.description,
    d.formula
FROM kpi_metrics m
LEFT JOIN metric_definitions d ON m.metric_name = d.metric_name
WHERE m.date >= date('now', '-7 days')
ORDER BY m.date DESC, m.metric_name;

-- Daily performance snapshot
-- Child ASIN KPIs
SELECT
    date,
    child_asin,
    sku,
    ordered_product_sales AS total_sales,
    units_ordered,
    sessions,
    conversion_rate
FROM child_traffic_metrics
WHERE date >= date('now', '-14 days')
ORDER BY date DESC, ordered_product_sales DESC;

-- Inventory totals (all programs)
SELECT
    snapshot_date,
    sku,
    fulfillment_program,
    total_quantity,
    available_quantity,
    reserved_quantity,
    inbound_working_quantity,
    inbound_shipped_quantity,
    inbound_receiving_quantity
FROM inventory_snapshots
WHERE snapshot_date >= date('now', '-14 days')
ORDER BY snapshot_date DESC, sku;

-- Consolidated inventory per SKU (FBA + AWD)
SELECT
    snapshot_date,
    sku,
    SUM(available_quantity) AS available,
    SUM(reserved_quantity) AS reserved,
    SUM(inbound_working_quantity + inbound_shipped_quantity + inbound_receiving_quantity) AS inbound_total
FROM inventory_snapshots
GROUP BY snapshot_date, sku
ORDER BY snapshot_date DESC, sku;
SELECT 
    date,
    SUM(CASE WHEN metric_name = 'total_orders' THEN value END) as orders,
    SUM(CASE WHEN metric_name = 'total_revenue' THEN value END) as revenue,
    SUM(CASE WHEN metric_name = 'total_ad_spend' THEN value END) as ad_spend,
    SUM(CASE WHEN metric_name = 'total_ad_sales' THEN value END) as ad_sales
FROM kpi_metrics
WHERE date >= date('now', '-30 days')
GROUP BY date
ORDER BY date DESC;
```

---

## 📈 Database Schema

### Table: kpi_metrics

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| date | DATE | Metric date |
| timestamp | DATETIME | Created timestamp |
| metric_name | VARCHAR(255) | Name of the metric |
| metric_category | VARCHAR(100) | Category (Sales, Advertising) |
| metric_subcategory | VARCHAR(100) | Subcategory (optional) |
| value | FLOAT | Metric value |
| target | FLOAT | Target value |
| previous_value | FLOAT | Previous period value |
| unit | VARCHAR(50) | Unit (count, currency, percentage) |
| source | VARCHAR(100) | Data source |
| notes | TEXT | Additional notes |
| created_at | DATETIME | Record created |
| updated_at | DATETIME | Record updated |

### Table: metric_definitions
### Table: child_traffic_metrics

Tracks Detail Page Sales & Traffic by Child Item.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| date | DATE | Reporting date |
| child_asin | VARCHAR(20) | Child ASIN |
| parent_asin | VARCHAR(20) | Parent ASIN |
| sku | VARCHAR(50) | Seller SKU |
| sessions | FLOAT | Sessions count |
| session_percentage | FLOAT | Session percentage |
| page_views | FLOAT | Page views |
| page_views_percentage | FLOAT | Page view share |
| buy_box_percentage | FLOAT | Buy box percentage |
| units_ordered | FLOAT | Units sold |
| units_ordered_b2b | FLOAT | Units sold B2B |
| ordered_product_sales | FLOAT | Sales amount |
| ordered_product_sales_b2b | FLOAT | Sales amount B2B |
| total_order_items | FLOAT | Orders |
| conversion_rate | FLOAT | Unit session % |
| created_at / updated_at | DATETIME | Audit columns |

### Table: inventory_snapshots

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| snapshot_date | DATE | Snapshot date |
| asin | VARCHAR(20) | ASIN |
| sku | VARCHAR(50) | SKU |
| fnsku | VARCHAR(40) | Fulfillment network SKU |
| fulfillment_program | VARCHAR(20) | `FBA` or `AWD` |
| total_quantity | FLOAT | Total units |
| available_quantity | FLOAT | Available supply |
| reserved_quantity | FLOAT | Reserved units |
| inbound_working_quantity | FLOAT | Inbound working |
| inbound_shipped_quantity | FLOAT | Inbound shipped |
| inbound_receiving_quantity | FLOAT | Inbound receiving |
| research_quantity | FLOAT | Research/damages |
| fulfillment_center_id | VARCHAR(50) | FC (if provided) |
| source_report_type | VARCHAR(80) | Report type |
| created_at / updated_at | DATETIME | Audit columns |

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| metric_name | VARCHAR(255) | Unique metric name |
| description | TEXT | Metric description |
| formula | TEXT | Calculation formula |
| data_type | VARCHAR(50) | Data type |
| category | VARCHAR(100) | Category |
| subcategory | VARCHAR(100) | Subcategory |
| created_at | DATETIME | Record created |
| updated_at | DATETIME | Record updated |

---

## 🛠️ Common Tasks in DBeaver

### Export Data

1. Right-click table → **Export Data**
2. Choose format: CSV, Excel, JSON, etc.
3. Configure options
4. Click **Proceed**

### Import Data

1. Right-click table → **Import Data**
2. Select file
3. Map columns
4. Click **Proceed**

### Create ER Diagram

1. Right-click database → **View Diagram**
2. DBeaver generates visual schema

### Backup Database

Simply copy the file:
```bash
copy kpi_metrics.db kpi_metrics_backup.db
```

Or in DBeaver:
1. Right-click database → **Tools** → **Backup**

---

## 🔄 Refresh Data

When you add data via the API or sync scripts:

**In DBeaver:**
- Press `F5` or click **Refresh** icon to see new data

---

## 💡 Pro Tips

### 1. Create Bookmarks

Save frequently used queries:
- Write query in SQL Editor
- Right-click → **Add to Bookmarks**

### 2. Use Data Viewer Features

- **Filters**: Click column header → Add filter
- **Sorting**: Click column header
- **Search**: `Ctrl+F`
- **Export**: Right-click results → Export

### 3. SQL Editor Shortcuts

- `Ctrl+Enter`: Execute current query
- `Ctrl+Shift+Enter`: Execute script
- `Ctrl+Space`: Auto-complete
- `Alt+X`: Explain plan

### 4. View Data Updates in Real-Time

- Open table view
- Press `F5` to refresh periodically
- Or enable auto-refresh in preferences

---

## 🚀 Next Steps

1. **Start API Server**
   ```bash
   python main.py
   ```
   Visit: http://localhost:8000/docs

2. **Add Real Data**
   - Configure Amazon API credentials in `.env` (LWA + AWS + role ARN)
   - Run: `python data_sync.py --start-date 2024-01-01 --end-date 2024-12-31`
   - Or refresh recent data: `python data_sync.py --job incremental --days 3`
   - Press `F5` in DBeaver to see new SP-API data

3. **Create Visualizations**
   - Use DBeaver's chart features
   - Or export to Excel/BI tools
   - Or build frontend using the API

---

## 🐛 Troubleshooting

### Can't Find Database File
- Ensure you ran `setup_database.py` first
- Check file exists: `dir kpi_metrics.db`
- Use full absolute path in DBeaver

### Database Locked Error
- Close any other connections
- Make sure API server isn't running
- Restart DBeaver

### No Data Showing
- Run `setup_database.py` with sample data
- Check filters in DBeaver aren't hiding data
- Verify table isn't empty: `SELECT COUNT(*) FROM kpi_metrics;`

---

## 📞 Database File Location

Your database is located at:
```
C:\Users\User\OneDrive\Desktop\The 1000 bananas\The1000backend\kpi_metrics.db
```

You can:
- ✅ Open in DBeaver
- ✅ Copy for backup
- ✅ Share with team
- ✅ Open in other SQLite tools (DB Browser, SQLite Studio)

---

**Happy querying! 🎉**

