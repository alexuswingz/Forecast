# Quick Start Guide - 5 Minutes to Running API

## ⚡ Super Fast Setup (Local Development)

### 1. Install Dependencies (1 minute)
```bash
cd "The1000backend"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure (2 minutes)
```bash
# Create .env file
copy .env.template .env

# Edit .env - MINIMUM required:
# For now, just use SQLite (already configured)
# Add Amazon credentials when ready
```

### 3. Initialize Database (30 seconds)
```bash
python -c "from database import init_db; init_db()"
```

### 4. Start API (30 seconds)
```bash
python main.py
```

### 5. Test It! (1 minute)
Open browser: `http://localhost:8000/docs`

✅ **You're running!**

---

## 🔑 Getting Amazon Credentials (Do this next)

### SP-API (Seller Central):
1. Visit: https://developer.sellercentral.amazon.com/
2. Register app → Get Client ID, Secret, Refresh Token
3. Add to `.env`

### Ads API:
1. Visit: https://advertising.amazon.com/
2. API Settings → Register app → Get credentials
3. Add to `.env`

---

## 🚀 First Data Sync

Once you have credentials:
```bash
# Sync last 7 days
python data_sync.py
```

Check results:
```bash
curl http://localhost:8000/api/metrics
```

---

## 📊 Quick API Tests

```bash
# Health check
curl http://localhost:8000/

# Get sync status
curl http://localhost:8000/api/sync/status

# Get all metrics
curl http://localhost:8000/api/metrics?limit=10

# Trigger sync (last 7 days)
curl -X POST http://localhost:8000/api/sync/trigger \
  -H "Content-Type: application/json" \
  -d "{\"days_back\": 7}"
```

---

## 🎯 Next: Move to RDS

When ready for production:
1. Create RDS PostgreSQL instance in AWS
2. Update `.env`:
   ```
   USE_SQLITE=false
   DB_HOST=your-rds-endpoint
   DB_USER=admin
   DB_PASSWORD=yourpassword
   ```
3. `pip install psycopg2-binary`
4. Reinitialize: `python -c "from database import init_db; init_db()"`

---

**Full details: See README.md and WALKTHROUGH.md**

