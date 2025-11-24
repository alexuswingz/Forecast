-- Critical Performance Indexes for Planning Endpoint
-- Run these on your RDS PostgreSQL database to drastically improve query speed

-- Index on order_items for ASIN lookups (critical for planning queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_items_asin 
ON order_items(asin);

-- Index on order_items for date filtering (order_date is TEXT)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_items_date 
ON order_items(order_date);

-- Composite index for ASIN + date queries (most common pattern)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_order_items_asin_date 
ON order_items(asin, order_date);

-- Index on inventory_snapshots for ASIN lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_snapshots_asin 
ON inventory_snapshots(asin);

-- Index on inventory_snapshots for date filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_snapshots_date 
ON inventory_snapshots(snapshot_date DESC);

-- Composite index for ASIN + date queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_snapshots_asin_date 
ON inventory_snapshots(asin, snapshot_date DESC);

-- Analyze tables to update statistics
ANALYZE order_items;
ANALYZE inventory_snapshots;
ANALYZE products;

-- Verify indexes were created
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('order_items', 'inventory_snapshots', 'products')
ORDER BY tablename, indexname;

