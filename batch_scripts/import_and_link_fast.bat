@echo off
echo ========================================
echo Starting Fulfillment Import and ASIN Linking (Fast Mode)
echo ========================================
echo.

cd /d "C:\Users\User\OneDrive\Desktop\The 1000 bananas\The1000backend"

echo [STEP 1/4] Dropping order_items table for fast reset...
echo.
python scripts/run_sql.py --sql "DROP TABLE IF EXISTS order_items"

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to drop table!
    pause
    exit /b 1
)

echo [STEP 2/4] Recreating order_items table...
echo.
python -c "from database import init_db; init_db(); print('[OK] Tables created')"

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create table!
    pause
    exit /b 1
)

echo.
echo [STEP 3/4] Importing Fulfillment Reports (no delete, fresh table)...
echo This will take 30-60 minutes. Each chunk prints progress every 30-60 seconds.
echo.
python -u import_fulfillment_shipments.py --folder "Fulfillment reports" --chunk-size 5000

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Fulfillment import failed!
    pause
    exit /b 1
)

echo.
echo [STEP 4/4] Linking all ASINs across orders, inventory, and ads...
echo.
python scripts/link_asins.py

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: ASIN linking failed!
    pause
    exit /b 1
)

echo.
echo [FINAL CHECK] Verifying row counts...
echo.
python scripts/run_sql.py --sql "SELECT COUNT(*) FROM order_items"
python scripts/run_sql.py --sql "SELECT COUNT(*) AS missing FROM order_items WHERE asin IS NULL OR asin = ''"

echo.
echo ========================================
echo IMPORT AND LINKING COMPLETE!
echo ========================================
echo.
pause

