-- Additional indexes for /metrics endpoint performance

-- Indexes for child_traffic_metrics (traffic data)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_child_traffic_child_asin 
ON child_traffic_metrics(child_asin);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_child_traffic_date 
ON child_traffic_metrics(date);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_child_traffic_child_asin_date 
ON child_traffic_metrics(child_asin, date);

-- Indexes for ad_product_performance (advertising data)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ad_performance_asin 
ON ad_product_performance(advertised_asin);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ad_performance_date 
ON ad_product_performance(report_date);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ad_performance_asin_date 
ON ad_product_performance(advertised_asin, report_date);

-- Analyze tables to update statistics
ANALYZE child_traffic_metrics;
ANALYZE ad_product_performance;

-- Verify indexes were created
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('child_traffic_metrics', 'ad_product_performance')
AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;


