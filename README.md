# The 1000 Bananas Backend

Backend system for Amazon SP-API and Ads API data synchronization and metrics reporting.

## 📁 Project Structure

```
The1000backend/
├── 📄 Core Application Files
│   ├── config.py              # Configuration and environment variables
│   ├── database.py            # Database connection setup
│   ├── models.py              # SQLAlchemy ORM models
│   ├── main.py                # FastAPI application entry point
│   ├── data_sync.py           # Data synchronization orchestrator
│   ├── scheduler.py           # Scheduled job manager
│   ├── requirements.txt       # Python dependencies
│   └── .env                   # Environment variables (not in git)
│
├── 🗄️ Database
│   └── kpi_metrics.db         # SQLite database (dev only)
│
├── 🔌 integrations/           # API Integration modules
│   ├── amazon_sp_api.py       # Amazon Selling Partner API client
│   └── amazon_ads_api.py      # Amazon Advertising API client
│
├── 📥 importers/              # Data import scripts
│   ├── import_ads_report.py
│   ├── import_awd_inventory_report.py
│   ├── import_fba_inventory_report.py
│   ├── import_fulfillment_shipments.py
│   ├── import_inventory_ledger.py
│   ├── import_products_and_cogs.py
│   └── sync_child_daily.py
│
├── 🛠️ scripts/               # Utility and maintenance scripts
│   ├── build_hydrangea_metrics.py
│   ├── check_hydrangea_orders.py
│   ├── db_summary.py
│   ├── export_hydrangea_from_rds.py
│   ├── export_hydrangea_to_excel.py
│   ├── fetch_settlement_reports.py
│   ├── find_hydrangea_skus_2025.py
│   ├── link_asins.py
│   ├── migrate_sqlite_to_postgres.py
│   ├── migrate_sqlite_to_rds.ps1
│   ├── run_sql.py
│   ├── show_config.py
│   ├── sync_child_daily.py
│   └── sync_to_rds.py
│
├── 🔄 batch_scripts/         # Windows batch automation
│   ├── import_and_link.bat
│   └── import_and_link_fast.bat
│
├── 📊 data/                  # Source data files
│   ├── source/               # Original data files
│   │   ├── Data Bing Bong KPIs_Metrics (2).xlsx
│   │   ├── Sponsored_Products_Advertised_product_report (1).xlsx
│   │   └── [Other source files]
│   └── Fulfillment reports/  # Amazon fulfillment CSV reports
│
├── 📈 reports/               # Generated output reports
│   ├── Hydrangea_Weekly_Metrics_from_RDS.xlsx
│   ├── Hydrangea_Weekly_Metrics.xlsx
│   └── [Other generated reports]
│
├── 📋 logs/                  # Application logs
│   ├── ads_import.log
│   ├── fulfillment_import.log
│   ├── migration.log
│   └── rds_sync.log
│
├── 💾 raw_exports/           # Raw API response cache
│   └── [JSON/TSV files from Amazon APIs]
│
└── 📚 docs/                  # Documentation
    ├── README.md             # This file
    ├── START_HERE.md         # Quick start guide
    ├── WALKTHROUGH.md        # Detailed setup walkthrough
    ├── QUICK_START.md        # Quick reference
    └── DBEAVER_SETUP.md      # Database viewer setup
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and fill in your credentials:
- Amazon SP-API credentials
- Amazon Ads API credentials
- RDS PostgreSQL credentials (production)

### 3. Import Data
```bash
# Import fulfillment reports
python importers/import_fulfillment_shipments.py --folder "data/Fulfillment reports"

# Import ads data
python importers/import_ads_report.py --input "data/source/Sponsored_Products_Advertised_product_report (1).xlsx"

# Import products and COGS
python importers/import_products_and_cogs.py

# Link ASINs across all tables
python scripts/link_asins.py
```

### 4. Generate Reports
```bash
# Generate hydrangea weekly metrics from RDS
python scripts/export_hydrangea_from_rds.py
```

### 5. Sync to RDS (Production)
```bash
# Sync SQLite data to RDS PostgreSQL
python scripts/sync_to_rds.py --drop-first
```

## 📊 Database

### Development (SQLite)
- File: `kpi_metrics.db`
- Location: Project root
- Size: ~500 MB (1.5M+ rows)

### Production (RDS PostgreSQL)
- Host: `forecast.cf6s2y8ae04j.ap-southeast-2.rds.amazonaws.com`
- Database: `kpi_metrics`
- Tables: products, product_cogs, order_items, inventory_snapshots, child_traffic_metrics, ad_product_performance, settlement_transactions

## 📈 Available Metrics

### Hydrangea Product Metrics (Weekly)
- **Sales**: Total revenue, units sold
- **Traffic**: Sessions, conversion rate (organic + ads)
- **Ads**: Spend, TACOS, CPC, impressions, clicks
- **Inventory**: Total, Available, Reserved, Inbound (Working/Shipped/Receiving), FBA, AWD

### Data Coverage
- **Orders**: May 2024 - Nov 2025 (971,637 records)
- **Ads**: Aug 2025 - Nov 2025 (163,339 records)
- **Inventory**: May 2024 - Nov 2025 (382,613 snapshots)
- **Traffic**: May 2024 - Nov 2025 (8,945 child metrics)

## 🔄 Daily Automation

The system supports automated daily data pulls:

```bash
# Daily child traffic metrics
python importers/sync_child_daily.py

# Daily settlement reports
python scripts/fetch_settlement_reports.py
```

## 🛠️ Useful Commands

```bash
# Check database summary
python scripts/db_summary.py

# Run custom SQL query
python scripts/run_sql.py --sql "SELECT COUNT(*) FROM order_items"

# Show current configuration
python scripts/show_config.py

# Link ASINs across tables
python scripts/link_asins.py
```

## 📚 Documentation

- **[START_HERE.md](docs/START_HERE.md)** - Begin here for setup
- **[WALKTHROUGH.md](docs/WALKTHROUGH.md)** - Detailed step-by-step guide
- **[QUICK_START.md](docs/QUICK_START.md)** - Quick reference
- **[DBEAVER_SETUP.md](docs/DBEAVER_SETUP.md)** - Database viewer setup

## 🔐 Security

- Never commit `.env` file (contains API credentials)
- RDS credentials are stored in environment variables only
- Raw API responses are cached locally for debugging

## 📞 Support

For issues or questions, check the documentation in the `docs/` folder.

---

**Last Updated**: November 2025  
**Version**: 1.0  
**Status**: Production Ready ✅
