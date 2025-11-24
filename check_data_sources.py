"""
Check what data sources we have vs what's needed for all metrics
"""
from config import Config
from sqlalchemy import create_engine, text
import sys

# Required data sources for complete metrics
REQUIRED_DATA = {
    "Sales & Units": {
        "table": "order_items",
        "metrics": ["Units", "Sales", "Orders"],
        "source": "Fulfilled Shipments CSVs"
    },
    "Traffic & Conversion": {
        "table": "child_traffic_metrics",
        "metrics": ["Sessions", "Organic Conversion Rate", "Page Views"],
        "source": "SP-API: Detail Page Sales & Traffic by Child"
    },
    "Advertising": {
        "table": "ad_product_performance",
        "metrics": ["Ad Impressions", "Ad Clicks", "Ad Spend", "Ad Sales", "Ad Orders", "Ad Units", "Ad Conversion Rate"],
        "source": "Sponsored Products Advertised Product Report"
    },
    "Inventory": {
        "table": "inventory_snapshots",
        "metrics": ["Total Inventory", "Available", "Reserved", "Inbound Working", "Inbound Shipped", "Inbound Receiving", "Research", "FBA", "AWD"],
        "source": "FBA/AWD Inventory Reports"
    },
    "Product Master": {
        "table": "products",
        "metrics": ["Product Name", "Brand", "Size", "ASIN"],
        "source": "Product master data"
    },
    "COGS": {
        "table": "product_cogs",
        "metrics": ["Cost per Unit", "Profit Margin"],
        "source": "COGS spreadsheet"
    },
    "Fees": {
        "table": "settlement_transactions",
        "metrics": ["FBA Fees", "Referral Fees", "Storage Fees"],
        "source": "SP-API: Settlement Reports"
    }
}

print("=" * 80)
print("DATA SOURCE AVAILABILITY CHECK")
print("=" * 80)

# Connect to database
engine = create_engine(Config.DATABASE_URL)
conn = engine.connect()

# Get all tables
if Config.USE_SQLITE:
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
else:
    result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"))

existing_tables = {row[0] for row in result}

print(f"\nDatabase: {'SQLite (local)' if Config.USE_SQLITE else 'PostgreSQL (RDS)'}")
print(f"Tables found: {len(existing_tables)}\n")

# Check each data source
missing_sources = []
available_sources = []

for source_name, info in REQUIRED_DATA.items():
    table = info['table']
    has_data = table in existing_tables
    
    if has_data:
        # Check row count
        try:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.fetchone()[0]
            status = f"[OK] {count:,} rows"
            available_sources.append((source_name, info))
        except:
            status = "[OK] exists"
            available_sources.append((source_name, info))
    else:
        status = "[MISSING]"
        missing_sources.append((source_name, info))
    
    print(f"{status:20s} {source_name:25s} | {table}")
    print(f"{'':20s} Metrics: {', '.join(info['metrics'][:3])}{'...' if len(info['metrics']) > 3 else ''}")
    print(f"{'':20s} Source: {info['source']}")
    print()

conn.close()

# Summary
print("=" * 80)
print("SUMMARY")
print("=" * 80)

if not missing_sources:
    print("\n[SUCCESS] All data sources are available!")
    print("\nYou have COMPLETE data for all metrics:")
    print("- Sales & Orders")
    print("- Traffic & Conversion")
    print("- Advertising (PPC)")
    print("- Inventory (FBA/AWD)")
    print("- Product Info & COGS")
    print("- Fees & Settlement")
    print("\nYour Lambda endpoints can now provide FULL metrics!")
else:
    print(f"\n[PARTIAL] {len(available_sources)}/{len(REQUIRED_DATA)} data sources available")
    print(f"\nMissing sources ({len(missing_sources)}):")
    for name, info in missing_sources:
        print(f"  - {name}: {info['source']}")
    
    print(f"\nAvailable metrics: {len(available_sources)}/{len(REQUIRED_DATA)}")

print("\n" + "=" * 80)


