"""
Main FastAPI Application
Provides REST API endpoints for KPI/Metrics data
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel
import logging

from database import get_db, init_db
from models import KPIMetric, MetricDefinition
from config import Config
from data_sync import DataSyncService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="KPI Metrics API",
    description="API for fetching Amazon SP-API and Ads data KPIs",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API responses
class KPIMetricResponse(BaseModel):
    id: int
    date: str
    metric_name: str
    metric_category: Optional[str]
    value: Optional[float]
    target: Optional[float]
    unit: Optional[str]
    source: Optional[str]
    
    class Config:
        from_attributes = True


class MetricDefinitionResponse(BaseModel):
    id: int
    metric_name: str
    description: Optional[str]
    formula: Optional[str]
    category: Optional[str]
    
    class Config:
        from_attributes = True


class SyncRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    days_back: Optional[int] = 7


# Events
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")


# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "status": "running",
        "message": "KPI Metrics API",
        "version": "1.0.0",
        "database": "SQLite" if Config.USE_SQLITE else "PostgreSQL"
    }


# KPI Metrics endpoints
@app.get("/api/metrics", response_model=List[KPIMetricResponse])
async def get_metrics(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    metric_name: Optional[str] = Query(None, description="Filter by metric name"),
    limit: int = Query(100, ge=1, le=1000, description="Limit results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    Get KPI metrics with optional filters
    """
    query = db.query(KPIMetric)
    
    # Apply filters
    if start_date:
        query = query.filter(KPIMetric.date >= datetime.fromisoformat(start_date).date())
    
    if end_date:
        query = query.filter(KPIMetric.date <= datetime.fromisoformat(end_date).date())
    
    if category:
        query = query.filter(KPIMetric.metric_category == category)
    
    if metric_name:
        query = query.filter(KPIMetric.metric_name.ilike(f"%{metric_name}%"))
    
    # Order by date descending
    query = query.order_by(KPIMetric.date.desc(), KPIMetric.metric_name)
    
    # Apply pagination
    metrics = query.offset(offset).limit(limit).all()
    
    return [
        KPIMetricResponse(
            id=m.id,
            date=m.date.isoformat(),
            metric_name=m.metric_name,
            metric_category=m.metric_category,
            value=m.value,
            target=m.target,
            unit=m.unit,
            source=m.source
        )
        for m in metrics
    ]


@app.get("/api/metrics/{metric_id}", response_model=KPIMetricResponse)
async def get_metric_by_id(metric_id: int, db: Session = Depends(get_db)):
    """
    Get a specific metric by ID
    """
    metric = db.query(KPIMetric).filter(KPIMetric.id == metric_id).first()
    
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    return KPIMetricResponse(
        id=metric.id,
        date=metric.date.isoformat(),
        metric_name=metric.metric_name,
        metric_category=metric.metric_category,
        value=metric.value,
        target=metric.target,
        unit=metric.unit,
        source=metric.source
    )


@app.get("/api/metrics/summary/by-category")
async def get_metrics_summary_by_category(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get summary of metrics grouped by category
    """
    query = db.query(
        KPIMetric.metric_category,
        func.count(KPIMetric.id).label('count'),
        func.avg(KPIMetric.value).label('avg_value'),
        func.sum(KPIMetric.value).label('total_value')
    )
    
    if start_date:
        query = query.filter(KPIMetric.date >= datetime.fromisoformat(start_date).date())
    
    if end_date:
        query = query.filter(KPIMetric.date <= datetime.fromisoformat(end_date).date())
    
    results = query.group_by(KPIMetric.metric_category).all()
    
    return [
        {
            'category': r[0],
            'count': r[1],
            'average_value': float(r[2]) if r[2] else None,
            'total_value': float(r[3]) if r[3] else None
        }
        for r in results
    ]


@app.get("/api/metrics/categories")
async def get_categories(db: Session = Depends(get_db)):
    """
    Get list of all metric categories
    """
    categories = db.query(KPIMetric.metric_category).distinct().all()
    return [c[0] for c in categories if c[0]]


@app.get("/api/metrics/names")
async def get_metric_names(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get list of all metric names, optionally filtered by category
    """
    query = db.query(KPIMetric.metric_name).distinct()
    
    if category:
        query = query.filter(KPIMetric.metric_category == category)
    
    names = query.all()
    return [n[0] for n in names if n[0]]


# Metric Definitions endpoints
@app.get("/api/definitions", response_model=List[MetricDefinitionResponse])
async def get_metric_definitions(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get metric definitions
    """
    query = db.query(MetricDefinition)
    
    if category:
        query = query.filter(MetricDefinition.category == category)
    
    definitions = query.all()
    
    return [
        MetricDefinitionResponse(
            id=d.id,
            metric_name=d.metric_name,
            description=d.description,
            formula=d.formula,
            category=d.category
        )
        for d in definitions
    ]


# Data Sync endpoints
@app.post("/api/sync/trigger")
async def trigger_sync(sync_request: SyncRequest):
    """
    Manually trigger a data sync
    """
    try:
        logger.info("Manual sync triggered")
        
        sync_service = DataSyncService()
        sync_service.initialize_clients()
        
        if sync_request.days_back:
            sync_service.sync_incremental(days_back=sync_request.days_back)
        else:
            sync_service.sync_all_data(
                start_date=sync_request.start_date,
                end_date=sync_request.end_date
            )
        
        return {
            "status": "success",
            "message": "Data sync completed"
        }
        
    except Exception as e:
        logger.error(f"Error during manual sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sync/status")
async def get_sync_status(db: Session = Depends(get_db)):
    """
    Get status of last sync
    """
    # Get last synced date for each source
    sp_api_last = db.query(func.max(KPIMetric.date)).filter(
        KPIMetric.source == 'Amazon SP-API'
    ).scalar()
    
    ads_api_last = db.query(func.max(KPIMetric.date)).filter(
        KPIMetric.source == 'Amazon Ads API'
    ).scalar()
    
    total_metrics = db.query(func.count(KPIMetric.id)).scalar()
    
    return {
        "total_metrics": total_metrics,
        "last_sp_api_sync": sp_api_last.isoformat() if sp_api_last else None,
        "last_ads_api_sync": ads_api_last.isoformat() if ads_api_last else None,
        "data_start_date": Config.DATA_START_DATE
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=Config.API_PORT,
        reload=Config.APP_ENV == 'development'
    )



