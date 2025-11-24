@echo off
echo ============================================================
echo Creating Database Indexes for Performance
echo ============================================================
echo.
echo This will create indexes on your RDS database to speed up queries.
echo Expected time: 5-10 minutes
echo.
pause

python lambda_forecast\run_indexes.py

echo.
echo ============================================================
echo Verifying indexes...
echo ============================================================
python lambda_forecast\verify_indexes.py

echo.
pause


