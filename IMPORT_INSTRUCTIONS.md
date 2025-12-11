# 📥 Import November Reports - Quick Instructions

## Files You Have:
1. **BusinessReport-11-29-25.xlsx** (188 KB) - Business report for whole November
2. **AWD Inventorr Ledger.xlsx** (357 KB) - AWD inventory for whole November

---

## ✅ What the Import Script Does Automatically:

- ✅ **Skips Nov 1-14** (already in database)
- ✅ **Imports only Nov 15-29** (new data)
- ✅ **Avoids ALL duplicates** using UPSERT logic
- ✅ **Safe to run multiple times** (won't create duplicates)

---

## 🚀 How to Import (3 Simple Steps):

### Step 1: Copy Files to Backend Folder
Move both files to your backend folder:
```
C:\Users\User\OneDrive\Desktop\The 1000 bananas\The1000backend\
```

### Step 2: Run Import Script
Open PowerShell or Command Prompt in the backend folder and run:

```bash
python scripts/import_november_reports.py "BusinessReport-11-29-25.xlsx" "AWD Inventorr Ledger.xlsx"
```

### Step 3: Aggregate Data
After successful import, run:
```bash
python scripts/update_daily_metrics.py
```

---

## 📋 Alternative: Use Drag-and-Drop Batch File

Double-click: **`import_november_data.bat`**

Then:
1. Drag and drop `BusinessReport-11-29-25.xlsx` → Press ENTER
2. Drag and drop `AWD Inventorr Ledger.xlsx` → Press ENTER
3. Wait for import to complete
4. Run aggregation: `python scripts/update_daily_metrics.py`

---

## 🔍 Expected Output:

```
================================================================================
IMPORTING BUSINESS REPORT (Sales & Traffic)
================================================================================

Reading: BusinessReport-11-29-25.xlsx
Total rows in file: 23,040  (768 ASINs × 30 days)
Date range in file: 2025-11-01 to 2025-11-29

Dates already in database: ['2025-11-01', '2025-11-02', ... '2025-11-14']
Rows after filtering duplicates: 11,520  (768 ASINs × 15 days)

[SUCCESS] Imported 11,520 rows from Business Report

================================================================================
IMPORTING AWD INVENTORY LEDGER
================================================================================

Reading: AWD Inventorr Ledger.xlsx
Total rows in file: 15,990
Date range in file: 2025-11-01 to 2025-11-29

Dates already in database: ['2025-11-01', '2025-11-02', ... '2025-11-14']
Rows after filtering duplicates: 7,995  (533 ASINs × 15 days)

[SUCCESS] Imported 7,995 AWD inventory records

================================================================================
IMPORT COMPLETE
================================================================================
Business Report rows imported: 11,520
AWD Inventory rows imported:   7,995
Total records imported:        19,515

[NEXT STEP] Run aggregation:
  python scripts/update_daily_metrics.py
```

---

## ✅ Verify Import Worked:

```bash
python scripts/check_data_status.py
```

Expected: **"0 days behind"** ✅

---

## 🆘 Troubleshooting:

### "File not found"
- Make sure files are in the backend folder
- Check file names match exactly (including spaces)

### "ModuleNotFoundError: pandas"
```bash
pip install pandas openpyxl psycopg2-binary python-dotenv
```

### "Connection refused"
- Check your `.env` file has correct database credentials
- Verify RDS is accessible

### "No new data to import"
- This is GOOD! It means the dates are already in the database
- The script correctly detected and skipped duplicates

---

## 📊 What Gets Imported:

### From Business Report:
- Sales amount per ASIN per day
- Units sold
- Sessions (traffic)
- Conversion rate
- Page views
- Order items

### From AWD Inventory:
- Available quantity per ASIN
- Warehouse locations
- Package quantities
- Carton counts

---

## 🎯 After Import:

Your database will be updated to **November 29, 2025** (today!)

Then your Lambda API will show:
- ✅ Latest forecast data
- ✅ Current inventory levels
- ✅ Up-to-date sales metrics
- ✅ Real-time conversion rates

---

**Ready to import? Follow the 3 steps above!** 🚀







