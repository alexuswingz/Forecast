import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # Database Configuration
    USE_SQLITE = os.getenv('USE_SQLITE', 'true').lower() == 'true'
    
    # SQLite Configuration
    SQLITE_DB_PATH = os.getenv('SQLITE_DB_PATH', 'kpi_metrics.db')
    
    # PostgreSQL/RDS Configuration (for production)
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'kpi_metrics_db')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    
    # SQLAlchemy Database URI
    if USE_SQLITE:
        DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH}"
    else:
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Application
    APP_ENV = os.getenv('APP_ENV', 'development')
    API_PORT = int(os.getenv('API_PORT', 8000))
    
    # CORS
    ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:8080"]
    
    # Amazon SP-API Configuration
    SP_API_REFRESH_TOKEN = os.getenv('SP_API_REFRESH_TOKEN')
    SP_API_CLIENT_ID = os.getenv('SP_API_CLIENT_ID')
    SP_API_CLIENT_SECRET = os.getenv('SP_API_CLIENT_SECRET')
    SP_API_MARKETPLACE = os.getenv('SP_API_MARKETPLACE', 'US')  # Accepts marketplace code or ID
    SP_API_REGION = os.getenv('SP_API_REGION', 'us-east-1')
    SP_API_ROLE_ARN = os.getenv('SP_API_ROLE_ARN')
    SP_API_AWS_SESSION_NAME = os.getenv('SP_API_AWS_SESSION_NAME', 'sp-api-session')
    
    # Amazon Ads API Configuration
    ADS_API_CLIENT_ID = os.getenv('ADS_API_CLIENT_ID')
    ADS_API_CLIENT_SECRET = os.getenv('ADS_API_CLIENT_SECRET')
    ADS_API_REFRESH_TOKEN = os.getenv('ADS_API_REFRESH_TOKEN')
    ADS_API_PROFILE_ID = os.getenv('ADS_API_PROFILE_ID')
    ADS_API_REGION = os.getenv('ADS_API_REGION', 'NA')  # NA, EU, or FE
    
    # AWS Configuration (for RDS)
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID') or os.getenv('AWS_ACCESS_KEY')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY') or os.getenv('AWS_SECRET_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    
    # Data Sync Configuration
    SYNC_INTERVAL_HOURS = int(os.getenv('SYNC_INTERVAL_HOURS', 24))
    DATA_START_DATE = os.getenv('DATA_START_DATE', '2024-01-01')
    RAW_OUTPUT_DIR = os.getenv('RAW_OUTPUT_DIR', 'raw_exports')

