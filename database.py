from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import Config

# Create database engine with appropriate settings
if Config.USE_SQLITE:
    # SQLite-specific configuration
    engine = create_engine(
        Config.DATABASE_URL,
        connect_args={"check_same_thread": False},  # Needed for SQLite with FastAPI
        echo=Config.APP_ENV == 'development'
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        Config.DATABASE_URL,
        pool_pre_ping=True,
        echo=Config.APP_ENV == 'development'
    )

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

