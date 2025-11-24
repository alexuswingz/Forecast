# Amazon Forecast Backend

> Production-ready backend system for Amazon Seller analytics, forecasting, and reporting with AWS Lambda integration

[![GitHub](https://img.shields.io/badge/GitHub-alexuswingz%2FForecast-blue)](https://github.com/alexuswingz/Forecast.git)

## 🚀 Features

- **Excel-Accurate Forecasting Engine** - Python implementation matching Excel AUTOFORECAST formulas
- **AWS Lambda API** - RESTful endpoints for charts, metrics, and forecasts
- **PostgreSQL RDS Integration** - Scalable data storage with daily metrics aggregation
- **Adjustable Velocity Weights** - Real-time forecast tuning via API parameters
- **Clickable Metrics Dashboard** - Interactive sales, ads, and traffic metrics
- **Weekly Metrics Endpoint** - Gregorian calendar-based reporting
- **Amazon SP-API & Ads API** - Automated data sync from Amazon

## 📊 Key Components

### 1. Forecasting Engine (`forecasting/`)
Excel-accurate forecasting with:
- Peak envelope smoothing
- Weighted moving averages (11-week pyramid)
- Seasonal patterns & velocity adjustments
- Visual output with charts

### 2. Lambda Functions (`lambda_forecast/`)
Production API endpoints:
- `/chart/{asin}` - Forecast chart data with adjustable weights
- `/sales-chart/{asin}` - Sales metrics (units, revenue, sessions, conversion)
- `/ads-chart/{asin}` - Advertising metrics (spend, ACOS, TACOS, clicks)
- `/weekly-metrics/{asin}` - Weekly aggregated data by year
- `/forecast` - Product forecasting data
- `/products` - Product management

### 3. Data Importers (`importers/`)
- Fulfillment shipments
- Ads reports
- Inventory ledgers
- Child traffic metrics
- Daily metrics aggregation

### 4. Database Scripts (`scripts/`)
- Daily metrics updates
- Forecast table creation
- Data migration to RDS
- Product status management

## 🛠️ Setup

### Prerequisites
```bash
- Python 3.8+
- PostgreSQL (local or RDS)
- AWS credentials (for Lambda deployment)
```

### Installation
```bash
# Clone repository
git clone https://github.com/alexuswingz/Forecast.git
cd Forecast

# Install dependencies
pip install -r forecasting/requirements.txt

# Configure database
cp config.py.example config.py
# Edit config.py with your database credentials
```

### Configuration
Edit `config.py`:
```python
DB_HOST = 'your-rds-endpoint.amazonaws.com'
DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASSWORD = 'your-password'
```

## 📈 Usage

### Generate Forecast
```bash
# Run forecasting for an ASIN
cd forecasting
python generate_forecast.py B0BRTK1P8Z

# With visualization
run_forecast_with_charts.bat
```

### Update Daily Metrics
```bash
python scripts/update_daily_metrics.py
```

### Deploy Lambda
```bash
cd lambda_forecast
# Package and upload forecast-lambda.zip to AWS Lambda
```

## 📚 Documentation

- [API Documentation](API_README.md) - Complete API reference
- [Forecast Calculations](CALCULATIONS.md) - Formula documentation
- [Excel Formula Comparison](EXCEL_V1.1_VS_V1.2_COMPARISON.md) - Formula accuracy verification
- [Clickable Metrics Guide](lambda_forecast/CLICKABLE_METRICS_GUIDE.md) - Frontend integration
- [Lambda Deployment](lambda_forecast/DEPLOYMENT.txt) - AWS deployment guide

## 🔄 Data Flow

```
Amazon APIs → Data Importers → PostgreSQL RDS
                                      ↓
                               Daily Metrics
                                      ↓
                            Forecasting Engine
                                      ↓
                              Lambda API Endpoints
                                      ↓
                               Frontend Dashboard
```

## 🎯 Key Endpoints

### Forecast Chart (with adjustable weights)
```
GET /chart/B0BRTK1P8Z?sales_velocity_weight=0.30&sv_velocity_weight=0.20
```

### Sales Metrics
```
GET /sales-chart/B0BRTK1P8Z?start_date=2024-01-01&end_date=2024-12-31
```

### Weekly Metrics
```
GET /weekly-metrics/B0BRTK1P8Z?year=2024
```

## 📊 Database Schema

### Main Tables
- `daily_product_metrics` - Aggregated daily data per ASIN
- `order_items` - Fulfillment data
- `ad_product_performance` - Advertising metrics
- `child_traffic_metrics` - Sessions & conversion
- `weekly_forecast_metrics` - Pre-computed forecasts
- `products` - Product catalog

## 🧪 Data Status

Check current data:
```bash
python scripts/check_data_status.py
```

Latest status (as of Nov 18, 2025):
- Latest data: November 14, 2025
- Total ASINs: 768
- Total metrics: 136,347 rows
- Days behind: 4

## 🔐 Security

Sensitive data excluded from repository:
- Fulfillment reports
- Raw data exports
- Customer information
- API credentials (use environment variables)

## 📝 License

Private repository - All rights reserved

## 🤝 Contributing

This is a private project. For access or questions, contact the repository owner.

---

**Built with** ❤️ **for Amazon Seller Analytics**
