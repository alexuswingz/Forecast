@echo off
echo ============================================================
echo Setting Up Fast Daily Metrics System
echo ============================================================
echo.
echo This will:
echo   1. Create daily_product_metrics table
echo   2. Backfill historical data (this may take 10-30 minutes)
echo   3. Prepare Lambda function for deployment
echo.
pause

echo.
echo [STEP 1/3] Creating daily_product_metrics table...
python scripts\create_daily_metrics_table.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create table!
    pause
    exit /b 1
)

echo.
echo [STEP 2/3] Backfilling historical data...
echo This will take several minutes depending on data size...
python scripts\backfill_daily_metrics.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to backfill data!
    pause
    exit /b 1
)

echo.
echo [STEP 3/3] Packaging Lambda function...
cd lambda_forecast
if exist ..\forecast-lambda.zip del ..\forecast-lambda.zip
powershell -Command "Compress-Archive -Path lambda_function.py,ADD_INDEXES.sql,ADD_METRICS_INDEXES.sql -DestinationPath ..\forecast-lambda.zip -Force"
cd ..

echo.
echo ============================================================
echo SETUP COMPLETE!
echo ============================================================
echo.
echo Next steps:
echo   1. Deploy forecast-lambda.zip to AWS Lambda
echo   2. Test: GET /metrics/B0BRTK1P8Z?days=30
echo   3. Expected response time: 0.5-2 seconds (was 20+ seconds)
echo.
echo Daily maintenance:
echo   - Run: python scripts\update_daily_metrics.py
echo   - Or setup as cron job to run daily
echo.
pause


