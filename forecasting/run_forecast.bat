@echo off
REM Quick Start - Run Forecast for Hydrangea
echo ======================================
echo  Forecasting System - Quick Start
echo ======================================
echo.
echo Generating forecast for Hydrangea (B0C73TDZCQ)...
echo.

python forecasting/generate_forecast.py --asin B0C73TDZCQ --start-date 2024-05-01

echo.
echo ======================================
echo  FORECAST COMPLETE!
echo ======================================
echo.
echo Check forecasting/output/ for results:
echo   - historical_*.csv
echo   - forecast_*.csv
echo   - inventory_plan_*.csv
echo.
pause


