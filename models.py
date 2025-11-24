"""
SQLAlchemy ORM models for database tables
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, BigInteger, Boolean, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class DailyProductMetric(Base):
    """Pre-aggregated daily metrics for fast dashboard queries"""
    __tablename__ = 'daily_product_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # Sales metrics
    units_sold = Column(Integer, default=0)
    sales_amount = Column(Float, default=0.0)
    orders_count = Column(Integer, default=0)
    
    # Traffic metrics
    sessions = Column(Integer, default=0)
    page_views = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    
    # Advertising metrics
    ad_spend = Column(Float, default=0.0)
    ad_sales = Column(Float, default=0.0)
    ad_clicks = Column(Integer, default=0)
    ad_impressions = Column(Integer, default=0)
    ad_orders = Column(Integer, default=0)
    
    # Calculated on insert
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Unique constraint
    __table_args__ = (
        {'extend_existing': True},
    )


class KPIMetric(Base):
    """Weekly aggregated KPI metrics (legacy)"""
    __tablename__ = 'kpi_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    asin = Column(String, nullable=True)
    sku = Column(String, nullable=True)
    parent_asin = Column(String, nullable=True)
    product_name = Column(String, nullable=True)
    units = Column(Integer, default=0)
    sales = Column(Float, default=0.0)
    orders = Column(Integer, default=0)
    ad_spend = Column(Float, default=0.0)
    ad_sales = Column(Float, default=0.0)
    tacos = Column(Float, default=0.0)
    sessions = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    source = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class OrderItem(Base):
    """Individual order line items from Fulfilled Shipments"""
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, nullable=False)
    order_date = Column(String, nullable=False)
    asin = Column(String, nullable=True)
    sku = Column(String, nullable=True)
    quantity = Column(Integer, default=0)
    item_price = Column(Float, default=0.0)
    item_tax = Column(Float, default=0.0)
    shipping_price = Column(Float, default=0.0)
    shipping_tax = Column(Float, default=0.0)
    promotion_discount = Column(Float, default=0.0)
    sales_channel = Column(String, nullable=True)
    fulfillment = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class AdProductPerformance(Base):
    """Sponsored Products advertising performance"""
    __tablename__ = 'ad_product_performance'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(Date, nullable=False)
    profile_id = Column(String, nullable=True)
    marketplace = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    campaign_name = Column(String, nullable=True)
    campaign_id = Column(String, nullable=True)
    ad_group_name = Column(String, nullable=True)
    ad_group_id = Column(String, nullable=True)
    advertised_asin = Column(String, nullable=True)
    sku = Column(String, nullable=True)
    match_type = Column(String, nullable=True)
    targeting = Column(String, nullable=True)
    placement = Column(String, nullable=True)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    spend = Column(Float, default=0.0)
    sales_14d = Column(Float, default=0.0)
    orders_14d = Column(Integer, default=0)
    units_14d = Column(Integer, default=0)
    cpc = Column(Float, default=0.0)
    ctr = Column(Float, default=0.0)
    acos = Column(Float, default=0.0)
    roas = Column(Float, default=0.0)
    conversion_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class MetricDefinition(Base):
    """Definitions and metadata for KPI metrics"""
    __tablename__ = 'metric_definitions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    description = Column(Text)
    formula = Column(Text)
    unit = Column(String)
    format_type = Column(String)
    source_table = Column(String)
    is_calculated = Column(Boolean, default=False)
    category = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class ChildTrafficMetric(Base):
    """Detail page traffic and conversion metrics by child ASIN"""
    __tablename__ = 'child_traffic_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    child_asin = Column(String, nullable=True)
    parent_asin = Column(String, nullable=True)
    sku = Column(String, nullable=True)
    sessions = Column(Integer, default=0)
    session_percentage = Column(Float, default=0.0)
    page_views = Column(Integer, default=0)
    page_views_percentage = Column(Float, default=0.0)
    buy_box_percentage = Column(Float, default=0.0)
    units_ordered = Column(Integer, default=0)
    units_ordered_b2b = Column(Integer, default=0)
    ordered_product_sales = Column(Float, default=0.0)
    ordered_product_sales_b2b = Column(Float, default=0.0)
    total_order_items = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    source = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class InventorySnapshot(Base):
    """Daily inventory snapshots from FBA/AWD inventory reports"""
    __tablename__ = 'inventory_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(Date, nullable=False)
    asin = Column(String, nullable=True)
    sku = Column(String, nullable=True)
    fnsku = Column(String, nullable=True)
    product_name = Column(String, nullable=True)
    condition = Column(String, nullable=True)
    available_quantity = Column(Integer, default=0)
    reserved_quantity = Column(Integer, default=0)
    inbound_working_quantity = Column(Integer, default=0)
    inbound_shipped_quantity = Column(Integer, default=0)
    inbound_receiving_quantity = Column(Integer, default=0)
    research_quantity = Column(Integer, default=0)
    total_quantity = Column(Integer, default=0)
    fulfillment_channel_sku = Column(String, nullable=True)
    warehouse_condition_code = Column(String, nullable=True)
    source = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class SettlementTransaction(Base):
    """FBA settlement transactions for fees and costs"""
    __tablename__ = 'settlement_transactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    settlement_id = Column(String, nullable=False)
    settlement_start_date = Column(Date, nullable=True)
    settlement_end_date = Column(Date, nullable=True)
    deposit_date = Column(Date, nullable=True)
    transaction_type = Column(String, nullable=True)
    order_id = Column(String, nullable=True)
    sku = Column(String, nullable=True)
    asin = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    quantity = Column(Integer, default=0)
    marketplace = Column(String, nullable=True)
    fulfillment = Column(String, nullable=True)
    amount_type = Column(String, nullable=True)
    amount = Column(Float, default=0.0)
    currency = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Product(Base):
    """Product master data"""
    __tablename__ = 'products'
    
    asin = Column(String, primary_key=True)
    parent_asin = Column(String, nullable=True)
    sku = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    category = Column(String, nullable=True)
    product_name = Column(String, nullable=True)
    size = Column(String, nullable=True)
    status = Column(String, nullable=True, server_default='Launched')


class ProductCOGS(Base):
    """Product cost of goods sold"""
    __tablename__ = 'product_cogs'
    
    asin = Column(String, primary_key=True)
    sku = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    category = Column(String, nullable=True)
    product_name = Column(String, nullable=True)
    size = Column(String, nullable=True)
    cogs_amount = Column(Float, default=0.0)
    currency = Column(String, nullable=True)
    source = Column(String, nullable=True)


class SKUAlias(Base):
    """SKU to ASIN mapping aliases"""
    __tablename__ = 'sku_aliases'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String, nullable=False)
    asin = Column(String, nullable=False)
    source = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
