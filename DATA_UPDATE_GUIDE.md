# 📊 Data Update Guide - Complete Checklist

**Last Check**: November 29, 2025  
**Database Status**: 15 days behind (last updated November 14, 2025)

---

## 🔍 Current Data Status

### Sales & Metrics Data
- **Status**: ⚠️ **15 DAYS BEHIND**
- **Latest Date**: November 14, 2025
- **Missing**: November 15-29, 2025
- **Total Rows**: 136,347 metrics across 768 ASINs
- **Date Range**: April 8, 2024 → November 14, 2025

### Inventory Data

#### FBA Inventory
- **Status**: ⚠️ **15 DAYS BEHIND**
- **Latest Snapshot**: November 14, 2025
- **Unique ASINs**: 748
- **Total Available**: 2,605,564 units
- **Total Reserved**: 17,378 units
- **Total Inbound**: 30,919 units
- **Grand Total**: 2,648,184 units

#### AWD Inventory (Amazon Warehousing & Distribution)
- **Status**: ⚠️ **18 DAYS BEHIND**
- **Latest Snapshot**: November 11, 2025
- **Unique ASINs**: 533
- **Total Available**: 53,684,265 units
- **Total Reserved**: 0 units
- **Total Inbound**: 0 units
- **Grand Total**: 53,684,265 units

---

## 📥 What You Need to Download from Amazon

To bring your database up to date (through November 29, 2025), download these **5 reports**:

---

### 1️⃣ Business Reports - Sales & Traffic Data

**📍 Location**: Seller Central → Reports → Business Reports → Detail Page Sales and Traffic

**Settings**:
- Report Type: **"Detail Page Sales and Traffic by Child Item"**
- Report Period: **Daily**
- Date Range: **November 15, 2025 to November 29, 2025**
- Format: **CSV**
- Expected filename: `DetailPageSalesTrafficByChildItem_*.csv`

**Contains**:
- Sales revenue per ASIN
- Units sold
- Sessions (page views)
- Conversion rate
- Units ordered
- Order product sales

**Import Command**:
```bash
python importers/import_child_traffic.py "path/to/DetailPageSalesTrafficByChildItem.csv"
```

---

### 2️⃣ Advertising Reports - Sponsored Products

**📍 Location**: Seller Central → Advertising → Campaign Manager → Reporting

**Settings**:
- Report Type: **"Sponsored Products - Advertised Product Report"**
- Attribution: **14-day click, 1-day view**
- Date Range: **November 15, 2025 to November 29, 2025**
- Segment: **All campaigns**
- Format: **XLSX** or **CSV**
- Expected filename: `Sponsored_Products_Advertised_Product_Report_*.xlsx`

**Contains**:
- Ad spend per ASIN
- Ad sales
- Ad orders
- Impressions
- Clicks
- ACOS (Advertising Cost of Sales)
- CPC (Cost Per Click)

**Import Command**:
```bash
python importers/import_ads_report.py "path/to/Sponsored_Products_Advertised_Product_Report.xlsx"
```

---

### 3️⃣ Fulfillment Reports - Order Data

**📍 Location**: Seller Central → Reports → Fulfillment → All Orders

**Settings**:
- Report Type: **"Amazon Fulfilled Shipments"** or **"All Orders"**
- Date Range: **November 15, 2025 to November 29, 2025**
- Format: **CSV**
- Expected filename: `[Order Number].csv` or `AmazonFulfilledShipments_*.csv`

**Contains**:
- Order items
- Purchase dates
- Shipment dates
- Quantities
- Revenue per order line

**Import Command**:
```bash
python importers/import_fulfillment_shipments.py "path/to/fulfillment_report.csv"
```

---

### 4️⃣ FBA Inventory Report

**📍 Location**: Seller Central → Reports → Fulfillment → Amazon Fulfilled Inventory

**Settings**:
- Report Type: **"FBA Inventory"** or **"Manage FBA Inventory"**
- Date: **Today (November 29, 2025)** - this is a snapshot, not a date range
- Format: **CSV** or **TSV**
- Expected filename: `FBAInventory_*.csv`

**Contains**:
- Available quantity per ASIN/SKU
- Reserved quantity
- Inbound working quantity
- Inbound shipped quantity
- Inbound receiving quantity
- Total quantity
- Fulfillment center locations

**Import Command**:
```bash
python importers/import_fba_inventory_report.py "path/to/FBAInventory.csv"
```

---

### 5️⃣ AWD Inventory Report (Optional - if using AWD)

**📍 Location**: Seller Central → Reports → AWD → Inventory

**Settings**:
- Report Type: **"AWD Inventory"**
- Date: **Today (November 29, 2025)** - snapshot
- Format: **CSV**
- Expected filename: `AWDInventory_*.csv`

**Contains**:
- AWD available quantity
- AWD reserved quantity
- AWD distribution center locations

**Import Command**:
```bash
python importers/import_awd_inventory_report.py "path/to/AWDInventory.csv"
```

---

## 🔄 Step-by-Step Import Process

### Step 1: Download All Reports
Download all 5 reports listed above and save them to a folder (e.g., `C:\Downloads\Amazon_Reports_2025-11-29\`)

### Step 2: Import Sales & Traffic Data
```bash
cd "C:\Users\User\OneDrive\Desktop\The 1000 bananas\The1000backend"
python importers/import_child_traffic.py "C:\Downloads\Amazon_Reports_2025-11-29\DetailPageSalesTrafficByChildItem.csv"
```

### Step 3: Import Advertising Data
```bash
python importers/import_ads_report.py "C:\Downloads\Amazon_Reports_2025-11-29\Sponsored_Products_Advertised_Product_Report.xlsx"
```

### Step 4: Import Fulfillment Data
```bash
python importers/import_fulfillment_shipments.py "C:\Downloads\Amazon_Reports_2025-11-29\fulfillment_report.csv"
```

### Step 5: Import FBA Inventory
```bash
python importers/import_fba_inventory_report.py "C:\Downloads\Amazon_Reports_2025-11-29\FBAInventory.csv"
```

### Step 6: Import AWD Inventory (if applicable)
```bash
python importers/import_awd_inventory_report.py "C:\Downloads\Amazon_Reports_2025-11-29\AWDInventory.csv"
```

### Step 7: Aggregate into Daily Metrics
This is the **most important step** - it combines all the raw data into the `daily_product_metrics` table used by your forecasting and APIs:

```bash
python scripts/update_daily_metrics.py
```

**What this does**:
- Joins order items, ad performance, and traffic data
- Calculates daily totals per ASIN
- Computes conversion rates, TACOS, ACOS, CPC
- Updates the `daily_product_metrics` table

### Step 8: Verify Data Updated
```bash
python scripts/check_data_status.py
```

Expected output: **"0 days behind"** ✅

---

## 🤖 Automation Options

### Option 1: Weekly Manual Updates
Set a calendar reminder to download and import reports every **Monday morning**:
1. Download all 5 reports for the previous week
2. Run the 6 import commands
3. Run `update_daily_metrics.py`

### Option 2: SP-API Automation (Recommended)
The codebase already has SP-API integration (`integrations/amazon_sp_api.py`):

**Setup**:
1. Get SP-API credentials from Amazon Seller Central
2. Configure `.env` with your credentials:
   ```
   SP_API_REFRESH_TOKEN=your_refresh_token
   SP_API_CLIENT_ID=your_client_id
   SP_API_CLIENT_SECRET=your_client_secret
   ```
3. Set up daily scheduled task (Windows Task Scheduler):
   ```bash
   python scheduler.py
   ```

**Benefits**:
- ✅ Fully automated daily updates
- ✅ No manual downloads needed
- ✅ Always up to date
- ✅ Runs at 2 AM daily

---

## 📋 Quick Reference Commands

### Check Current Status
```bash
# Check sales/metrics data status
python scripts/check_data_status.py

# Check inventory status
python scripts/check_inventory_status.py
```

### Import Data
```bash
# Import all data types
python importers/import_child_traffic.py <sales_report.csv>
python importers/import_ads_report.py <ads_report.xlsx>
python importers/import_fulfillment_shipments.py <fulfillment.csv>
python importers/import_fba_inventory_report.py <fba_inventory.csv>
python importers/import_awd_inventory_report.py <awd_inventory.csv>

# Aggregate everything
python scripts/update_daily_metrics.py
```

### Verify Updates
```bash
# Verify data is up to date
python scripts/check_data_status.py

# Check specific ASIN
python -c "import psycopg2; from psycopg2.extras import RealDictCursor; import os; from dotenv import load_dotenv; load_dotenv(); conn = psycopg2.connect(host=os.getenv('DB_HOST'), database=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD')); cur = conn.cursor(cursor_factory=RealDictCursor); cur.execute('SELECT date, sales_amount, units_sold FROM daily_product_metrics WHERE asin = %s ORDER BY date DESC LIMIT 5', ('B0BRTK1P8Z',)); [print(f\"{r['date']}: ${r['sales_amount']:.2f}, {r['units_sold']} units\") for r in cur.fetchall()]"
```

---

## 🎯 Top 20 ASINs by Inventory (as of Nov 14, 2025)

| ASIN | SKU | Available | Reserved | Inbound | Total |
|------|-----|-----------|----------|---------|-------|
| B0BRTK1P8Z | HPMONST8OZ-FBA-UPC-0 | 2,825 | 1,132 | 2,285 | 6,018 |
| B0BRTKV4TC | LIQUIDPF8OZ-FBA-UPC- | 1,827 | 1,353 | 2,700 | 5,627 |
| B0CPGGCRT8 | XMASCACTUS8OZ-FBA-UP | 159 | 915 | 3,160 | 4,031 |
| B0BRTJB518 | HPINDOOR8OZ-FBA-UPC- | 893 | 799 | 1,359 | 2,811 |
| B0BRTJGR33 | HPFIG8OZ-FBA-UPC-012 | 811 | 249 | 1,860 | 2,748 |
| B0C73SNJCH | LEMON8OZ-FBA-UPC-052 | 982 | 768 | 966 | 2,572 |
| B0C73PVKDR | PLUMERIA8OZ-FBA-UPC- | 2,123 | 151 | 25 | 2,150 |
| B0CT668F19 | HPSIL8OZ-FBA-UPC-012 | 650 | 202 | 1,092 | 1,904 |
| B0BRTJ4PLB | HPSUCC8OZ-FBA-UPC-01 | 722 | 422 | 720 | 1,858 |
| B0DQS6N546 | TPS-JAPANESEMAPLE-8O | 1,780 | 194 | 0 | 1,842 |

---

## ⚠️ Important Notes

1. **Report Date Ranges**: Sales/ads/fulfillment use date ranges (Nov 15-29), but inventory reports are **snapshots** (just Nov 29).

2. **File Formats**: 
   - Business Reports: CSV
   - Ads Reports: XLSX or CSV
   - Fulfillment: CSV
   - Inventory: CSV or TSV

3. **Import Order**: The order doesn't matter for the individual imports, but **you must run `update_daily_metrics.py` AFTER all imports** to aggregate the data.

4. **Data Gaps**: If you have gaps (e.g., missing Nov 10-14), download reports for those date ranges too.

5. **Daily Recommended**: To stay current, download reports **daily** or set up SP-API automation.

---

## 📞 Troubleshooting

### "No data imported"
- Check date range matches the filename
- Verify CSV format is correct
- Check file encoding (should be UTF-8)

### "Duplicate key error"
- Data already exists for that date
- Safe to ignore if re-importing same data

### "Table does not exist"
- Run database migrations: `python models.py`
- Or check RDS connection settings

### "Connection refused"
- Check `.env` has correct DB_HOST, DB_USER, DB_PASSWORD
- Verify RDS security group allows your IP

---

**Need Help?** Check the logs in the terminal output or contact the repository owner.

**Last Updated**: November 29, 2025










