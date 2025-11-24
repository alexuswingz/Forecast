# Complete Walkthrough: Building KPI Metrics Backend with Amazon APIs

This walkthrough guides you through setting up a complete backend system to fetch Amazon data and serve it via REST APIs.

## 🎯 Project Goal

Create a backend that:
1. Pulls KPI/Metrics data from Amazon SP-API and Amazon Ads API
2. Stores data from 2024 onwards in a database
3. Provides REST API endpoints to fetch and analyze the data
4. Can scale from SQLite (local) to AWS RDS (production)

---

## 📋 Phase 1: Local Development Setup (1-2 hours)

### Step 1.1: Environment Setup

```bash
# Navigate to your project directory
cd "C:\Users\User\OneDrive\Desktop\The 1000 bananas\The1000backend"

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

### Step 1.2: Get Amazon API Credentials

#### SP-API Credentials:
1. Go to https://developer.sellercentral.amazon.com/
2. Click "Add new app client"
3. Fill in app details and submit
4. Once approved, get:
   - LWA Client ID
   - LWA Client Secret
   - Refresh Token (requires OAuth flow)

**Getting Refresh Token:**
```bash
# Use this URL structure (replace YOUR_CLIENT_ID)
https://sellercentral.amazon.com/apps/authorize/consent?application_id=YOUR_CLIENT_ID&version=beta

# After authorization, you'll get a code
# Exchange it for refresh token using:
curl -X POST https://api.amazon.com/auth/o2/token \
  -d "grant_type=authorization_code" \
  -d "code=YOUR_CODE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

#### Ads API Credentials:
1. Go to https://advertising.amazon.com/
2. Navigate to API section in settings
3. Register your application
4. Get:
   - Client ID
   - Client Secret
   - Refresh Token (via OAuth flow)
   - Profile ID (from your account)

### Step 1.3: Configure Environment

```bash
# Create .env file from template
copy .env.template .env

# Open .env in notepad and fill in:
notepad .env
```

**Minimum required configuration:**
```env
# Start with SQLite for local testing
USE_SQLITE=true
SQLITE_DB_PATH=kpi_metrics.db

# Amazon SP-API (LWA)
SP_API_REFRESH_TOKEN=Atzr|IwEBIJxxxxx
SP_API_CLIENT_ID=amzn1.application-oa2-client.xxxxx
SP_API_CLIENT_SECRET=your_secret_here

# Amazon SP-API (IAM)
AWS_ACCESS_KEY_ID=AKIAxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxx
SP_API_ROLE_ARN=arn:aws:iam::123456789012:role/YourSpApiRole
SP_API_REGION=us-east-1

# Amazon Ads API
ADS_API_CLIENT_ID=amzn1.application-oa2-client.xxxxx
ADS_API_CLIENT_SECRET=your_ads_secret_here
ADS_API_REFRESH_TOKEN=Atzr|IwEBIJxxxxx
ADS_API_PROFILE_ID=1234567890

# Data configuration
DATA_START_DATE=2024-01-01
```

### Step 1.4: Initialize Database

```bash
# Create database and tables
python -c "from database import init_db; init_db()"

# Verify database was created
dir kpi_metrics.db
```

### Step 1.5: Test API Connections

```python
# Create test_connections.py
python
>>> from integrations.amazon_sp_api import AmazonSPAPIClient
>>> client = AmazonSPAPIClient()
>>> # Try fetching orders (if credentials are correct)
>>> orders = client.get_orders('2024-01-01', '2024-01-07')
>>> print(f"Fetched {len(orders)} orders")
```

### Step 1.6: Run Initial Data Sync

```bash
# Pull child metrics + inventory for a specific range
python data_sync.py --start-date 2024-01-01 --end-date 2024-01-31

# Or keep the last few days fresh
python data_sync.py --job incremental --days 3

# Logs should show:
# "Fetching child ASIN metrics..."
# "Stored N child ASIN metric rows"
# "Stored N inventory snapshot rows"
```

### Step 1.7: Start API Server

```bash
# Start the FastAPI server
python main.py

# Or with auto-reload for development
uvicorn main:app --reload --port 8000
```

### Step 1.8: Test API Endpoints

Open browser and visit:
- `http://localhost:8000` - Health check
- `http://localhost:8000/docs` - Interactive API documentation
- `http://localhost:8000/api/metrics` - View stored metrics

**Test with curl:**
```bash
# Get sync status
curl http://localhost:8000/api/sync/status

# Get all metrics
curl http://localhost:8000/api/metrics?limit=10

# Get sales metrics
curl "http://localhost:8000/api/metrics?category=Sales"

# Get metrics from specific date range
curl "http://localhost:8000/api/metrics?start_date=2024-01-01&end_date=2024-12-31"

# Trigger manual sync
curl -X POST http://localhost:8000/api/sync/trigger -H "Content-Type: application/json" -d "{\"days_back\": 7}"
```

---

## 📊 Phase 2: Production Setup with AWS RDS (2-4 hours)

### Step 2.1: Create AWS RDS Instance

1. **Login to AWS Console**
   - Go to RDS service
   - Click "Create database"

2. **Configure Database**
   - Engine: PostgreSQL
   - Template: Free tier (for testing) or Production
   - DB instance identifier: `kpi-metrics-db`
   - Master username: `admin`
   - Master password: (choose strong password)
   - DB instance class: db.t3.micro (or larger)
   - Storage: 20 GB (SSD)
   - VPC: Default or create new
   - Public access: Yes (for testing, No for production)
   - Database name: `kpi_metrics_db`

3. **Security Group**
   - Create new security group: `kpi-metrics-sg`
   - Add inbound rule:
     - Type: PostgreSQL
     - Port: 5432
     - Source: Your IP (for testing) or specific IPs/VPC

4. **Wait for creation** (5-10 minutes)
   - Note the endpoint URL

### Step 2.2: Update Configuration for RDS

```bash
# Edit .env file
notepad .env

# Update these lines:
USE_SQLITE=false
DB_HOST=kpi-metrics-db.xxxxx.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=kpi_metrics_db
DB_USER=admin
DB_PASSWORD=your_strong_password

# Install PostgreSQL driver
pip install psycopg2-binary
```

### Step 2.3: Initialize RDS Database

```bash
# Initialize tables in RDS
python -c "from database import init_db; init_db()"

# If you have existing data in SQLite, you can migrate it:
# (Create a migration script if needed)
```

### Step 2.4: Test RDS Connection

```bash
# Test the connection
python -c "from database import SessionLocal; db = SessionLocal(); print('Connected to RDS successfully!')"

# Run sync with RDS
python data_sync.py

# Start API server with RDS
python main.py
```

---

## 🚀 Phase 3: Deployment Options

### Option A: Deploy to AWS EC2

1. **Launch EC2 Instance**
   ```bash
   # Launch Ubuntu 22.04 t2.small instance
   # Add security group allowing:
   # - Port 22 (SSH)
   # - Port 8000 (API)
   # - Port 80/443 (HTTP/HTTPS with nginx)
   ```

2. **Connect and Setup**
   ```bash
   ssh -i your-key.pem ubuntu@ec2-xx-xx-xx-xx.compute.amazonaws.com
   
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Python and dependencies
   sudo apt install python3-pip python3-venv nginx -y
   
   # Clone or upload your code
   cd /home/ubuntu
   # (upload your files via scp or git)
   
   # Setup virtual environment
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create .env file on EC2**
   ```bash
   nano .env
   # Paste your production configuration
   ```

4. **Create systemd service**
   ```bash
   sudo nano /etc/systemd/system/kpi-api.service
   ```
   
   ```ini
   [Unit]
   Description=KPI Metrics API
   After=network.target
   
   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/The1000backend
   Environment="PATH=/home/ubuntu/The1000backend/venv/bin"
   ExecStart=/home/ubuntu/The1000backend/venv/bin/python main.py
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   ```bash
   # Enable and start service
   sudo systemctl enable kpi-api
   sudo systemctl start kpi-api
   sudo systemctl status kpi-api
   ```

5. **Setup nginx reverse proxy**
   ```bash
   sudo nano /etc/nginx/sites-available/kpi-api
   ```
   
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```
   
   ```bash
   sudo ln -s /etc/nginx/sites-available/kpi-api /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

6. **Setup scheduler**
   ```bash
   sudo nano /etc/systemd/system/kpi-scheduler.service
   ```
   
   ```ini
   [Unit]
   Description=KPI Metrics Scheduler
   After=network.target
   
   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/The1000backend
   Environment="PATH=/home/ubuntu/The1000backend/venv/bin"
   ExecStart=/home/ubuntu/The1000backend/venv/bin/python scheduler.py
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   ```bash
   sudo systemctl enable kpi-scheduler
   sudo systemctl start kpi-scheduler
   ```

### Option B: Deploy to AWS ECS (Docker)

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.10-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY . .
   
   CMD ["python", "main.py"]
   ```

2. **Build and push to ECR**
   ```bash
   # Build image
   docker build -t kpi-metrics-api .
   
   # Tag and push to ECR
   aws ecr create-repository --repository-name kpi-metrics-api
   docker tag kpi-metrics-api:latest xxxxx.dkr.ecr.us-east-1.amazonaws.com/kpi-metrics-api:latest
   docker push xxxxx.dkr.ecr.us-east-1.amazonaws.com/kpi-metrics-api:latest
   ```

3. **Create ECS Task Definition and Service**
   - Use AWS Console or CLI to create ECS cluster
   - Create task definition with your container image
   - Set environment variables from .env
   - Create service with desired task count

---

## 📈 Phase 4: Monitoring and Maintenance

### Setup Logging

```python
# Add to main.py for production logging
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler('api.log', maxBytes=10000000, backupCount=5)
handler.setLevel(logging.INFO)
logger.addHandler(handler)
```

### Monitor Sync Status

```bash
# Check last sync via API
curl http://your-domain.com/api/sync/status

# Check logs
tail -f api.log

# Check systemd service logs
sudo journalctl -u kpi-api -f
```

### Backup Database

```bash
# For SQLite
cp kpi_metrics.db kpi_metrics_backup_$(date +%Y%m%d).db

# For RDS - use AWS Backup or automated snapshots
aws rds create-db-snapshot \
  --db-instance-identifier kpi-metrics-db \
  --db-snapshot-identifier kpi-metrics-snapshot-$(date +%Y%m%d)
```

---

## 🔍 Troubleshooting Guide

### Common Issues:

**1. SP-API Authentication Error**
```
Error: 403 Forbidden
Solution: 
- Check refresh token is valid
- Verify app has correct permissions in Seller Central
- Token may have expired, generate new one
```

**2. Ads API 401 Unauthorized**
```
Solution:
- Run OAuth flow again to get fresh refresh token
- Verify profile ID matches your account
- Check client ID and secret are correct
```

**3. Database Connection Failed**
```
Solution:
- Check RDS security group allows your IP
- Verify endpoint URL is correct
- Test connection with psql client
- Check credentials in .env
```

**4. No Data Being Synced**
```
Solution:
- Check date ranges are valid
- Verify API credentials are working
- Check logs for specific errors
- Test API connections individually
```

**5. API Server Won't Start**
```
Solution:
- Check port 8000 is not in use
- Verify all dependencies are installed
- Check .env file exists and is valid
- Look for syntax errors in code
```

---

## ✅ Verification Checklist

- [ ] Virtual environment created and activated
- [ ] All dependencies installed
- [ ] Amazon SP-API credentials obtained
- [ ] Amazon Ads API credentials obtained
- [ ] .env file configured correctly
- [ ] Database initialized successfully
- [ ] API connections tested
- [ ] Initial data sync completed
- [ ] API server starts without errors
- [ ] Can access API documentation at /docs
- [ ] Can fetch metrics via API endpoints
- [ ] (Production) RDS instance created
- [ ] (Production) API deployed to EC2/ECS
- [ ] (Production) Scheduler running
- [ ] (Production) Monitoring setup

---

## 📞 Next Steps

1. **Parse Excel file** to extract metric definitions
2. **Create dashboards** using the API data
3. **Add more metrics** from SP-API and Ads API
4. **Setup alerts** for critical KPIs
5. **Add authentication** to API endpoints
6. **Create frontend** to visualize data

---

## 🎓 Key Concepts

- **SP-API**: Amazon Selling Partner API - provides order, sales, and product data
- **Ads API**: Amazon Advertising API - provides campaign and advertising performance data
- **SQLAlchemy**: Python ORM for database operations
- **FastAPI**: Modern web framework for building APIs
- **APScheduler**: Python job scheduling library
- **RDS**: AWS Relational Database Service (managed PostgreSQL)

---

**You now have a complete backend system ready to scale from local development to production!** 🎉

