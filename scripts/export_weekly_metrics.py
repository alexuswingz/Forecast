#!/usr/bin/env python3
"""
Export weekly metrics to Excel
"""
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get PostgreSQL RDS connection"""
    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        cursor_factory=RealDictCursor
    )

def export_weekly_metrics(output_file='weekly_metrics.xlsx'):
    """Export weekly metrics to Excel"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        print("=" * 80)
        print("EXPORTING WEEKLY METRICS TO EXCEL")
        print("=" * 80)
        
        # Query weekly aggregated metrics
        cur.execute("""
            SELECT 
                DATE_TRUNC('week', date)::date as week_start,
                DATE_TRUNC('week', date)::date + INTERVAL '6 days' as week_end,
                p.brand,
                p.product_name,
                p.size,
                d.asin,
                SUM(d.units_sold) as units_sold,
                SUM(d.sales_amount) as sales,
                SUM(d.sales_amount) / NULLIF(SUM(d.units_sold), 0) as avg_price,
                SUM(d.sessions) as sessions,
                AVG(d.conversion_rate) as avg_conversion_rate,
                SUM(d.page_views) as page_views,
                SUM(d.ad_spend) as ad_spend,
                SUM(d.ad_sales) as ad_sales,
                SUM(d.ad_clicks) as ad_clicks,
                SUM(d.ad_impressions) as ad_impressions,
                AVG(CASE WHEN d.sales_amount > 0 THEN (d.ad_spend / d.sales_amount * 100) ELSE 0 END) as avg_tacos,
                AVG(CASE WHEN d.ad_sales > 0 THEN (d.ad_spend / d.ad_sales * 100) ELSE 0 END) as avg_acos
            FROM daily_product_metrics d
            JOIN products p ON p.asin = d.asin
            WHERE d.date >= CURRENT_DATE - INTERVAL '12 months'
            GROUP BY 
                DATE_TRUNC('week', date),
                p.brand,
                p.product_name,
                p.size,
                d.asin
            ORDER BY 
                week_start DESC,
                p.brand,
                p.product_name,
                p.size
        """)
        
        rows = cur.fetchall()
        
        if not rows:
            print("[!] No data found!")
            return
        
        print(f"[OK] Found {len(rows)} weekly records")
        
        # Convert to DataFrame
        df = pd.DataFrame(rows)
        
        # Format dates
        df['week_start'] = pd.to_datetime(df['week_start']).dt.date
        df['week_end'] = pd.to_datetime(df['week_end']).dt.date
        
        # Round numeric columns
        df['avg_price'] = df['avg_price'].round(2)
        df['sales'] = df['sales'].round(2)
        df['avg_conversion_rate'] = df['avg_conversion_rate'].round(2)
        df['ad_spend'] = df['ad_spend'].round(2)
        df['ad_sales'] = df['ad_sales'].round(2)
        df['avg_tacos'] = df['avg_tacos'].round(2)
        df['avg_acos'] = df['avg_acos'].round(2)
        
        # Rename columns for Excel
        df.columns = [
            'Week Start',
            'Week End',
            'Brand',
            'Product',
            'Size',
            'ASIN',
            'Units Sold',
            'Sales ($)',
            'Avg Price ($)',
            'Sessions',
            'Avg Conv Rate (%)',
            'Page Views',
            'Ad Spend ($)',
            'Ad Sales ($)',
            'Ad Clicks',
            'Ad Impressions',
            'Avg TACOS (%)',
            'Avg ACOS (%)'
        ]
        
        # Export to Excel with formatting
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Weekly Metrics', index=False)
            
            # Get worksheet
            worksheet = writer.sheets['Weekly Metrics']
            
            # Auto-size columns
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        print(f"\n[OK] Exported to: {output_file}")
        print(f"Weeks: {df['Week Start'].min()} to {df['Week Start'].max()}")
        print(f"Products: {df['ASIN'].nunique()} unique ASINs")
        print(f"Total Sales: ${df['Sales ($)'].sum():,.2f}")
        print(f"Total Units: {int(df['Units Sold'].sum())}")
        
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    output_file = sys.argv[1] if len(sys.argv) > 1 else 'weekly_metrics.xlsx'
    export_weekly_metrics(output_file)

