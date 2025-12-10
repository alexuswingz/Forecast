@echo off
echo ================================================================================
echo IMPORTING NOVEMBER REPORTS WITH DUPLICATE FILTERING
echo ================================================================================
echo.
echo This script will automatically:
echo   1. Skip Nov 1-14 (already in database)
echo   2. Import only Nov 15-29 (new data)
echo   3. Avoid all duplicates using UPSERT
echo.
echo.
echo Drag and drop your Business Report file here, then press ENTER:
set /p BUSINESS_REPORT=
echo.
echo Drag and drop your AWD Inventory Ledger file here, then press ENTER:
set /p AWD_INVENTORY=
echo.
echo Starting import...
echo.

python scripts/import_november_reports.py %BUSINESS_REPORT% %AWD_INVENTORY%

echo.
echo ================================================================================
echo Import complete! Check output above for any errors.
echo.
echo NEXT STEP: Run data aggregation
echo   python scripts/update_daily_metrics.py
echo ================================================================================
echo.
pause

