@echo off
REM Quick Start - Run Forecast with Charts
echo ======================================
echo  Forecasting System with Charts
echo ======================================
echo.
echo Generating forecast and charts for Hydrangea (B0C73TDZCQ)...
echo.

python forecasting/visualize.py --asin B0C73TDZCQ --start-date 2024-05-01

echo.
echo ======================================
echo  DONE!
echo ======================================
echo.
echo Check forecasting/output/ for:
echo   - CSV files (historical, forecast, inventory_plan)
echo   - PNG charts (sales_forecast, smoothing_detail, inventory_plan, inventory_breakdown)
echo.
pause


