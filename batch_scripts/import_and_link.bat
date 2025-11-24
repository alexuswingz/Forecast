@echo off
echo ========================================
echo Starting Fulfillment Import and ASIN Linking
echo ========================================
echo.

cd /d "C:\Users\User\OneDrive\Desktop\The 1000 bananas\The1000backend"

echo [STEP 1/3] Importing Fulfillment Reports...
echo This will take 30-60 minutes. Each chunk prints progress.
echo.
python -u import_fulfillment_shipments.py --folder "Fulfillment reports" --chunk-size 50000 --reset

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Fulfillment import failed!
    pause
    exit /b 1
)

echo.
echo [STEP 2/3] Linking all ASINs across orders, inventory, and ads...
echo.
python scripts/link_asins.py

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: ASIN linking failed!
    pause
    exit /b 1
)

echo.
echo [STEP 3/3] Verifying final row counts...
echo.
python scripts/run_sql.py --sql "SELECT COUNT(*) FROM order_items"
python scripts/run_sql.py --sql "SELECT COUNT(*) AS missing FROM order_items WHERE asin IS NULL OR asin = ''"

echo.
echo ========================================
echo IMPORT AND LINKING COMPLETE!
echo ========================================
echo.
pause

