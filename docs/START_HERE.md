# 🚀 START HERE - SQLite Development Setup

## Quick 3-Step Setup (5 minutes)

### ✅ Step 1: Install Dependencies
```bash
cd "C:\Users\User\OneDrive\Desktop\The 1000 bananas\The1000backend"

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### ✅ Step 2: Create Database
```bash
# Create SQLite database with 30 days of sample data
python setup_database.py
```

**Output:**
```
✓ Database tables created
✓ Metric definitions created
✓ Sample metrics created

DATABASE SETUP COMPLETE!
Database file: kpi_metrics.db
Total metrics: 390
```

### ✅ Step 3: View in DBeaver
1. Open DBeaver
2. New Connection → SQLite
3. Path: `C:\Users\User\OneDrive\Desktop\The 1000 bananas\The1000backend\kpi_metrics.db`
4. Test Connection → Finish

**See detailed DBeaver instructions in: `DBEAVER_SETUP.md`**

---

## 🎯 What You Get

### Sample Data Categories:
- **Sales Metrics**: orders, revenue, average order value
- **Advertising Metrics**: impressions, clicks, spend, ROAS, ACOS
- **30 Days** of daily data points
- **13 Different** KPI metrics

### Database Tables:
- `kpi_metrics` - Top-level KPI data points
- `metric_definitions` - Metric metadata and formulas
- `child_traffic_metrics` - Child ASIN sales + sessions + conversion rate direct from Business Reports
- `inventory_snapshots` - Daily FBA/AWD inventory buckets (available, reserved, inbound, etc.)

---

## 🌐 Optional: Start API Server

```bash
# Start FastAPI server
python main.py
```

**Access:**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000
- Get Metrics: http://localhost:8000/api/metrics

**Example API Calls:**
```bash
# Get all metrics
curl http://localhost:8000/api/metrics?limit=10

# Get sales metrics only
curl "http://localhost:8000/api/metrics?category=Sales"

# Get metrics from specific date
curl "http://localhost:8000/api/metrics?start_date=2024-11-01"
```

---

## 📊 Quick DBeaver Queries

```sql
-- View recent metrics
SELECT * FROM kpi_metrics ORDER BY date DESC LIMIT 50;

-- Sales summary
SELECT date, metric_name, value, unit
FROM kpi_metrics 
WHERE metric_category = 'Sales' 
ORDER BY date DESC;

-- Advertising performance
SELECT date, metric_name, value, target
FROM kpi_metrics 
WHERE metric_category = 'Advertising'
ORDER BY date DESC;
```

---

## 🔄 Regenerate Database

Need fresh data?
```bash
# Delete old database
del kpi_metrics.db

# Create new one with 60 days of data
python setup_database.py 60
```

---

## 🎓 Learn More

- **DBEAVER_SETUP.md** - Complete DBeaver guide with queries
- **README.md** - Full project documentation
- **WALKTHROUGH.md** - Detailed step-by-step guide
- **QUICK_START.md** - Fast setup reference

---

## 🔮 Next Steps (When Ready)

### 1. Add Real Amazon Data

1. **Edit `.env`** and include every credential required by the SP-API Python SDK:
   ```env
   # Login with Amazon (LWA)
   SP_API_CLIENT_ID=amzn1.application-oa2-client.xxxxx
   SP_API_CLIENT_SECRET=amzn1.oa2-cs.v1.xxxxx
   SP_API_REFRESH_TOKEN=Atzr|IwEBIxxxxx

   # AWS IAM (used to sign SP-API calls)
   AWS_ACCESS_KEY_ID=AKIAxxxxxxxx
   AWS_SECRET_ACCESS_KEY=xxxxxxxx
   SP_API_ROLE_ARN=arn:aws:iam::123456789012:role/YourSPAPIRole
   SP_API_REGION=us-east-1
   ```
   > Need help? Follow Amazon’s “Automate your SP-API calls using a prebuilt Python SDK” guide to provision the IAM role + policies.

2. **Run the sync (full or incremental)**:
   ```bash
   # Backfill from 2024-01-01 through today
   python data_sync.py --start-date 2024-01-01 --end-date 2024-12-31

   # Or just refresh the most recent 3 days
   python data_sync.py --job incremental --days 3
   ```
   This pulls:
   - Child-level sales/traffic (total sales, units sold, sessions, conversion rate)
   - FBA + AWD inventory (available, reserved, inbound working/shipped/receiving)
   - Order-level KPIs for legacy dashboards

### 2. Explore Excel Definitions
Your `Data Bing Bong KPIs_Metrics (2).xlsx` file contains metric definitions.
Use `excel_parser.py` to import them.

### 3. Build Dashboard
Use the API to create a frontend dashboard:
- React + Chart.js
- Power BI
- Tableau
- Or any visualization tool

---

## ✨ You're All Set!

Your SQLite database is ready for development. Open it in DBeaver and start exploring! 🎉

**Questions? Check the other markdown files for detailed guides.**

