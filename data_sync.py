"""
Data Sync Service
Handles periodic syncing of data from Amazon APIs to database
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from database import SessionLocal, init_db
from models import ChildTrafficMetric, InventorySnapshot, KPIMetric
from integrations.amazon_sp_api import AmazonSPAPIClient, extract_kpis_from_orders
from integrations.amazon_ads_api import AmazonAdsAPIClient, extract_kpis_from_ads
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataSyncService:
    """Service to sync data from Amazon APIs"""
    
    def __init__(self):
        self.sp_api_client = None
        self.ads_api_client = None
        self.raw_output_dir = Path(Config.RAW_OUTPUT_DIR)
        
    def initialize_clients(self):
        """Initialize API clients"""
        try:
            if all([Config.SP_API_REFRESH_TOKEN, Config.SP_API_CLIENT_ID, Config.SP_API_CLIENT_SECRET]):
                self.sp_api_client = AmazonSPAPIClient()
                logger.info("SP-API client initialized")
            else:
                logger.warning("SP-API credentials not configured")
            
            if all([Config.ADS_API_CLIENT_ID, Config.ADS_API_CLIENT_SECRET, Config.ADS_API_REFRESH_TOKEN]):
                self.ads_api_client = AmazonAdsAPIClient()
                logger.info("Ads API client initialized")
            else:
                logger.warning("Ads API credentials not configured")
                
        except Exception as e:
            logger.error(f"Error initializing clients: {e}")
    
    # ------------------------
    # Helper utilities
    # ------------------------

    @staticmethod
    def _as_date(value: str) -> datetime.date:
        return datetime.fromisoformat(value).date()

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        if value in (None, "", "-"):
            return None
        try:
            return float(str(value).replace(",", ""))
        except ValueError:
            return None

    @staticmethod
    def _safe_int(value) -> Optional[int]:
        if value in (None, "", "-"):
            return None
        try:
            return int(float(str(value).replace(",", "")))
        except ValueError:
            return None

    def _write_raw(self, category: str, start_date: str, end_date: Optional[str], payload):
        if payload in (None, [], {}):
            return
        try:
            self.raw_output_dir.mkdir(parents=True, exist_ok=True)
            normalized_end = end_date or start_date
            filename = f"{category}_{start_date}_{normalized_end}.json"
            path = self.raw_output_dir / filename
            with path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, default=str, indent=2)
            logger.info("Saved raw %s response to %s", category, path)
        except Exception as exc:
            logger.warning("Unable to persist raw %s payload: %s", category, exc)
    def _write_raw_text(self, category: str, start_date: str, end_date: Optional[str], text: Optional[str], extension: str = ".tsv"):
        if not text:
            return
        try:
            self.raw_output_dir.mkdir(parents=True, exist_ok=True)
            normalized_end = end_date or start_date
            filename = f"{category}_{start_date}_{normalized_end}{extension}"
            path = self.raw_output_dir / filename
            path.write_text(text, encoding="utf-8")
            logger.info("Saved raw %s report to %s", category, path)
        except Exception as exc:
            logger.warning("Unable to persist raw %s text: %s", category, exc)

    # ------------------------
    # SP-API Syncs
    # ------------------------

    def sync_sp_api_data(self, db: Session, start_date: str, end_date: Optional[str] = None):
        """
        Sync data from SP-API
        
        Args:
            db: Database session
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (optional)
        """
        if not self.sp_api_client:
            logger.error("SP-API client not initialized")
            return
        
        try:
            logger.info(f"Syncing SP-API data from {start_date}")
            
            # Fetch orders
            orders = self.sp_api_client.get_orders(start_date, end_date)
            
            if orders:
                self._write_raw("orders", start_date, end_date, orders)
                # Extract KPIs from orders
                kpis = extract_kpis_from_orders(orders)
                
                # Save KPIs to database
                date_obj = datetime.fromisoformat(start_date).date()
                
                for metric_name, value in kpis.items():
                    metric = KPIMetric(
                        date=date_obj,
                        metric_name=metric_name,
                        metric_category='Sales',
                        value=float(value) if value is not None else None,
                        source='Amazon SP-API',
                        unit='count' if 'orders' in metric_name else 'currency'
                    )
                    db.add(metric)
                
                db.commit()
                logger.info(f"Saved {len(kpis)} SP-API metrics")
            
            # Fetch sales metrics
            sales_metrics = self.sp_api_client.get_sales_metrics(start_date, end_date)
            
            if sales_metrics:
                logger.info("Sales metrics fetched successfully")
                # TODO: persist additional aggregated metrics

            # Child level sales & traffic
            self.sync_child_traffic_metrics(db, start_date, end_date or start_date)
            # Inventory (FBA + AWD)
            inventory_date = end_date or start_date
            try:
                self.sync_inventory_snapshots(db, inventory_date)
            except Exception as inv_exc:
                logger.warning("Inventory sync skipped for %s: %s", inventory_date, inv_exc)
            
        except Exception as e:
            logger.error(f"Error syncing SP-API data: {e}")
            db.rollback()
    
    def sync_ads_api_data(self, db: Session, start_date: str, end_date: Optional[str] = None):
        """
        Sync data from Ads API
        
        Args:
            db: Database session
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format (optional)
        """
        if not self.ads_api_client:
            logger.error("Ads API client not initialized")
            return
        
        try:
            logger.info(f"Syncing Ads API data from {start_date}")
            
            # Fetch campaigns
            campaigns = self.ads_api_client.get_campaigns()
            
            if campaigns:
                logger.info(f"Fetched {len(campaigns)} campaigns")
                
                # Request performance report
                report_response = self.ads_api_client.get_campaign_performance(start_date, end_date)
                
                if report_response and 'report_id' in report_response:
                    logger.info(f"Campaign report requested: {report_response['report_id']}")
                    # Note: Reports take time to generate. You'll need to check status and download later
                
                # Extract basic KPIs from campaigns
                kpis = extract_kpis_from_ads(campaigns)
                
                # Save KPIs to database
                date_obj = datetime.strptime(start_date, '%Y%m%d').date()
                
                for metric_name, value in kpis.items():
                    metric = KPIMetric(
                        date=date_obj,
                        metric_name=metric_name,
                        metric_category='Advertising',
                        value=float(value) if value is not None else None,
                        source='Amazon Ads API',
                        unit='count' if 'campaign' in metric_name else 'number'
                    )
                    db.add(metric)
                
                db.commit()
                logger.info(f"Saved {len(kpis)} Ads API metrics")
            
        except Exception as e:
            logger.error(f"Error syncing Ads API data: {e}")
            db.rollback()

    # ------------------------
    # Child metrics processing
    # ------------------------

    def sync_child_traffic_metrics(self, db: Session, start_date: str, end_date: str):
        """Pull Detail Page Sales and Traffic by Child Item"""
        if not self.sp_api_client:
            return

        end_date = end_date or start_date
        start_dt = datetime.fromisoformat(start_date).date()
        end_dt = datetime.fromisoformat(end_date).date()
        window = timedelta(days=30)

        total_upserted = 0
        current = start_dt
        while current <= end_dt:
            window_end = min(current + window - timedelta(days=1), end_dt)
            chunk_start = current.isoformat()
            chunk_end = window_end.isoformat()
            logger.info("Fetching child ASIN metrics from %s to %s", chunk_start, chunk_end)
            rows, raw_text = self.sp_api_client.fetch_child_traffic_metrics(chunk_start, chunk_end)
            self._write_raw_text("child_sales", chunk_start, chunk_end, raw_text)
            if not rows:
                logger.warning("No child metrics returned for %s - %s", chunk_start, chunk_end)
                current = window_end + timedelta(days=1)
                continue

            upserted = 0
            for row in rows:
                report_date = (
                    row.get("date")
                    or row.get("Date")
                    or row.get("reportDate")
                    or row.get("childItemData")
                )
                if not report_date:
                    continue
                try:
                    date_obj = self._as_date(report_date[:10])
                except ValueError:
                    logger.debug("Skipping row with invalid date: %s", report_date)
                    continue

                child_asin = row.get("childAsin") or row.get("child-asin") or row.get("asin")
                if not child_asin:
                    continue
                parent_asin = row.get("parentAsin") or row.get("parent-asin")
                if parent_asin and child_asin == parent_asin:
                    continue
                sku = row.get("sku") or row.get("sellerSku") or row.get("merchantSku") or child_asin

                existing = (
                    db.query(ChildTrafficMetric)
                    .filter(
                        ChildTrafficMetric.date == date_obj,
                        ChildTrafficMetric.child_asin == child_asin,
                        ChildTrafficMetric.sku == sku,
                    )
                    .one_or_none()
                )

                payload = {
                    "parent_asin": parent_asin,
                    "sessions": self._safe_float(row.get("sessions")),
                    "session_percentage": self._safe_float(row.get("sessionPercentage")),
                    "page_views": self._safe_float(row.get("pageViews")),
                    "page_views_percentage": self._safe_float(row.get("pageViewsPercentage")),
                    "buy_box_percentage": self._safe_float(row.get("buyBoxPercentage")),
                    "units_ordered": self._safe_float(row.get("unitsOrdered")),
                    "units_ordered_b2b": self._safe_float(row.get("unitsOrderedB2B")),
                    "ordered_product_sales": self._safe_float(row.get("orderedProductSales")),
                    "ordered_product_sales_b2b": self._safe_float(row.get("orderedProductSalesB2B")),
                    "total_order_items": self._safe_float(row.get("totalOrderItems")),
                    "conversion_rate": self._safe_float(row.get("unitSessionPercentage")),
                }

                if existing:
                    for key, value in payload.items():
                        setattr(existing, key, value)
                else:
                    db.add(
                        ChildTrafficMetric(
                            date=date_obj,
                            child_asin=child_asin,
                            sku=sku,
                            **payload,
                        )
                    )
                upserted += 1

            db.commit()
            total_upserted += upserted
            logger.info("Stored %s child ASIN metric rows for %s - %s", upserted, chunk_start, chunk_end)
            current = window_end + timedelta(days=1)

        logger.info("Stored %s total child ASIN metric rows", total_upserted)

    # ------------------------
    # Inventory processing
    # ------------------------

    def sync_inventory_snapshots(self, db: Session, snapshot_date: str):
        """Pull FBA and AWD inventory snapshots"""
        if not self.sp_api_client:
            return

        logger.info("Fetching inventory snapshot for %s", snapshot_date)

        fba_rows, fba_raw = self.sp_api_client.fetch_fba_inventory_positions(snapshot_date)
        awd_rows, awd_raw = self.sp_api_client.fetch_awd_inventory_positions(snapshot_date)

        self._write_raw_text("inventory_fba", snapshot_date, snapshot_date, fba_raw)
        self._write_raw_text("inventory_awd", snapshot_date, snapshot_date, awd_raw)

        changed = 0
        for program, rows in (("FBA", fba_rows), ("AWD", awd_rows)):
            if not rows:
                continue
            for row in rows:
                sku = row.get("sku") or row.get("seller-sku")
                if not sku:
                    continue
                asin = row.get("asin") or row.get("asin1")
                fnsku = row.get("fnsku")
                date_value = row.get("snapshot-date") or row.get("snapshotDate") or snapshot_date
                try:
                    date_obj = self._as_date(date_value[:10])
                except ValueError:
                    date_obj = self._as_date(snapshot_date)

                existing = (
                    db.query(InventorySnapshot)
                    .filter(
                        InventorySnapshot.snapshot_date == date_obj,
                        InventorySnapshot.sku == sku,
                        InventorySnapshot.fulfillment_program == program,
                    )
                    .one_or_none()
                )

                payload = {
                    "asin": asin,
                    "fnsku": fnsku,
                    "total_quantity": self._safe_float(
                        row.get("total-quantity") or row.get("totalQuantity")
                    ),
                    "available_quantity": self._safe_float(row.get("available")),
                    "reserved_quantity": self._safe_float(row.get("reserved")),
                    "inbound_working_quantity": self._safe_float(
                        row.get("inbound-working-quantity") or row.get("inboundWorkingQuantity")
                    ),
                    "inbound_shipped_quantity": self._safe_float(
                        row.get("inbound-shipped-quantity") or row.get("inboundShippedQuantity")
                    ),
                    "inbound_receiving_quantity": self._safe_float(
                        row.get("inbound-receiving-quantity") or row.get("inboundReceivingQuantity")
                    ),
                    "research_quantity": self._safe_float(row.get("researching-quantity")),
                    "fulfillment_center_id": row.get("fulfillment-center-id"),
                    "source_report_type": row.get("reportType") or program,
                }

                if existing:
                    for key, value in payload.items():
                        setattr(existing, key, value)
                else:
                    db.add(
                        InventorySnapshot(
                            snapshot_date=date_obj,
                            sku=sku,
                            fulfillment_program=program,
                            **payload,
                        )
                    )
                changed += 1

        if changed:
            db.commit()
            logger.info("Stored %s inventory snapshot rows", changed)
    
    def sync_all_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None):
        """
        Sync data from all sources
        
        Args:
            start_date: Start date (format depends on API)
            end_date: End date (optional)
        """
        if not start_date:
            start_date = Config.DATA_START_DATE
        
        logger.info(f"Starting full data sync from {start_date}")
        
        db = SessionLocal()
        
        try:
            # Sync SP-API data (YYYY-MM-DD format)
            if self.sp_api_client:
                self.sync_sp_api_data(db, start_date, end_date)
            
            # Sync Ads API data (YYYYMMDD format)
            if self.ads_api_client:
                ads_start_date = start_date.replace('-', '')
                ads_end_date = end_date.replace('-', '') if end_date else None
                self.sync_ads_api_data(db, ads_start_date, ads_end_date)
            
            logger.info("Full data sync completed")
            
        except Exception as e:
            logger.error(f"Error during full sync: {e}")
        finally:
            db.close()
    
    def sync_incremental(self, days_back: int = 7):
        """
        Sync data for the last N days
        
        Args:
            days_back: Number of days to sync backwards from today
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        logger.info(f"Starting incremental sync from {start_date} to {end_date}")
        
        self.sync_all_data(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )


def run_daily_sync():
    """Run daily sync job"""
    logger.info("Running daily sync job")
    
    sync_service = DataSyncService()
    sync_service.initialize_clients()
    
    # Sync last 7 days to catch any updates
    sync_service.sync_incremental(days_back=7)


def run_historical_sync():
    """Run historical sync from configured start date"""
    logger.info("Running historical sync job")
    
    # Initialize database
    init_db()
    
    sync_service = DataSyncService()
    sync_service.initialize_clients()
    
    # Sync from configured start date
    sync_service.sync_all_data(start_date=Config.DATA_START_DATE)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Amazon data sync runner")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)", default=Config.DATA_START_DATE)
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--job", choices=["historical", "incremental"], default="historical")
    parser.add_argument("--days", type=int, default=7, help="Days back for incremental sync")
    args = parser.parse_args()

    init_db()
    sync_service = DataSyncService()
    sync_service.initialize_clients()

    if args.job == "incremental":
        sync_service.sync_incremental(days_back=args.days)
    else:
        sync_service.sync_all_data(start_date=args.start_date, end_date=args.end_date)

