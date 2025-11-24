"""
Amazon SP-API Integration
Handles fetching data from Amazon Selling Partner API
"""

import csv
import gzip
import io
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

import json

from sp_api.api import Orders, Reports, Sales
from sp_api.base import Marketplaces, SellingApiException

from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AmazonSPAPIClient:
    """Client for Amazon SP-API with helper utilities for reports"""

    CHILD_SALES_REPORT = "GET_SALES_AND_TRAFFIC_REPORT"
    FBA_INVENTORY_REPORT = "GET_FBA_MYI_ALL_INVENTORY_DATA"
    AWD_INVENTORY_REPORT = os.getenv("SP_API_AWD_REPORT_TYPE", "GET_FULFILLMENT_AWD_INVENTORY_DATA")
    SETTLEMENT_REPORT = "GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE_V2"

    def __init__(self):
        self.credentials = self._build_credentials()
        self.marketplace = self._resolve_marketplace(Config.SP_API_MARKETPLACE)
        self.marketplace_ids = [self.marketplace.marketplace_id]

    def _build_credentials(self) -> Dict:
        creds = {
            "refresh_token": Config.SP_API_REFRESH_TOKEN,
            "lwa_app_id": Config.SP_API_CLIENT_ID,
            "lwa_client_secret": Config.SP_API_CLIENT_SECRET,
        }

        if Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY:
            creds["aws_access_key"] = Config.AWS_ACCESS_KEY_ID
            creds["aws_secret_key"] = Config.AWS_SECRET_ACCESS_KEY

        if Config.SP_API_ROLE_ARN:
            creds["role_arn"] = Config.SP_API_ROLE_ARN

        if Config.SP_API_REGION:
            creds["region"] = Config.SP_API_REGION

        return creds

    def _resolve_marketplace(self, marketplace_value: Optional[str]):
        if not marketplace_value:
            return Marketplaces.US

        value = marketplace_value.upper()
        # Try attribute lookup (e.g., "US", "CA")
        marketplace = getattr(Marketplaces, value, None)
        if marketplace:
            return marketplace

        # Fall back to lookup by marketplace ID (e.g., ATVPDKIKX0DER)
        for mp in Marketplaces.__members__.values():
            if mp.marketplace_id == marketplace_value:
                return mp

        raise ValueError(f"Unsupported marketplace value: {marketplace_value}")

    # -----------------------
    # Order & sales endpoints
    # -----------------------

    def get_orders(self, start_date: str, end_date: Optional[str] = None) -> List[Dict]:
        """Fetch order metadata directly from Orders API"""
        try:
            orders_api = Orders(credentials=self.credentials, marketplace=self.marketplace)
            if not end_date:
                end_date = datetime.utcnow().isoformat()
            else:
                end_date = datetime.fromisoformat(end_date).isoformat()

            start_date = datetime.fromisoformat(start_date).isoformat()
            logger.info("Fetching orders from %s to %s", start_date, end_date)

            response = orders_api.get_orders(
                CreatedAfter=start_date,
                CreatedBefore=end_date,
                MarketplaceIds=self.marketplace_ids,
            )
            orders = response.payload.get("Orders", [])
            logger.info("Fetched %s orders", len(orders))
            return orders
        except SellingApiException as exc:
            logger.error("SP-API error while fetching orders: %s", exc)
        except Exception as exc:
            logger.error("Unexpected error while fetching orders: %s", exc)
        return []

    def get_sales_metrics(self, start_date: str, end_date: Optional[str] = None, granularity: str = "Day") -> List[Dict]:
        """Use the Sales API to collect aggregated order metrics"""
        try:
            sales_api = Sales(credentials=self.credentials, marketplace=self.marketplace)
            if not end_date:
                end_date = datetime.utcnow().date().isoformat()

            response = sales_api.get_order_metrics(
                marketplaceIds=self.marketplace_ids,
                interval=f"{start_date}T00:00:00Z--{end_date}T23:59:59Z",
                granularity=granularity,
            )
            return response.payload
        except SellingApiException as exc:
            logger.error("SP-API error while fetching sales metrics: %s", exc)
        except Exception as exc:
            logger.error("Unexpected error while fetching sales metrics: %s", exc)
        return []

    # ----------------
    # Report handling
    # ----------------

    def _get_reports_client(self) -> Reports:
        return Reports(credentials=self.credentials, marketplace=self.marketplace)

    def create_report(self, report_type: str, start_date: str, end_date: Optional[str] = None, **extra) -> Optional[str]:
        end_date = end_date or datetime.utcnow().date().isoformat()
        reports_api = self._get_reports_client()
        payload = {
            "reportType": report_type,
            "dataStartTime": start_date,
            "dataEndTime": end_date,
            "marketplaceIds": self.marketplace_ids,
        }
        payload.update(extra)
        logger.info("Requesting report %s from %s to %s", report_type, start_date, end_date)
        response = reports_api.create_report(**payload)
        return response.payload.get("reportId")

    def wait_for_report(self, report_id: str, timeout_seconds: int = 900, poll_interval: int = 30) -> Dict:
        reports_api = self._get_reports_client()
        start = time.time()
        while time.time() - start < timeout_seconds:
            details = reports_api.get_report(report_id).payload
            status = details.get("processingStatus")
            if status in {"DONE", "DONE_NO_DATA"}:
                return details
            if status in {"CANCELLED", "FATAL"}:
                raise RuntimeError(f"Report {report_id} failed with status {status}")
            logger.info("Report %s still %s, waiting %ss", report_id, status, poll_interval)
            time.sleep(poll_interval)
        raise TimeoutError(f"Timed out waiting for report {report_id}")

    def download_report_document(self, document_id: str) -> str:
        reports_api = self._get_reports_client()
        document = reports_api.get_report_document(document_id, decrypt=True)
        payload = document.payload
        logger.info("Report document payload keys: %s", list(payload.keys()))
        document_body = payload.get("document")
        if document_body:
            if isinstance(document_body, (bytes, bytearray)):
                return document_body.decode("utf-8")
            return document_body
        if "url" in payload:
            import requests

            logger.info("Downloading report document via URL")
            response = requests.get(payload["url"], timeout=60)
            response.raise_for_status()
            content = response.content
            if payload.get("compressionAlgorithm") == "GZIP":
                content = gzip.decompress(content)
            return content.decode("utf-8")
        raise ValueError("Report document payload did not include data")

    def fetch_report_text(
        self,
        report_type: str,
        start_date: str,
        end_date: Optional[str] = None,
        report_options: Optional[Dict] = None,
        **extra,
    ) -> str:
        payload = dict(extra)
        if report_options:
            payload["reportOptions"] = report_options
        report_id = self.create_report(report_type, start_date, end_date, **payload)
        if not report_id:
            raise RuntimeError(f"Failed to request report {report_type}")
        status = self.wait_for_report(report_id)
        document_id = status.get("reportDocumentId")
        if not document_id:
            logger.warning("Report %s returned no document id", report_id)
            return []
        raw_text = self.download_report_document(document_id)
        return raw_text

    def fetch_report_rows(
        self,
        report_type: str,
        start_date: str,
        end_date: Optional[str] = None,
        report_options: Optional[Dict] = None,
        **extra,
    ) -> List[Dict]:
        raw_text = self.fetch_report_text(
            report_type,
            start_date,
            end_date,
            report_options=report_options,
            **extra,
        )
        return self._parse_report_text(raw_text)

    @staticmethod
    def _parse_report_text(text: str) -> List[Dict]:
        if text is None:
            return []
        clean_text = text.strip()
        if not clean_text:
            return []
        first_line = clean_text.splitlines()[0]
        delimiter = "\t" if "\t" in first_line else ","
        reader = csv.DictReader(io.StringIO(clean_text), delimiter=delimiter)
        return [{k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()} for row in reader]

    @staticmethod
    def _parse_child_sales_report(text: str, default_date: str) -> List[Dict]:
        if not text:
            return []
        clean_text = text.strip()
        if not clean_text:
            return []
        if not clean_text.startswith(("{", "[")):
            return AmazonSPAPIClient._parse_report_text(text)
        try:
            payload = json.loads(clean_text)
        except json.JSONDecodeError:
            return AmazonSPAPIClient._parse_report_text(text)

        asin_rows = payload.get("salesAndTrafficByAsin", [])
        normalized: List[Dict] = []
        for entry in asin_rows:
            sales = entry.get("salesByAsin") or {}
            traffic = entry.get("trafficByAsin") or {}
            ordered_sales = sales.get("orderedProductSales") or {}
            ordered_sales_b2b = sales.get("orderedProductSalesB2B") or {}
            normalized.append(
                {
                    "date": default_date,
                    "parentAsin": entry.get("parentAsin"),
                    "childAsin": entry.get("childAsin"),
                    "unitsOrdered": sales.get("unitsOrdered"),
                    "unitsOrderedB2B": sales.get("unitsOrderedB2B"),
                    "orderedProductSales": ordered_sales.get("amount"),
                    "orderedProductSalesB2B": ordered_sales_b2b.get("amount"),
                    "totalOrderItems": sales.get("totalOrderItems"),
                    "totalOrderItemsB2B": sales.get("totalOrderItemsB2B"),
                    "sessions": traffic.get("sessions"),
                    "sessionsB2B": traffic.get("sessionsB2B"),
                    "sessionPercentage": traffic.get("sessionPercentage"),
                    "sessionPercentageB2B": traffic.get("sessionPercentageB2B"),
                    "pageViews": traffic.get("pageViews"),
                    "pageViewsB2B": traffic.get("pageViewsB2B"),
                    "pageViewsPercentage": traffic.get("pageViewsPercentage"),
                    "pageViewsPercentageB2B": traffic.get("pageViewsPercentageB2B"),
                    "buyBoxPercentage": traffic.get("buyBoxPercentage"),
                    "buyBoxPercentageB2B": traffic.get("buyBoxPercentageB2B"),
                    "unitSessionPercentage": traffic.get("unitSessionPercentage"),
                    "unitSessionPercentageB2B": traffic.get("unitSessionPercentageB2B"),
                }
            )
        return normalized

    # ------------------------
    # Domain specific helpers
    # ------------------------

    def fetch_child_traffic_metrics(self, start_date: str, end_date: Optional[str] = None):
        """
        Pull the Business Reports -> Detail Page Sales and Traffic by Child Item dataset.
        Returns one row per child ASIN with sales, units, sessions, and conversion metrics.
        """
        report_options = {
            "dateGranularity": "DAY",
            "asinGranularity": "CHILD",
            "salesChannel": "ALL",
        }
        raw_text = self.fetch_report_text(
            self.CHILD_SALES_REPORT,
            start_date,
            end_date,
            report_options=report_options,
        )
        default_date = end_date or start_date
        rows = self._parse_child_sales_report(raw_text, default_date)
        return rows, raw_text

    def fetch_fba_inventory_positions(self, snapshot_date: str) -> List[Dict]:
        """
        Pull the FBA inventory report which contains total/available/reserved/inbound quantities.
        """
        raw_text = self.fetch_report_text(
            self.FBA_INVENTORY_REPORT,
            snapshot_date,
            snapshot_date,
            additionalInformation={"format": "text/tab-separated-values"},
        )
        rows = self._parse_report_text(raw_text)
        return rows, raw_text

    def fetch_awd_inventory_positions(self, snapshot_date: str):
        """
        Pull the AWD inventory report (if enabled). Report type can be overridden via env.
        """
        try:
            raw_text = self.fetch_report_text(self.AWD_INVENTORY_REPORT, snapshot_date, snapshot_date)
            rows = self._parse_report_text(raw_text)
            return rows, raw_text
        except Exception as exc:
            logger.warning("AWD inventory report failed: %s", exc)
            return [], None

    def fetch_settlement_transactions(self, start_date: str, end_date: Optional[str] = None) -> List[Dict]:
        """
        Download the settlement report (fees, charges, disbursements) for the given window.
        """
        try:
            rows = self.fetch_report_rows(
                self.SETTLEMENT_REPORT,
                start_date,
                end_date,
            )
            return rows
        except Exception as exc:
            logger.error("Failed to download settlement report: %s", exc)
            return []


def extract_kpis_from_orders(orders: List[Dict]) -> Dict:
    """Basic KPI aggregation from Orders payload"""
    if not orders:
        return {}

    total_orders = len(orders)
    total_revenue = sum(float(order.get("OrderTotal", {}).get("Amount", 0)) for order in orders)
    pending_orders = sum(1 for order in orders if order.get("OrderStatus") == "Pending")
    shipped_orders = sum(1 for order in orders if order.get("OrderStatus") == "Shipped")
    avg_order_value = total_revenue / total_orders if total_orders else 0

    return {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "pending_orders": pending_orders,
        "shipped_orders": shipped_orders,
        "average_order_value": avg_order_value,
    }

