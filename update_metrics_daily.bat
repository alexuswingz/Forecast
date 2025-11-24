@echo off
echo ============================================================
echo Daily Metrics Update
echo ============================================================
echo.
echo Updating last 7 days of metrics...
echo (run this after importing fresh data each day)
echo.

python scripts\update_daily_metrics.py --days 7

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo Daily update complete!
    echo ============================================================
) else (
    echo.
    echo ERROR: Update failed!
    pause
    exit /b 1
)


