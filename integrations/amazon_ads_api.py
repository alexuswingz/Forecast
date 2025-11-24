"""
Amazon Ads API Integration
Handles fetching advertising data from Amazon Advertising API
"""

import requests
import json
import time
import gzip
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AmazonAdsAPIClient:
    """Client for Amazon Advertising API"""
    
    BASE_URLS = {
        'NA': 'https://advertising-api.amazon.com',
        'EU': 'https://advertising-api-eu.amazon.com',
        'FE': 'https://advertising-api-fe.amazon.com'
    }
    
    def __init__(self):
        self.client_id = Config.ADS_API_CLIENT_ID
        self.client_secret = Config.ADS_API_CLIENT_SECRET
        self.refresh_token = Config.ADS_API_REFRESH_TOKEN
        self.profile_id = Config.ADS_API_PROFILE_ID
        self.region = Config.ADS_API_REGION
        self.base_url = self.BASE_URLS.get(self.region, self.BASE_URLS['NA'])
        self.access_token = None
        
    def get_access_token(self) -> Optional[str]:
        """
        Get access token using refresh token
        
        Returns:
            Access token string or None if failed
        """
        try:
            url = 'https://api.amazon.com/auth/o2/token'
            
            payload = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            response = requests.post(url, data=payload)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data.get('access_token')
            logger.info("Successfully obtained access token")
            
            return self.access_token
            
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None
    
    def _make_request(self, endpoint: str, method: str = 'GET', 
                     params: Dict = None, data: Dict = None) -> Optional[Dict]:
        """
        Make API request with authentication
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            params: Query parameters
            data: Request body data
        
        Returns:
            Response data or None if failed
        """
        if not self.access_token:
            self.get_access_token()
        
        if not self.access_token:
            logger.error("No access token available")
            return None
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Amazon-Advertising-API-ClientId': self.client_id,
            'Amazon-Advertising-API-Scope': self.profile_id,
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e}")
            logger.error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error making request: {e}")
            return None
    
    def get_campaigns(self, state_filter: str = None) -> List[Dict]:
        """
        Get list of campaigns
        
        Args:
            state_filter: Filter by state ('enabled', 'paused', 'archived')
        
        Returns:
            List of campaign dictionaries
        """
        endpoint = '/v2/sp/campaigns'
        params = {}
        
        if state_filter:
            params['stateFilter'] = state_filter
        
        campaigns = self._make_request(endpoint, params=params)
        
        if campaigns:
            logger.info(f"Fetched {len(campaigns)} campaigns")
        
        return campaigns or []
    
    def get_campaign_performance(self, start_date: str, end_date: Optional[str] = None,
                                metrics: List[str] = None) -> List[Dict]:
        """
        Get campaign performance metrics
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format (optional)
            metrics: List of metrics to fetch
        
        Returns:
            List of performance data dictionaries
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        
        if not metrics:
            metrics = [
                'impressions',
                'clicks',
                'cost',
                'sales',
                'orders',
                'attributedConversions14d',
                'attributedSales14d'
            ]
        
        endpoint = '/v2/sp/campaigns/report'
        
        payload = {
            'reportDate': start_date,
            'metrics': ','.join(metrics)
        }
        
        # For date range
        if start_date != end_date:
            payload['reportDate'] = f"{start_date}-{end_date}"
        
        logger.info(f"Fetching campaign performance from {start_date} to {end_date}")
        
        # This returns a report ID that needs to be downloaded
        report_response = self._make_request(endpoint, method='POST', data=payload)
        
        if report_response:
            report_id = report_response.get('reportId')
            logger.info(f"Report requested: {report_id}")
            return {'report_id': report_id}
        
        return []
    
    def get_keywords_performance(self, start_date: str, end_date: Optional[str] = None) -> Dict:
        """
        Get keyword performance metrics
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format (optional)
        
        Returns:
            Performance data dictionary
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        
        endpoint = '/v2/sp/keywords/report'
        
        payload = {
            'reportDate': f"{start_date}-{end_date}",
            'metrics': 'impressions,clicks,cost,sales'
        }
        
        logger.info(f"Fetching keyword performance from {start_date} to {end_date}")
        
        report_response = self._make_request(endpoint, method='POST', data=payload)
        
        return report_response or {}
    
    def get_product_ads_performance(self, start_date: str, end_date: Optional[str] = None) -> Dict:
        """
        Get product ads performance metrics
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format (optional)
        
        Returns:
            Performance data dictionary
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        
        endpoint = '/v2/sp/productAds/report'
        
        payload = {
            'reportDate': f"{start_date}-{end_date}",
            'metrics': 'impressions,clicks,cost,attributedSales14d,attributedConversions14d'
        }
        
        logger.info(f"Fetching product ads performance from {start_date} to {end_date}")
        
        report_response = self._make_request(endpoint, method='POST', data=payload)
        
        return report_response or {}
    
    def download_report(self, report_id: str) -> Optional[List[Dict]]:
        """
        Download a completed report
        
        Args:
            report_id: The report ID to download
        
        Returns:
            Report data as list of dictionaries
        """
        endpoint = f'/v2/reports/{report_id}'
        
        report_status = self._make_request(endpoint)

        if not report_status:
            return None

        status = report_status.get('status')

        if status == 'SUCCESS':
            download_url = report_status.get('location')
            compression = report_status.get('compression')

            if download_url:
                try:
                    response = requests.get(download_url)
                    response.raise_for_status()

                    content = response.content
                    if compression == 'GZIP':
                        content = gzip.decompress(content)

                    try:
                        data = json.loads(content.decode('utf-8'))
                    except Exception:
                        data = json.loads(content.decode('utf-16'))

                    logger.info(f"Downloaded report {report_id}")
                    return data

                except Exception as e:
                    logger.error(f"Error downloading report: {e}")
                    return None
        else:
            logger.info(f"Report status: {status}")
            return None

    # ---------- Advertised product helper methods ----------

    def create_advertised_product_report(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        metrics: Optional[List[str]] = None,
        time_unit: str = "DAILY",
    ) -> Optional[str]:
        """
        Request a Sponsored Products advertised product report for a date range.
        Dates should be 'YYYY-MM-DD'.
        """
        endpoint = '/v2/sp/advertisedProducts/report'
        if not end_date:
            end_date = start_date

        payload = {
            'metrics': ','.join(metrics or [
                'impressions',
                'clicks',
                'cost',
                'attributedSales14d',
                'attributedUnitsOrdered14d',
                'attributedConversions14dSameSKU'
            ]),
            'timeUnit': time_unit
        }

        if start_date == end_date:
            payload['reportDate'] = start_date.replace('-', '')
        else:
            payload['startDate'] = start_date.replace('-', '')
            payload['endDate'] = end_date.replace('-', '')

        response = self._make_request(endpoint, method='POST', data=payload)
        if response and 'reportId' in response:
            logger.info(f"Created advertised product report {response['reportId']} for {start_date} - {end_date}")
            return response['reportId']
        return None

    def get_ads_report_status(self, report_id: str) -> Optional[Dict]:
        endpoint = f'/v2/reports/{report_id}'
        return self._make_request(endpoint)

    def wait_for_ads_report(self, report_id: str, timeout_seconds: int = 900, poll_interval: int = 30) -> Optional[Dict]:
        start = time.time()
        while time.time() - start < timeout_seconds:
            details = self.get_ads_report_status(report_id)
            if not details:
                time.sleep(poll_interval)
                continue
            status = details.get('status')
            if status == 'SUCCESS':
                return details
            if status in {'FAILURE', 'CANCELLED'}:
                logger.error(f"Ads report {report_id} failed with status {status}")
                return None
            logger.info(f"Ads report {report_id} still {status}, waiting {poll_interval}s")
            time.sleep(poll_interval)
        logger.error(f"Timed out waiting for ads report {report_id}")
        return None

    def download_ads_report(self, report_id: str, wait: bool = True) -> Optional[List[Dict]]:
        if wait:
            details = self.wait_for_ads_report(report_id)
            if not details:
                return None
        else:
            details = self.get_ads_report_status(report_id)
            if not details or details.get('status') != 'SUCCESS':
                return None

        download_url = details.get('location')
        compression = details.get('compression')
        if not download_url:
            return None

        try:
            response = requests.get(download_url)
            response.raise_for_status()
            content = response.content
            if compression == 'GZIP':
                content = gzip.decompress(content)
            try:
                return json.loads(content.decode('utf-8'))
            except Exception:
                return json.loads(content.decode('utf-16'))
        except Exception as exc:
            logger.error(f"Error downloading ads report {report_id}: {exc}")
            return None


def extract_kpis_from_ads(campaigns: List[Dict], performance_data: List[Dict] = None) -> Dict:
    """
    Extract KPIs from advertising data
    
    Args:
        campaigns: List of campaign dictionaries
        performance_data: List of performance data dictionaries
    
    Returns:
        Dictionary of calculated KPIs
    """
    kpis = {
        'total_campaigns': len(campaigns),
        'active_campaigns': sum(1 for c in campaigns if c.get('state') == 'enabled'),
    }
    
    if performance_data:
        total_impressions = sum(p.get('impressions', 0) for p in performance_data)
        total_clicks = sum(p.get('clicks', 0) for p in performance_data)
        total_cost = sum(p.get('cost', 0) for p in performance_data)
        total_sales = sum(p.get('attributedSales14d', 0) for p in performance_data)
        
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        acos = (total_cost / total_sales * 100) if total_sales > 0 else 0
        roas = (total_sales / total_cost) if total_cost > 0 else 0
        
        kpis.update({
            'total_impressions': total_impressions,
            'total_clicks': total_clicks,
            'total_ad_spend': total_cost,
            'total_ad_sales': total_sales,
            'ctr': ctr,
            'acos': acos,
            'roas': roas
        })
    
    return kpis

