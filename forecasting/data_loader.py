"""
Data Loader - Fetch historical data from local database
"""
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
from typing import Optional, Tuple
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config


class ForecastDataLoader:
    """Load historical sales and search volume data from database"""
    
    def __init__(self, asin: Optional[str] = None, sku: Optional[str] = None):
        """
        Initialize data loader
        
        Args:
            asin: Product ASIN to forecast
            sku: Product SKU to forecast (alternative to ASIN)
        """
        self.asin = asin
        self.sku = sku
        
        # Use SQLite for local forecasting
        if Config.USE_SQLITE:
            self.engine = create_engine(f"sqlite:///{Config.SQLITE_DB_PATH}")
        else:
            self.engine = create_engine(Config.DATABASE_URL)
        
        print(f" Connected to database: {'SQLite' if Config.USE_SQLITE else 'PostgreSQL'}")
    
    def load_weekly_sales(self, start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Load weekly sales data (units sold)
        
        Returns:
            DataFrame with columns: week_end, units_sold
        """
        # Determine date function based on database type
        if Config.USE_SQLITE:
            week_expr = "date(order_date, 'weekday 0', '-6 days')"
        else:
            week_expr = "date_trunc('week', order_date)::date + 6"
        
        # Build query
        where_clauses = []
        params = {}
        
        if self.asin:
            where_clauses.append("asin = :asin")
            params['asin'] = self.asin
        elif self.sku:
            where_clauses.append("sku = :sku")
            params['sku'] = self.sku
        
        if start_date:
            where_clauses.append("order_date >= :start_date")
            params['start_date'] = start_date
        
        if end_date:
            where_clauses.append("order_date <= :end_date")
            params['end_date'] = end_date
        
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
            SELECT 
                {week_expr} as week_end,
                SUM(quantity) as units_sold
            FROM order_items
            {where_sql}
            GROUP BY week_end
            ORDER BY week_end
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn, params=params)
        
        # Convert week_end to datetime
        df['week_end'] = pd.to_datetime(df['week_end'])
        
        print(f" Loaded {len(df)} weeks of sales data")
        if len(df) > 0:
            print(f"   Date range: {df['week_end'].min()} to {df['week_end'].max()}")
            print(f"   Total units: {df['units_sold'].sum():,.0f}")
        
        return df
    
    def load_weekly_traffic(self, start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Load weekly traffic data (sessions, page views)
        
        Returns:
            DataFrame with columns: week_end, sessions, page_views, conversion_rate
        """
        # Determine date function
        if Config.USE_SQLITE:
            week_expr = "date(date, 'weekday 0', '-6 days')"
        else:
            week_expr = "date_trunc('week', date)::date + 6"
        
        # Build query
        where_clauses = []
        params = {}
        
        if self.asin:
            where_clauses.append("child_asin = :asin")
            params['asin'] = self.asin
        elif self.sku:
            where_clauses.append("parent_asin IN (SELECT parent_asin FROM products WHERE asin = :sku)")
            params['sku'] = self.sku
        
        if start_date:
            where_clauses.append("date >= :start_date")
            params['start_date'] = start_date
        
        if end_date:
            where_clauses.append("date <= :end_date")
            params['end_date'] = end_date
        
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
            SELECT 
                {week_expr} as week_end,
                SUM(sessions) as sessions,
                SUM(page_views) as page_views,
                AVG(conversion_rate) as avg_conversion_rate
            FROM child_traffic_metrics
            {where_sql}
            GROUP BY week_end
            ORDER BY week_end
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn, params=params)
        
        df['week_end'] = pd.to_datetime(df['week_end'])
        
        print(f" Loaded {len(df)} weeks of traffic data")
        
        return df
    
    def load_search_volume(self, search_terms: list,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Load weekly search volume data (if available)
        
        Note: This is a placeholder - you'll need to add search volume tracking
        For now, we'll return synthetic data based on sessions
        
        Returns:
            DataFrame with columns: week_end, search_volume
        """
        # For now, use traffic sessions as a proxy for search volume
        traffic = self.load_weekly_traffic(start_date, end_date)
        
        if len(traffic) > 0:
            df = traffic[['week_end', 'sessions']].copy()
            df.rename(columns={'sessions': 'search_volume'}, inplace=True)
            
            print(f"  Using sessions as proxy for search volume")
            print(f"   (Add search volume tracking for accurate forecasts)")
            
            return df
        
        return pd.DataFrame(columns=['week_end', 'search_volume'])
    
    def load_current_inventory(self) -> Tuple[float, dict]:
        """
        Load current inventory levels
        
        Returns:
            (total_inventory, breakdown_dict)
        """
        where_clause = ""
        params = {}
        
        if self.asin:
            where_clause = "WHERE asin = :asin"
            params['asin'] = self.asin
        elif self.sku:
            where_clause = "WHERE sku = :sku"
            params['sku'] = self.sku
        
        query = f"""
            SELECT 
                asin,
                sku,
                SUM(available_quantity) as available_fba,
                SUM(reserved_quantity) as reserved_fba,
                SUM(inbound_working_quantity + inbound_shipped_quantity + inbound_receiving_quantity) as inbound_fba,
                SUM(research_quantity) as researching,
                MAX(snapshot_date) as latest_date
            FROM inventory_snapshots
            {where_clause}
            GROUP BY asin, sku
            ORDER BY latest_date DESC
            LIMIT 1
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn, params=params)
        
        if len(df) == 0:
            print("  No inventory data found")
            return 0.0, {}
        
        row = df.iloc[0]
        
        breakdown = {
            'available_fba': float(row.get('available_fba', 0) or 0),
            'reserved_fba': float(row.get('reserved_fba', 0) or 0),
            'inbound_fba': float(row.get('inbound_fba', 0) or 0),
            'researching': float(row.get('researching', 0) or 0),
            'latest_date': row.get('latest_date'),
        }
        
        total = sum(v for k, v in breakdown.items() if k != 'latest_date')
        
        print(f" Current Inventory: {total:,.0f} units (as of {breakdown['latest_date']})")
        print(f"   Available: {breakdown['available_fba']:,.0f}")
        print(f"   Reserved: {breakdown['reserved_fba']:,.0f}")
        print(f"   Inbound: {breakdown['inbound_fba']:,.0f}")
        
        return total, breakdown
    
    def get_product_info(self) -> dict:
        """Get product information"""
        where_clause = ""
        params = {}
        
        if self.asin:
            where_clause = "WHERE asin = :asin"
            params['asin'] = self.asin
        elif self.sku:
            where_clause = "WHERE asin IN (SELECT asin FROM product_cogs WHERE sku = :sku LIMIT 1)"
            params['sku'] = self.sku
        
        query = f"""
            SELECT 
                asin,
                parent_asin,
                product_name as title
            FROM products
            {where_clause}
            LIMIT 1
        """
        
        with self.engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn, params=params)
        
        if len(df) == 0:
            return {'asin': self.asin or 'Unknown', 'title': 'Unknown Product'}
        
        return df.iloc[0].to_dict()


if __name__ == '__main__':
    # Test data loader
    print("Testing Data Loader...")
    print("=" * 60)
    
    # Load Hydrangea data
    loader = ForecastDataLoader(asin='B0C73TDZCQ')
    
    # Get product info
    product = loader.get_product_info()
    print(f"\nProduct: {product.get('title', 'Unknown')}")
    print(f"ASIN: {product['asin']}")
    
    # Load sales data
    print("\n" + "=" * 60)
    sales = loader.load_weekly_sales(start_date='2024-05-01')
    
    if len(sales) > 0:
        print("\nFirst 5 weeks:")
        print(sales.head().to_string(index=False))
        
        print("\nLast 5 weeks:")
        print(sales.tail().to_string(index=False))
    
    # Load inventory
    print("\n" + "=" * 60)
    total_inv, breakdown = loader.load_current_inventory()
    
    print("\n Data loader tests complete!")

