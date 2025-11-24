# Project Folder Structure

## Overview
This document explains the organized folder structure of The 1000 Bananas Backend project.

## 📁 Root Directory (11 files)

**Core application files only:**
```
The1000backend/
├── .env                    # Environment variables (credentials)
├── .gitignore             # Git ignore rules
├── config.py              # Configuration management
├── database.py            # Database connection
├── data_sync.py           # Data synchronization orchestrator
├── kpi_metrics.db         # SQLite database (dev only)
├── main.py                # FastAPI entry point
├── models.py              # SQLAlchemy ORM models
├── README.md              # Project documentation
├── requirements.txt       # Python dependencies
└── scheduler.py           # Scheduled jobs
```

## 📂 Organized Folders

### 🔌 `integrations/` (6 files)
API integration clients for external services.

```
integrations/
├── __init__.py
├── amazon_sp_api.py       # Amazon Selling Partner API
└── amazon_ads_api.py      # Amazon Advertising API
```

### 📥 `importers/` (7 files)
Scripts for importing data from various sources.

```
importers/
├── import_ads_report.py                 # Import ads performance data
├── import_awd_inventory_report.py       # Import AWD inventory
├── import_fba_inventory_report.py       # Import FBA inventory
├── import_fulfillment_shipments.py      # Import order fulfillment data
├── import_inventory_ledger.py           # Import inventory ledger
├── import_products_and_cogs.py          # Import product master data
└── sync_child_daily.py                  # Daily child traffic sync
```

### 🛠️ `scripts/` (15 files)
Utility and maintenance scripts.

```
scripts/
├── build_hydrangea_metrics.py          # Build weekly metrics
├── check_hydrangea_orders.py           # Verify order data
├── db_summary.py                        # Database statistics
├── export_hydrangea_from_rds.py        # Generate Excel from RDS
├── export_hydrangea_to_excel.py        # Generate Excel from SQLite
├── fetch_settlement_reports.py         # Pull settlement data
├── find_hydrangea_skus_2025.py         # Find SKUs
├── link_asins.py                        # Link ASINs across tables
├── migrate_sqlite_to_postgres.py       # Database migration (Python)
├── migrate_sqlite_to_rds.ps1           # Database migration (PowerShell)
├── run_sql.py                           # Execute SQL queries
├── show_config.py                       # Display configuration
├── sync_child_daily.py                  # Daily traffic sync
└── sync_to_rds.py                       # Sync data to RDS
```

### 🔄 `batch_scripts/` (2 files)
Windows batch automation scripts.

```
batch_scripts/
├── import_and_link.bat                  # Full import + ASIN linking
└── import_and_link_fast.bat            # Fast import (drop/recreate)
```

### 📊 `data/` (5 files + subdirectories)
All source data files.

```
data/
├── source/                              # Original data files
│   ├── Data Bing Bong KPIs_Metrics (2).xlsx
│   ├── Sponsored_Products_Advertised_product_report (1).xlsx
│   ├── 3568a9b6-e7ad-41f6-a70b-7b7b58beb6f6.amzn1.tortuga.4.na.csv
│   ├── 374975020406 (1).csv
│   └── fba.txt
└── Fulfillment reports/                 # Amazon fulfillment CSVs (17 files)
```

### 📈 `reports/` (5 files)
Generated output reports and metrics.

```
reports/
├── Hydrangea_Weekly_Metrics_from_RDS.xlsx    # Latest from RDS
├── Hydrangea_Weekly_Metrics.xlsx             # From SQLite
├── hydrangea_weekly_metrics_with_conversion.csv
├── hydrangea_weekly_metrics.csv
└── hydrangea_weekly.txt
```

### 📋 `logs/` (5 files)
Application logs for debugging.

```
logs/
├── ads_import.log
├── ads_import2.log
├── fulfillment_import.log
├── migration.log
└── rds_sync.log
```

### 💾 `raw_exports/` (26 files)
Cached raw API responses for debugging.

```
raw_exports/
├── child_sales_YYYY-MM-DD_YYYY-MM-DD.tsv    # Child traffic reports
└── orders_YYYY-MM-DD_YYYY-MM-DD.json        # Order data
```

### 📚 `docs/` (5 files)
Project documentation.

```
docs/
├── README.md                    # Project overview (also in root)
├── START_HERE.md               # Quick start guide
├── WALKTHROUGH.md              # Detailed setup
├── QUICK_START.md              # Quick reference
├── DBEAVER_SETUP.md            # Database viewer setup
└── FOLDER_STRUCTURE.md         # This file
```

## 🚀 Common Workflows

### Import Data
```bash
# Import fulfillment data
python importers/import_fulfillment_shipments.py --folder "data/Fulfillment reports"

# Import ads data
python importers/import_ads_report.py --input "data/source/Sponsored_Products_Advertised_product_report (1).xlsx"

# Link ASINs
python scripts/link_asins.py
```

### Generate Reports
```bash
# From RDS (production)
python scripts/export_hydrangea_from_rds.py

# From SQLite (development)
python scripts/export_hydrangea_to_excel.py
```

### Database Operations
```bash
# Check database status
python scripts/db_summary.py

# Sync to RDS
python scripts/sync_to_rds.py --drop-first

# Run custom query
python scripts/run_sql.py --sql "SELECT COUNT(*) FROM order_items"
```

### Batch Operations
```bash
# Full import with ASIN linking (Windows)
batch_scripts\import_and_link_fast.bat
```

## 📝 Notes

- **Root directory**: Only core application files, no clutter
- **Logs folder**: Ignored by Git, safe to delete anytime
- **Raw exports**: Cached API responses, can be regenerated
- **Reports**: Generated output files, not source controlled
- **Data/source**: Original data files, keep for reference

## 🧹 Maintenance

To clean up generated files:
```bash
# Delete logs (will be regenerated)
rm -rf logs/*

# Delete cached exports (will be regenerated)
rm -rf raw_exports/*

# Delete old reports (can be regenerated)
rm reports/*.csv
```

To rebuild from scratch:
1. Keep: `data/source/*` and `data/Fulfillment reports/*`
2. Delete: `kpi_metrics.db`, `logs/*`, `raw_exports/*`, `reports/*`
3. Run importers again

---

**Last Updated**: November 2025



