# KPI Metrics Backend - Amazon Data Integration

A FastAPI backend service that pulls KPI/Metrics data from Amazon SP-API and Amazon Ads API, stores it in a database (SQLite or PostgreSQL/RDS), and provides REST API endpoints for data access.

## 🎯 Overview

This system:
- **Pulls data** from Amazon Selling Partner API (SP-API) and Amazon Advertising API
- **Stores metrics** in SQLite (local development) or PostgreSQL/RDS (production)
- **Provides REST API** endpoints to query and analyze KPIs
- **Scheduled syncs** to keep data up-to-date automatically
- **Tracks data from 2024** onwards as configured

## 📁 Project Structure

```
The1000backend/
├── main.py                           # FastAPI application with REST endpoints
├── config.py                         # Configuration management
├── database.py                       # Database connection and session management
├── models.py                         # SQLAlchemy database models
├── data_sync.py                      # Data synchronization service
├── scheduler.py                      # Scheduled job runner
├── excel_parser.py                   # Excel file parser (for metric definitions)
├── requirements.txt                  # Python dependencies
├── .env.template                     # Environment variables template
├── .gitignore                        # Git ignore file
├── integrations/
│   ├── __init__.py
│   ├── amazon_sp_api.py             # SP-API integration
│   └── amazon_ads_api.py            # Ads API integration
└── Data Bing Bong KPIs_Metrics (2).xlsx  # Metric definitions reference
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Amazon Seller Central account with SP-API access
- Amazon Advertising account with API access

### Step 1: Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Create a `.env` file (see `START_HERE.md` for a copy/paste block) and include:

**Required Configuration:**

1. **Amazon SP-API Credentials**
   - Go to [Amazon SP-API Developer Console](https://developer-docs.amazon.com/sp-api/docs/registering-your-application)
   - Register your application
   - Get: `SP_API_CLIENT_ID`, `SP_API_CLIENT_SECRET`, `SP_API_REFRESH_TOKEN`
   - Provision an IAM role/user with Selling Partner access
   - Add: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `SP_API_ROLE_ARN`, `SP_API_REGION`

2. **Amazon Ads API Credentials**
   - Go to [Amazon Advertising API](https://advertising.amazon.com/API/docs/en-us/get-started/how-to-use-api)
   - Register for API access
   - Get: `ADS_API_CLIENT_ID`, `ADS_API_CLIENT_SECRET`, `ADS_API_REFRESH_TOKEN`, `ADS_API_PROFILE_ID`

### Step 3: Initialize Database

```bash
# This will create the SQLite database and tables
python -c "from database import init_db; init_db()"
```

### Step 4: Run Initial Data Sync

```bash
# Full backfill (child metrics + inventory + KPIs)
python data_sync.py --start-date 2024-01-01 --end-date 2024-12-31

# Or incremental refresh (default 7 days)
python data_sync.py --job incremental --days 3
```

This will:
- Connect to Amazon SP-API (Orders, Sales, Reports) and Ads API
- Request the Business Reports “Detail Page Sales and Traffic by Child Item”
- Request FBA + AWD inventory reports
- Fetch data from `DATA_START_DATE` (default: 2024-01-01) to now
- Store child-level sales metrics, inventory buckets, and KPI summaries in the database

### Step 5: Start the API Server

```bash
# Start FastAPI server
python main.py

# Or use uvicorn directly
uvicorn main:app --reload --port 8000
```

The API will be available at: `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

## 📊 API Endpoints

### Health Check
- `GET /` - API status and health check

### Metrics
- `GET /api/metrics` - Get KPI metrics with filters
  - Query params: `start_date`, `end_date`, `category`, `metric_name`, `limit`, `offset`
- `GET /api/metrics/{metric_id}` - Get specific metric by ID
- `GET /api/metrics/summary/by-category` - Get metrics summary grouped by category
- `GET /api/metrics/categories` - Get list of all categories
- `GET /api/metrics/names` - Get list of all metric names

### Metric Definitions
- `GET /api/definitions` - Get metric definitions

### Data Sync
- `POST /api/sync/trigger` - Manually trigger data sync
  - Body: `{"days_back": 7}` or `{"start_date": "2024-01-01", "end_date": "2024-12-31"}`
- `GET /api/sync/status` - Get last sync status

### Example API Calls

```bash
# Get all metrics from last 30 days
curl "http://localhost:8000/api/metrics?start_date=2024-10-15"

# Get sales metrics
curl "http://localhost:8000/api/metrics?category=Sales"

# Get metrics summary by category
curl "http://localhost:8000/api/metrics/summary/by-category?start_date=2024-01-01"

# Trigger manual sync for last 7 days
curl -X POST "http://localhost:8000/api/sync/trigger" \
  -H "Content-Type: application/json" \
  -d '{"days_back": 7}'

# Check sync status
curl "http://localhost:8000/api/sync/status"
```

## ⏰ Scheduled Sync

To run automatic daily syncs:

```bash
# Run scheduler in background
python scheduler.py
```

The scheduler will:
- Run daily at 2 AM
- Sync last 7 days of data (to catch updates)
- Log all activities

## 🗄️ Database Schema

### KPIMetric Table
- `id` - Primary key
- `date` - Metric date
- `metric_name` - Name of the KPI
- `metric_category` - Category (Sales, Advertising, etc.)
- `value` - Metric value
- `target` - Target value (optional)
- `unit` - Unit of measurement
- `source` - Data source (SP-API, Ads API)
- `notes` - Additional notes

### MetricDefinition Table
### ChildTrafficMetric Table
- `date`, `child_asin`, `parent_asin`, `sku`
- `sessions`, `session_percentage`, `page_views`, `page_views_percentage`
- `buy_box_percentage`, `units_ordered`, `units_ordered_b2b`
- `ordered_product_sales`, `ordered_product_sales_b2b`, `total_order_items`
- `conversion_rate` (unit session %)

### InventorySnapshot Table
- `snapshot_date`, `asin`, `sku`, `fnsku`
- `fulfillment_program` (`FBA` or `AWD`)
- Quantity buckets: `total`, `available`, `reserved`, `inbound_working`, `inbound_shipped`, `inbound_receiving`, `research`
- `fulfillment_center_id`, `source_report_type`
- `id` - Primary key
- `metric_name` - Name of the metric
- `description` - Description
- `formula` - Calculation formula
- `category` - Category
- `data_type` - Data type

## 🔄 Switching to PostgreSQL/RDS

When ready for production with AWS RDS:

1. **Create RDS Instance**
   ```bash
   # Create PostgreSQL RDS instance in AWS Console
   # Note the endpoint, username, and password
   ```

2. **Update .env file**
   ```bash
   USE_SQLITE=false
   DB_HOST=your-rds-endpoint.rds.amazonaws.com
   DB_PORT=5432
   DB_NAME=kpi_metrics_db
   DB_USER=your_username
   DB_PASSWORD=your_password
   ```

3. **Install PostgreSQL driver**
   ```bash
   pip install psycopg2-binary
   ```

4. **Initialize RDS database**
   ```bash
   python -c "from database import init_db; init_db()"
   ```

## 📈 Available KPIs

### From SP-API:
- Total Orders / Revenue / Avg Order Value (Orders + Sales APIs)
- Child ASIN total sales, units sold, sessions, conversion rate (Business Reports)
- Buy Box %, Page Views/Sessions %, Unit Session %
- FBA + AWD inventory buckets (available, reserved, inbound working/shipped/receiving)
- Pending vs shipped orders

### From Ads API:
- Total Campaigns
- Active Campaigns
- Total Impressions
- Total Clicks
- Total Ad Spend
- Total Ad Sales
- CTR (Click-Through Rate)
- ACOS (Advertising Cost of Sale)
- ROAS (Return on Ad Spend)

## 🛠️ Development

### Run with Hot Reload
```bash
uvicorn main:app --reload --port 8000
```

### View Database
```bash
# Install SQLite viewer
pip install sqlite-web

# View database
sqlite_web kpi_metrics.db
```

### Run Manual Sync (inside Python)
```bash
python -c "from data_sync import DataSyncService; s = DataSyncService(); s.initialize_clients(); s.sync_all_data('2024-01-01', '2024-12-31')"
```

## 📝 Notes

1. **API Rate Limits**: Be aware of Amazon API rate limits. The sync service includes error handling for rate limit issues.

2. **Report Processing**: Some Amazon reports (especially Ads reports) are generated asynchronously. You may need to check report status and download later.

3. **Data Refresh**: The daily sync covers the last 7 days to catch any retroactive updates Amazon makes to data.

4. **Excel File**: The included Excel file contains metric definitions. You can parse it to populate the `metric_definitions` table using `excel_parser.py`.

## 🔐 Security

- Never commit `.env` file to git
- Use environment variables for all credentials
- When deploying to production, use AWS Secrets Manager or similar
- Enable RDS encryption at rest
- Use VPC security groups to restrict database access

## 🚢 Deployment Options

### Option 1: AWS EC2 + RDS
1. Create RDS PostgreSQL instance
2. Launch EC2 instance
3. Install Python and dependencies
4. Set up systemd service for FastAPI and scheduler
5. Use nginx as reverse proxy

### Option 2: AWS ECS/Fargate + RDS
1. Create Docker container
2. Deploy to ECS/Fargate
3. Connect to RDS
4. Use CloudWatch for logging

### Option 3: AWS Lambda + RDS
1. Package FastAPI with Mangum adapter
2. Deploy to Lambda
3. Use API Gateway
4. Scheduler via CloudWatch Events

## 📞 Troubleshooting

### Issue: SP-API authentication fails
- Verify your refresh token is valid
- Check that your LWA application has correct permissions
- Ensure marketplace ID matches your account region

### Issue: Ads API returns 401
- Get new access token by running the authentication flow
- Verify profile ID is correct for your account

### Issue: Database connection fails
- Check DATABASE_URL in config
- Ensure PostgreSQL service is running (if using PostgreSQL)
- Verify RDS security group allows your IP

## 📄 License

This project is for internal use.

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request

---

**Built with FastAPI, SQLAlchemy, and Amazon APIs** 🚀

