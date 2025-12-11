@echo off
cls
echo.
echo ================================================================================
echo   IMPORT NOVEMBER REPORTS - AUTOMATIC DUPLICATE FILTERING
echo ================================================================================
echo.
echo   This will import your November reports and automatically:
echo   - Skip Nov 1-14 (already in database)
echo   - Import only Nov 15-29 (new data)
echo   - Avoid all duplicates
echo.
echo   Files needed in this folder:
echo   1. BusinessReport-11-29-25.xlsx
echo   2. AWD Inventorr Ledger.xlsx
echo.
echo ================================================================================
echo.
pause

echo.
echo Checking for files...
echo.

if not exist "BusinessReport-11-29-25.xlsx" (
    echo [ERROR] BusinessReport-11-29-25.xlsx not found!
    echo Please copy the file to this folder.
    pause
    exit /b 1
)

if not exist "AWD Inventorr Ledger.xlsx" (
    echo [ERROR] AWD Inventorr Ledger.xlsx not found!
    echo Please copy the file to this folder.
    pause
    exit /b 1
)

echo [OK] Both files found!
echo.
echo Starting import...
echo.

python scripts/import_november_reports.py "BusinessReport-11-29-25.xlsx" "AWD Inventorr Ledger.xlsx"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================================================
    echo   IMPORT SUCCESSFUL!
    echo ================================================================================
    echo.
    echo   Next step: Run data aggregation
    echo.
    echo   Command: python scripts/update_daily_metrics.py
    echo.
    echo ================================================================================
) else (
    echo.
    echo ================================================================================
    echo   IMPORT FAILED - Check errors above
    echo ================================================================================
)

echo.
pause







