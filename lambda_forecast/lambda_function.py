"""
AWS Lambda Function for Forecast API
Endpoints for inventory, forecasting, and chart data
"""
import json
import os
from datetime import datetime, timedelta, date
from decimal import Decimal
import statistics
import psycopg2
from psycopg2.extras import RealDictCursor


# Database connection parameters from environment variables
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder for Decimal, datetime, and date types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super(DecimalEncoder, self).default(obj)


def get_db_connection():
    """Create database connection with optimized settings"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor,
        connect_timeout=5,
        options='-c statement_timeout=55000'  # 55 second query timeout
    )


PEAK_WEIGHTS = [1, 2, 4, 7, 11, 13, 11, 7, 4, 2, 1]
FORECAST_WEIGHTS = [1, 3, 5, 7, 5, 3, 1]
SALES_VELOCITY_WEIGHT = 0.25  # Default 25%
SV_VELOCITY_WEIGHT = 0.15  # Default 15% (Search Volume Velocity)


def _peak_envelope(values):
    result = []
    n = len(values)
    for i in range(n):
        start = max(0, i - 2)
        end = min(n, i + 3)
        window = values[start:end]
        result.append(max(window) if window else 0.0)
    return result


def _smooth_envelope(peak_values):
    result = []
    n = len(peak_values)
    for i in range(n):
        start = max(0, i - 1)
        end = min(n, i + 2)
        window = peak_values[start:end]
        result.append(sum(window) / len(window) if window else 0.0)
    return result


def _final_curve(units, peak, smooth):
    return [max(u, p, s) for u, p, s in zip(units, peak, smooth)]


def _final_smooth(final_curve):
    result = []
    n = len(final_curve)
    radius = len(PEAK_WEIGHTS) // 2
    for i in range(n):
        weighted_sum = 0.0
        weight_total = 0.0
        for offset, weight in zip(range(-radius, radius + 1), PEAK_WEIGHTS):
            idx = i + offset
            if 0 <= idx < n:
                weighted_sum += final_curve[idx] * weight
                weight_total += weight
        result.append(weighted_sum / weight_total if weight_total else 0.0)
    return result


def _seasonal_placeholder(units, weeks_ahead):
    if not units:
        return [0.0] * weeks_ahead
    
    recent = units[-26:] or units
    baseline = statistics.mean(recent) if recent else 0.0
    
    if len(units) >= 13:
        seasonal_period = min(52, len(units))
        seasonal_slice = units[-seasonal_period:]
        avg_units = statistics.mean(seasonal_slice) if seasonal_slice else baseline
        if avg_units:
            factors = [u / avg_units for u in seasonal_slice]
        else:
            factors = [1.0] * len(seasonal_slice)
        cycles = (weeks_ahead + len(factors) - 1) // len(factors)
        extended = (factors * cycles)[:weeks_ahead]
        return [baseline * f for f in extended]
    
    return [baseline] * weeks_ahead


def _build_seasonal_baseline(final_smooth, lag=52):
    baseline = [None] * len(final_smooth)
    for i in range(lag, len(final_smooth)):
        baseline[i] = final_smooth[i - lag]
    return baseline


def _forecast_peak_from_baseline(baseline):
    peak = []
    for i in range(len(baseline)):
        values = [baseline[j] for j in range(max(0, i - 2), i + 1) if baseline[j] is not None]
        peak.append(max(values) if values else 0.0)
    return peak


def _forecast_final_smooth(peak_values):
    result = []
    n = len(peak_values)
    radius = len(FORECAST_WEIGHTS) // 2
    for i in range(n):
        weighted_sum = 0.0
        weight_total = 0.0
        for offset, weight in zip(range(-radius, radius + 1), FORECAST_WEIGHTS):
            idx = i + offset
            if 0 <= idx < n:
                weighted_sum += peak_values[idx] * weight
                weight_total += weight
        result.append(weighted_sum / weight_total if weight_total else 0.0)
    return result


def _weighted_daily_average(series):
    windows = [1, 2, 4, 6]
    totals = []
    for weeks in windows:
        if len(series) >= weeks:
            window = series[-weeks:]
            totals.append(sum(window) / (7.0 * weeks))
        else:
            return None
    return 0.25 * sum(totals)


def _sales_velocity_ratio(actual_final_smooth, baseline_final_smooth):
    paired = [
        (a, b) for a, b in zip(actual_final_smooth, baseline_final_smooth)
        if a is not None and b is not None and b != 0
    ]
    if len(paired) < 6:
        return 0.0
    tail_actual = [p[0] for p in paired][-6:]
    tail_baseline = [p[1] for p in paired][-6:]
    actual_avg = _weighted_daily_average(tail_actual)
    baseline_avg = _weighted_daily_average(tail_baseline)
    if actual_avg is None or baseline_avg in (None, 0):
        return 0.0
    return (actual_avg / baseline_avg) - 1


def cors_response(status_code, body):
    """Create CORS-enabled response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }


def get_product_inventory(asin):
    """
    Get product details and current inventory
    
    Returns:
        {
            "product": {
                "asin": "B0BRTK1P8Z",
                "sku": "...",
                "name": "Monstera Plant Food",
                "brand": "TPS Plant Foods",
                "size": "8oz"
            },
            "inventory": {
                "fba": {
                    "total": 60,
                    "available": 12,
                    "reserved": 24,
                    "inbound": 0
                },
                "awd": {
                    "total": 60,
                    "outbound_to_fba": 60,
                    "available": 12,
                    "reserved": 24
                }
            },
            "latest_date": "2025-11-14"
        }
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get product details
        cur.execute("""
            SELECT 
                p.asin,
                p.sku,
                p.product_name as name,
                p.brand,
                p.size
            FROM products p
            WHERE p.asin = %s
            LIMIT 1
        """, (asin,))
        
        product = cur.fetchone()
        
        if not product:
            return {'error': 'Product not found'}
        
        # Get latest inventory snapshot
        cur.execute("""
            SELECT 
                snapshot_date,
                fulfillment_program,
                SUM(available_quantity) as available,
                SUM(reserved_quantity) as reserved,
                SUM(inbound_working_quantity + inbound_shipped_quantity + inbound_receiving_quantity) as inbound,
                SUM(total_quantity) as total
            FROM inventory_snapshots
            WHERE asin = %s
            AND snapshot_date = (
                SELECT MAX(snapshot_date) 
                FROM inventory_snapshots 
                WHERE asin = %s
            )
            GROUP BY snapshot_date, fulfillment_program
        """, (asin, asin))
        
        inventory_rows = cur.fetchall()
        
        # Parse inventory by fulfillment program
        fba = {'total': 0, 'available': 0, 'reserved': 0, 'inbound': 0}
        awd = {'total': 0, 'outbound_to_fba': 0, 'available': 0, 'reserved': 0}
        latest_date = None
        
        for row in inventory_rows:
            latest_date = row['snapshot_date']
            program = row['fulfillment_program'] or 'FBA'
            
            if 'AWD' in program.upper():
                awd['total'] += int(row['total'] or 0)
                awd['available'] += int(row['available'] or 0)
                awd['reserved'] += int(row['reserved'] or 0)
                awd['outbound_to_fba'] += int(row['inbound'] or 0)
            else:
                fba['total'] += int(row['total'] or 0)
                fba['available'] += int(row['available'] or 0)
                fba['reserved'] += int(row['reserved'] or 0)
                fba['inbound'] += int(row['inbound'] or 0)
        
        return {
            'product': dict(product),
            'inventory': {
                'fba': fba,
                'awd': awd
            },
            'latest_date': str(latest_date) if latest_date else None
        }
        
    finally:
        cur.close()
        conn.close()


def get_forecast_chart_data(asin, weeks_ahead=52, sales_velocity_weight=None, sv_velocity_weight=None):
    """
    Excel-accurate smoothing generated on the fly (no pre-aggregated tables).
    Supports adjustable velocity weights for real-time forecast changes.
    
    Args:
        asin: Product ASIN
        weeks_ahead: Number of weeks to forecast (max 104)
        sales_velocity_weight: Weight for sales velocity adjustment (0-1, default 0.25)
        sv_velocity_weight: Weight for search volume velocity adjustment (0-1, default 0.15)
    """
    # Use defaults if not provided
    if sales_velocity_weight is None:
        sales_velocity_weight = SALES_VELOCITY_WEIGHT
    if sv_velocity_weight is None:
        sv_velocity_weight = SV_VELOCITY_WEIGHT
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get sales data
        cur.execute("""
            SELECT 
                DATE_TRUNC('week', date)::date + 6 as week_end,
                SUM(units_sold) as units_sold
            FROM daily_product_metrics
            WHERE asin = %s
            GROUP BY DATE_TRUNC('week', date)
            ORDER BY week_end
        """, (asin,))
        
        rows = cur.fetchall()
        if not rows:
            return {'error': 'No historical data found'}
        
        hist_dates = []
        hist_units = []
        for row in rows:
            week_end = row['week_end']
            if isinstance(week_end, str):
                week_end = datetime.strptime(week_end, '%Y-%m-%d').date()
            hist_dates.append(week_end)
            units = row.get('units_sold') or 0
            if isinstance(units, Decimal):
                units = float(units)
            hist_units.append(float(units))
        
        hist_len = len(hist_units)
        if hist_len == 0:
            return {'error': 'No historical data found'}
        
        # Get search volume (sessions) data for velocity calculation
        cur.execute("""
            SELECT 
                DATE_TRUNC('week', date)::date + 6 as week_end,
                SUM(sessions) as sessions
            FROM daily_product_metrics
            WHERE asin = %s
            AND sessions IS NOT NULL
            GROUP BY DATE_TRUNC('week', date)
            ORDER BY week_end
        """, (asin,))
        
        sv_rows = cur.fetchall()
        sv_data = {}
        for row in sv_rows:
            week_end = row['week_end']
            if isinstance(week_end, date):
                week_end_str = week_end.isoformat()
            else:
                week_end_str = str(week_end)
            sessions = row.get('sessions') or 0
            if isinstance(sessions, Decimal):
                sessions = float(sessions)
            sv_data[week_end_str] = float(sessions)
        
        horizon = max(1, min(int(weeks_ahead), 104))
        placeholder = _seasonal_placeholder(hist_units, horizon)
        
        combined_units = hist_units + placeholder
        peak_env = _peak_envelope(combined_units)
        smooth_env = _smooth_envelope(peak_env)
        final_curve = _final_curve(combined_units, peak_env, smooth_env)
        final_smooth = _final_smooth(final_curve)
        
        hist_smooth = final_smooth[:hist_len]
        baseline = _build_seasonal_baseline(final_smooth)
        baseline_peak = _forecast_peak_from_baseline(baseline)
        baseline_final = _forecast_final_smooth(baseline_peak)
        
        # Calculate sales velocity adjustment
        sales_velocity_adj = _sales_velocity_ratio(final_smooth[:hist_len], baseline_final[:hist_len])
        
        # Calculate search volume velocity adjustment
        sv_velocity_adj = 0.0
        if sv_data:
            sv_values = []
            for week_date in hist_dates:
                week_str = week_date.isoformat()
                sv_values.append(sv_data.get(week_str, 0.0))
            
            if len(sv_values) >= 24:  # Need at least 24 weeks for comparison
                recent_sv = sv_values[-12:]  # Last 12 weeks
                baseline_sv = sv_values[-24:-12]  # Previous 12 weeks
                recent_avg = sum(recent_sv) / len(recent_sv) if recent_sv else 0
                baseline_avg = sum(baseline_sv) / len(baseline_sv) if baseline_sv else 0
                
                if baseline_avg > 0:
                    sv_velocity_adj = (recent_avg - baseline_avg) / baseline_avg
        
        # Combine both velocity adjustments with their respective weights
        total_adjustment = (sales_velocity_adj * sales_velocity_weight) + (sv_velocity_adj * sv_velocity_weight)
        total_multiplier = max(0.0, 1.0 + total_adjustment)
        
        forecast_base = final_smooth[hist_len:hist_len + horizon]
        forecast_adjusted = [max(0.0, fb * total_multiplier) for fb in forecast_base]
        
        last_week = hist_dates[-1]
        forecast_entries = []
        for idx, base_value in enumerate(forecast_base):
            week_date = last_week + timedelta(days=7 * (idx + 1))
            forecast_entries.append({
                'week_end': week_date.isoformat(),
                'forecast_base': round(base_value, 1),
                'forecast_adjusted': round(forecast_adjusted[idx], 1)
            })
        
        historical_entries = []
        for week_date, raw, smooth in zip(hist_dates, hist_units, hist_smooth):
            historical_entries.append({
                'week_end': week_date.isoformat(),
                'units_sold': round(raw, 1),
                'units_smooth': round(smooth, 1)
            })
        
        if forecast_adjusted:
            avg_window = min(len(forecast_adjusted), 12)
            avg_weekly = sum(forecast_adjusted[:avg_window]) / avg_window
        else:
            recent_hist = hist_units[-min(len(hist_units), 12):]
            avg_weekly = sum(recent_hist) / len(recent_hist)
        
        metadata = {
            'sales_velocity_adj': round(sales_velocity_adj, 4),
            'sv_velocity_adj': round(sv_velocity_adj, 4),
            'total_adjustment': round(total_adjustment, 4),
            'sales_velocity_weight': sales_velocity_weight,
            'sv_velocity_weight': sv_velocity_weight,
            'forecast_weeks': horizon,
            'avg_weekly_sales': round(avg_weekly, 1)
        }
        
        return {
            'historical': historical_entries,
            'forecast': forecast_entries,
            'metadata': metadata
        }
        
    finally:
        cur.close()
        conn.close()


def calculate_forecast_days(asin, settings=None):
    """
    Calculate DOI and forecast days
    
    Returns:
        {
            "current_date": "2025-11-17",
            "doi_goal": "2025-04-13",
            "fba_available_days": 23,
            "total_days": 92,
            "forecast_days": 162,
            "weekly_forecast_avg": 858.5,
            "inventory": {
                "total": 2392331,
                "available_fba": 2392267
            }
        }
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get settings
        doi_goal = (settings or {}).get('doi_goal', 120)
        lead_time = (settings or {}).get('lead_time', 37)
        
        # Get current inventory
        cur.execute("""
            SELECT 
                SUM(available_quantity) as available_fba,
                SUM(total_quantity) as total
            FROM inventory_snapshots
            WHERE asin = %s
            AND snapshot_date = (
                SELECT MAX(snapshot_date) 
                FROM inventory_snapshots 
                WHERE asin = %s
            )
        """, (asin, asin))
        
        inv_row = cur.fetchone()
        total_inv = int(inv_row['total'] or 0)
        available_fba = int(inv_row['available_fba'] or 0)
        
        # Prefer precomputed forecast averages (weekly_forecast_metrics)
        cur.execute("""
            WITH ranked AS (
                SELECT 
                    forecast_adjusted,
                    ROW_NUMBER() OVER (PARTITION BY asin ORDER BY week_end) as rn
                FROM weekly_forecast_metrics
                WHERE asin = %s
                  AND is_forecast = TRUE
            )
            SELECT AVG(forecast_adjusted) as avg_weekly_sales
            FROM ranked
            WHERE rn <= 12
        """, (asin,))
        
        sales_row = cur.fetchone()
        avg_weekly_sales = float(sales_row['avg_weekly_sales'] or 0) if sales_row else 0.0
        
        if avg_weekly_sales <= 0:
            # Fallback to recent actual sales if forecast data missing
            cur.execute("""
                SELECT AVG(weekly_units) as avg_weekly_sales
                FROM (
                    SELECT 
                        DATE_TRUNC('week', date)::date + 6 as week_end,
                        SUM(units_sold) as weekly_units
                    FROM daily_product_metrics
                    WHERE asin = %s
                    AND date >= CURRENT_DATE - INTERVAL '12 weeks'
                    GROUP BY DATE_TRUNC('week', date)
                    ORDER BY week_end DESC
                    LIMIT 12
                ) recent_weeks
            """, (asin,))
            fallback_row = cur.fetchone()
            avg_weekly_sales = float(fallback_row['avg_weekly_sales'] or 0) if fallback_row else 0.0
        
        avg_daily_sales = avg_weekly_sales / 7.0 if avg_weekly_sales > 0 else 0
        
        # Calculate DOI
        if avg_daily_sales > 0:
            fba_available_days = int(available_fba / avg_daily_sales)
            total_days = int(total_inv / avg_daily_sales)
        else:
            fba_available_days = 0
            total_days = 0
        
        # Calculate forecast period (remaining to hit DOI goal)
        forecast_days = max(0, doi_goal - total_days)
        
        # Calculate target dates
        current_date = datetime.now().date()
        doi_goal_date = current_date + timedelta(days=doi_goal)
        runout_date = current_date + timedelta(days=total_days)
        
        # Calculate units to make (to reach DOI goal)
        if avg_daily_sales > 0:
            target_inventory = avg_daily_sales * doi_goal
            units_to_make = max(0, int(target_inventory - total_inv))
        else:
            units_to_make = 0
        
        return {
            'current_date': str(current_date),
            'doi_goal_date': str(doi_goal_date),
            'runout_date': str(runout_date),
            'doi_goal': doi_goal,
            'lead_time': lead_time,
            'fba_available_days': fba_available_days,
            'total_days': total_days,
            'forecast_days': forecast_days,
            'doi_fba_available': fba_available_days,  # Alias for frontend
            'doi_total': total_days,  # Alias for frontend
            'units_to_make': units_to_make,
            'avg_daily_sales': round(avg_daily_sales, 1),
            'weekly_forecast_avg': round(avg_weekly_sales, 1),
            'daily_forecast_avg': round(avg_daily_sales, 1),
            'inventory': {
                'total': total_inv,
                'available_fba': available_fba
            }
        }
        
    finally:
        cur.close()
        conn.close()


def _get_forecast_chart_data_precomputed(asin, weeks_ahead=52):
    """
    Get historical and forecast data for charting
    
    Returns:
        {
            "historical": [
                {"week_end": "2024-05-06", "units_sold": 247, "units_smooth": 289.5},
                ...
            ],
            "forecast": [
                {"week_end": "2025-11-18", "forecast_base": 858, "forecast_adjusted": 694},
                ...
            ],
            "metadata": {
                "velocity_adjustment": -0.1911,
                "forecast_weeks": 52
            }
        }
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        def legacy_chart():
            cur.execute("""
                SELECT 
                    DATE_TRUNC('week', date)::date + 6 as week_end,
                    SUM(units_sold) as units_sold
                FROM daily_product_metrics
                WHERE asin = %s
                AND date >= CURRENT_DATE - INTERVAL '52 weeks'
                GROUP BY DATE_TRUNC('week', date)
                ORDER BY week_end
            """, (asin,))
            
            historical = [dict(row) for row in cur.fetchall()]
            
            if not historical:
                return {'error': 'No historical data found'}
            
            for row in historical:
                if isinstance(row['week_end'], date):
                    row['week_end'] = str(row['week_end'])
                if isinstance(row.get('units_sold'), Decimal):
                    row['units_sold'] = float(row['units_sold'])
            
            for i in range(len(historical)):
                start = max(0, i - 2)
                end = min(len(historical), i + 3)
                window_values = [historical[j]['units_sold'] for j in range(start, end)]
                historical[i]['units_smooth'] = sum(window_values) / len(window_values)
            
            recent_12 = [h['units_sold'] for h in historical[-12:]]
            overall_avg = sum(h['units_sold'] for h in historical) / len(historical)
            recent_avg = sum(recent_12) / len(recent_12)
            velocity_adj = (recent_avg - overall_avg) / overall_avg if overall_avg > 0 else 0
            
            last_52_weeks = [h['units_sold'] for h in historical[-52:]]
            avg_units = sum(last_52_weeks) / len(last_52_weeks)
            seasonal_factors = [u / avg_units if avg_units > 0 else 1 for u in last_52_weeks]
            
            forecast = []
            last_date = historical[-1]['week_end']
            if isinstance(last_date, str):
                last_date = datetime.strptime(last_date, '%Y-%m-%d').date()
            
            for i in range(weeks_ahead):
                week_date = last_date + timedelta(days=7 * (i + 1))
                seasonal_factor = seasonal_factors[i % len(seasonal_factors)]
                base_forecast = avg_units * seasonal_factor
                adjusted_forecast = base_forecast * (1 + velocity_adj * 0.25)
                
                forecast.append({
                    'week_end': str(week_date),
                    'forecast_base': round(base_forecast, 1),
                    'forecast_adjusted': round(adjusted_forecast, 1)
                })
            
            return {
                'historical': historical,
                'forecast': forecast,
                'metadata': {
                    'velocity_adjustment': round(velocity_adj, 4),
                    'forecast_weeks': weeks_ahead,
                    'avg_weekly_sales': round(avg_units, 1)
                }
            }
        
        cur.execute("""
            SELECT 
                week_end,
                units_sold,
                units_final_smooth,
                forecast_base,
                forecast_adjusted,
                is_forecast
            FROM weekly_forecast_metrics
            WHERE asin = %s
            ORDER BY week_end
        """, (asin,))
        
        rows = cur.fetchall()
        
        if rows:
            historical = []
            forecast = []
            
            for row in rows:
                week_end = row['week_end']
                week_str = week_end.isoformat() if isinstance(week_end, (datetime, date)) else str(week_end)
                
                if row['is_forecast']:
                    forecast.append({
                        'week_end': week_str,
                        'forecast_base': float(row['forecast_base'] or 0),
                        'forecast_adjusted': float(row['forecast_adjusted'] or 0)
                    })
                else:
                    historical.append({
                        'week_end': week_str,
                        'units_sold': float(row['units_sold'] or 0),
                        'units_smooth': float(row['units_final_smooth'] or 0)
                    })
            
            forecast = forecast[:weeks_ahead]
            
            cur.execute("""
                SELECT 
                    sales_velocity_adj,
                    sv_velocity_adj,
                    total_adjustment,
                    forecast_weeks,
                    generated_at
                FROM forecast_summaries
                WHERE asin = %s
            """, (asin,))
            
            summary = cur.fetchone()
            metadata = {
                'velocity_adjustment': float(summary['total_adjustment'] or 0) if summary else 0.0,
                'forecast_weeks': summary['forecast_weeks'] if summary and summary['forecast_weeks'] else weeks_ahead,
                'generated_at': summary['generated_at'].isoformat() if summary and summary['generated_at'] else None
            }
            
            avg_window = min(len(forecast), 12)
            if avg_window > 0:
                metadata['avg_weekly_sales'] = round(sum(item['forecast_adjusted'] for item in forecast[:avg_window]) / avg_window, 1)
            else:
                metadata['avg_weekly_sales'] = 0.0
            
            return {
                'historical': historical,
                'forecast': forecast,
                'metadata': metadata
            }
        
        return legacy_chart()
        
    finally:
        cur.close()
        conn.close()


def get_all_products():
    """
    Get list of all products with inventory
    
    Returns:
        [
            {
                "asin": "B0C73TDZCQ",
                "name": "Hydrangea Fertilizer",
                "brand": "TPS Nutrients",
                "has_data": true
            },
            ...
        ]
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # FAST query using pre-aggregated data
        cur.execute("""
            SELECT DISTINCT
                p.asin,
                p.product_name as name,
                p.brand,
                CASE WHEN d.asin IS NOT NULL THEN true ELSE false END as has_data
            FROM products p
            LEFT JOIN (
                SELECT DISTINCT asin 
                FROM daily_product_metrics 
                WHERE date >= CURRENT_DATE - INTERVAL '12 months'
            ) d ON p.asin = d.asin
            ORDER BY has_data DESC, p.product_name
        """)
        
        products = [dict(row) for row in cur.fetchall()]
        return {'products': products}
        
    finally:
        cur.close()
        conn.close()


def get_product_metrics(asin, days=30):
    """
    Get aggregated metrics for a product over a date range with period comparison
    
    Args:
        asin: Product ASIN
        days: Number of days for current period (default: 30)
    
    Returns:
        {
            "current_period": {...},
            "prior_period": {...},
            "changes": {...}
        }
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Calculate date ranges
        today = date.today()
        current_start = today - timedelta(days=days)
        prior_start = current_start - timedelta(days=days)
        prior_end = current_start - timedelta(days=1)
        
        # Get product info
        cur.execute("""
            SELECT product_name, brand, size
            FROM products
            WHERE asin = %s
            LIMIT 1
        """, (asin,))
        
        product = cur.fetchone()
        if not product:
            return {"error": "Product not found"}
        
        # Get COGS once (doesn't change between periods)
        cur.execute("""
            SELECT cogs_amount
            FROM product_cogs
            WHERE asin = %s
            LIMIT 1
        """, (asin,))
        cogs_row = cur.fetchone()
        unit_cost = float(cogs_row['cogs_amount']) if cogs_row else 0
        
        # Helper function to get metrics for a date range (ULTRA-FAST from pre-aggregated table)
        def get_period_metrics(start_date, end_date):
            # Query pre-aggregated daily_product_metrics table (10-100x faster!)
            cur.execute("""
                SELECT 
                    COALESCE(SUM(units_sold), 0) as units,
                    COALESCE(SUM(sales_amount), 0) as sales,
                    COALESCE(SUM(orders_count), 0) as orders,
                    COALESCE(SUM(sessions), 0) as sessions,
                    COALESCE(AVG(conversion_rate), 0) as conversion_rate,
                    COALESCE(SUM(page_views), 0) as page_views,
                    COALESCE(SUM(ad_spend), 0) as ad_spend,
                    COALESCE(SUM(ad_sales), 0) as ad_sales,
                    COALESCE(SUM(ad_clicks), 0) as ad_clicks,
                    COALESCE(SUM(ad_impressions), 0) as ad_impressions,
                    COALESCE(SUM(ad_orders), 0) as ad_orders
                FROM daily_product_metrics
                WHERE asin = %s
                AND date BETWEEN %s AND %s
            """, (asin, start_date, end_date))
            
            data = cur.fetchone()
            
            # Calculate metrics  
            units = int(data['units'])
            sales_amount = float(data['sales'])
            sessions = int(data['sessions'])
            conversion_rate = float(data['conversion_rate'])
            page_views = int(data['page_views'])
            ad_spend = float(data['ad_spend'])
            ad_sales = float(data['ad_sales'])
            ad_clicks = int(data['ad_clicks'])
            ad_impressions = int(data['ad_impressions'])
            
            # Derived metrics
            avg_price = sales_amount / units if units > 0 else 0
            tacos = (ad_spend / sales_amount * 100) if sales_amount > 0 else 0
            organic_sales_val = sales_amount - ad_sales
            organic_sales_pct = (organic_sales_val / sales_amount * 100) if sales_amount > 0 else 0
            
            cost_of_goods = units * unit_cost
            gross_profit = sales_amount - cost_of_goods
            net_profit = gross_profit - ad_spend
            profit_margin = (net_profit / sales_amount * 100) if sales_amount > 0 else 0
            
            return {
                "units_sold": units,
                "sales": round(sales_amount, 2),
                "sessions": sessions,
                "conversion_rate": round(conversion_rate, 2),
                "page_views": page_views,
                "tacos": round(tacos, 2),
                "price": round(avg_price, 2),
                "profit_margin": round(profit_margin, 2),
                "profit_total": round(net_profit, 2),
                "organic_sales_pct": round(organic_sales_pct, 2),
                "ad_spend": round(ad_spend, 2),
                "ad_sales": round(ad_sales, 2),
                "ad_clicks": ad_clicks,
                "ad_impressions": ad_impressions,
                "organic_sales": round(organic_sales_val, 2)
            }
        
        # Get current and prior period metrics
        current = get_period_metrics(current_start, today)
        prior = get_period_metrics(prior_start, prior_end)
        
        # Calculate changes (%)
        def calc_change(current_val, prior_val):
            if prior_val == 0:
                return 0
            return round(((current_val - prior_val) / prior_val * 100), 1)
        
        changes = {
            "units_sold": calc_change(current["units_sold"], prior["units_sold"]),
            "sales": calc_change(current["sales"], prior["sales"]),
            "sessions": calc_change(current["sessions"], prior["sessions"]),
            "conversion_rate": calc_change(current["conversion_rate"], prior["conversion_rate"]),
            "tacos": calc_change(current["tacos"], prior["tacos"]),
            "price": calc_change(current["price"], prior["price"]),
            "profit_margin": calc_change(current["profit_margin"], prior["profit_margin"]),
            "profit_total": calc_change(current["profit_total"], prior["profit_total"]),
            "organic_sales_pct": calc_change(current["organic_sales_pct"], prior["organic_sales_pct"])
        }
        
        return {
            "product": {
                "asin": asin,
                "name": product["product_name"],
                "brand": product["brand"],
                "size": product["size"]
            },
            "date_range": {
                "current_start": current_start.isoformat(),
                "current_end": today.isoformat(),
                "prior_start": prior_start.isoformat(),
                "prior_end": prior_end.isoformat(),
                "days": days
            },
            "current_period": current,
            "prior_period": prior,
            "changes": changes
        }
        
    finally:
        cur.close()
        conn.close()


def get_planning_table(page=1, limit=20):
    """
    Get planning table data for all products with pagination
    
    Args:
        page: Page number (1-based)
        limit: Items per page (default 50)
    
    Returns:
        {
            "products": [...],
            "pagination": {
                "page": 1,
                "limit": 50,
                "total": 150,
                "total_pages": 3
            }
        }
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get total count (ultra-fast approximation)
        cur.execute("""
            SELECT COUNT(DISTINCT asin) as total
            FROM order_items
            WHERE order_date::timestamp >= CURRENT_DATE - INTERVAL '30 days'
        """)
        
        result = cur.fetchone()
        total_count = result['total'] if result else 0
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        
        # Get paginated products with metrics (JOIN-optimized for speed)
        cur.execute("""
            WITH recent_asins AS (
                SELECT DISTINCT asin
                FROM order_items
                WHERE order_date::timestamp >= CURRENT_DATE - INTERVAL '30 days'
                ORDER BY asin
                LIMIT 1000
            ),
            sales_metrics AS (
                SELECT 
                    asin,
                    SUM(CASE WHEN order_date::timestamp >= CURRENT_DATE - INTERVAL '7 days' THEN quantity ELSE 0 END) as sales_7,
                    SUM(CASE WHEN order_date::timestamp >= CURRENT_DATE - INTERVAL '30 days' THEN quantity ELSE 0 END) as sales_30,
                    COUNT(CASE WHEN order_date::timestamp >= CURRENT_DATE - INTERVAL '12 weeks' THEN 1 END) as order_count_12w
                FROM order_items
                WHERE asin IN (SELECT asin FROM recent_asins)
                GROUP BY asin
            ),
            latest_inventory AS (
                SELECT DISTINCT ON (asin)
                    asin,
                    total_quantity
                FROM inventory_snapshots
                WHERE asin IN (SELECT asin FROM recent_asins)
                ORDER BY asin, snapshot_date DESC
            ),
            forecast_metrics AS (
                SELECT 
                    asin,
                    forecast_adjusted,
                    ROW_NUMBER() OVER (PARTITION BY asin ORDER BY week_end) as rn
                FROM weekly_forecast_metrics
                WHERE asin IN (SELECT asin FROM recent_asins)
                  AND is_forecast = TRUE
            ),
            forecast_avg AS (
                SELECT asin, AVG(forecast_adjusted) as weekly_forecast
                FROM forecast_metrics
                WHERE rn <= 12
                GROUP BY asin
            )
            SELECT 
                p.asin,
                p.brand,
                p.product_name as product,
                p.size,
                COALESCE(sm.sales_7, 0) as sales_7_day,
                COALESCE(sm.sales_30, 0) as sales_30_day,
                COALESCE(fa.weekly_forecast, 0) as weekly_forecast,
                COALESCE(li.total_quantity, 0) as inventory
            FROM products p
            INNER JOIN recent_asins ra ON ra.asin = p.asin
            LEFT JOIN sales_metrics sm ON sm.asin = p.asin
            LEFT JOIN latest_inventory li ON li.asin = p.asin
            LEFT JOIN forecast_avg fa ON fa.asin = p.asin
            ORDER BY p.brand, p.product_name, p.size
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        products = []
        for row in cur.fetchall():
            product = dict(row)
            # Convert Decimal to int/float for JSON
            for key in ['doi_fba', 'doi_total', 'inventory', 'weekly_forecast', 'sales_7_day', 'sales_30_day']:
                if isinstance(product.get(key), Decimal):
                    product[key] = int(product[key])
            
            weekly_forecast = float(product.get('weekly_forecast') or 0)
            product['forecast'] = weekly_forecast
        
            if weekly_forecast > 0:
                daily_rate = weekly_forecast / 7.0
                product['doi_total'] = int(product['inventory'] / daily_rate) if product['inventory'] else 0
                product['doi_fba'] = product['doi_total']
            else:
                product['doi_total'] = 0
                product['doi_fba'] = 0
        
            product['formula'] = ''  # Keep blank for now as requested
            products.append(product)
        
        return {
            'products': products,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'total_pages': total_pages
            }
        }
        
    finally:
        cur.close()
        conn.close()


def get_ads_chart_data(asin, days=30):
    """
    Get daily ads chart data for a specific ASIN
    Returns time series + summary metrics with prior period comparison
    Blue line: Total Sales, Orange line: TACOS
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Calculate date ranges
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        prior_start = start_date - timedelta(days=days)
        prior_end = start_date - timedelta(days=1)
        
        # Get daily time series for current period - ALL AD METRICS
        cursor.execute("""
            SELECT 
                date,
                COALESCE(SUM(sales_amount), 0) as total_sales,
                COALESCE(SUM(ad_spend), 0) as ad_spend,
                COALESCE(SUM(ad_orders), 0) as ad_units,
                COALESCE(SUM(ad_sales), 0) as ad_sales,
                COALESCE(SUM(ad_clicks), 0) as ad_clicks,
                COALESCE(SUM(ad_impressions), 0) as ad_impressions,
                CASE 
                    WHEN SUM(sales_amount) > 0 
                    THEN (SUM(ad_spend) / SUM(sales_amount)) * 100 
                    ELSE 0 
                END as tacos,
                CASE 
                    WHEN SUM(ad_sales) > 0 
                    THEN (SUM(ad_spend) / SUM(ad_sales)) * 100 
                    ELSE 0 
                END as acos,
                CASE 
                    WHEN SUM(ad_clicks) > 0 
                    THEN SUM(ad_spend) / SUM(ad_clicks)
                    ELSE 0 
                END as cpc
            FROM daily_product_metrics
            WHERE asin = %s 
                AND date >= %s 
                AND date <= %s
                AND date IS NOT NULL
            GROUP BY date
            ORDER BY date ASC
        """, (asin, start_date, end_date))
        
        daily_data = cursor.fetchall()
        
        # Get current period totals
        cursor.execute("""
            SELECT 
                COALESCE(SUM(ad_orders), 0) as total_ad_units,
                COALESCE(SUM(ad_spend), 0) as total_ad_spend,
                COALESCE(SUM(ad_sales), 0) as total_ad_sales,
                COALESCE(SUM(ad_clicks), 0) as total_ad_clicks,
                COALESCE(SUM(ad_impressions), 0) as total_impressions,
                COALESCE(SUM(sales_amount), 0) as total_sales
            FROM daily_product_metrics
            WHERE asin = %s 
                AND date >= %s 
                AND date <= %s
                AND date IS NOT NULL
        """, (asin, start_date, end_date))
        
        current = cursor.fetchone()
        
        # Get prior period totals for comparison
        cursor.execute("""
            SELECT 
                COALESCE(SUM(ad_orders), 0) as total_ad_units,
                COALESCE(SUM(ad_spend), 0) as total_ad_spend,
                COALESCE(SUM(ad_sales), 0) as total_ad_sales,
                COALESCE(SUM(ad_clicks), 0) as total_ad_clicks,
                COALESCE(SUM(ad_impressions), 0) as total_impressions,
                COALESCE(SUM(sales_amount), 0) as total_sales
            FROM daily_product_metrics
            WHERE asin = %s 
                AND date >= %s 
                AND date <= %s
                AND date IS NOT NULL
        """, (asin, prior_start, prior_end))
        
        prior = cursor.fetchone()
        
        # Calculate metrics
        def calc_change(current_val, prior_val):
            if prior_val and prior_val > 0:
                return round(((float(current_val) - float(prior_val)) / float(prior_val)) * 100, 1)
            return 0
        
        current_tacos = (float(current['total_ad_spend']) / float(current['total_sales'])) * 100 if float(current['total_sales']) > 0 else 0
        prior_tacos = (float(prior['total_ad_spend']) / float(prior['total_sales'])) * 100 if float(prior['total_sales']) > 0 else 0
        
        current_acos = (float(current['total_ad_spend']) / float(current['total_ad_sales'])) * 100 if float(current['total_ad_sales']) > 0 else 0
        prior_acos = (float(prior['total_ad_spend']) / float(prior['total_ad_sales'])) * 100 if float(prior['total_ad_sales']) > 0 else 0
        
        current_cpc = float(current['total_ad_spend']) / float(current['total_ad_clicks']) if float(current['total_ad_clicks']) > 0 else 0
        prior_cpc = float(prior['total_ad_spend']) / float(prior['total_ad_clicks']) if float(prior['total_ad_clicks']) > 0 else 0
        
        total_sales_change = calc_change(current['total_sales'], prior['total_sales'])
        ad_sales_change = calc_change(current['total_ad_sales'], prior['total_ad_sales'])
        ad_units_change = calc_change(current['total_ad_units'], prior['total_ad_units'])
        ad_spend_change = calc_change(current['total_ad_spend'], prior['total_ad_spend'])
        ad_clicks_change = calc_change(current['total_ad_clicks'], prior['total_ad_clicks'])
        ad_impressions_change = calc_change(current['total_impressions'], prior['total_impressions'])
        tacos_change = calc_change(current_tacos, prior_tacos)
        acos_change = calc_change(current_acos, prior_acos)
        cpc_change = calc_change(current_cpc, prior_cpc)
        
        return {
            'asin': asin,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'chart_data': [
                {
                    'date': row['date'].isoformat() if isinstance(row['date'], date) else str(row['date']),
                    'total_sales': float(row['total_sales']),
                    'ad_sales': float(row['ad_sales']),
                    'ad_units': float(row['ad_units']),
                    'ad_spend': float(row['ad_spend']),
                    'ad_clicks': float(row['ad_clicks']),
                    'ad_impressions': float(row['ad_impressions']),
                    'tacos': round(float(row['tacos']), 2),
                    'acos': round(float(row['acos']), 2),
                    'cpc': round(float(row['cpc']), 2)
                }
                for row in daily_data
            ],
            'summary': {
                'total_sales': {
                    'current': float(current['total_sales']),
                    'prior': float(prior['total_sales']),
                    'change_percent': total_sales_change
                },
                'ad_sales': {
                    'current': float(current['total_ad_sales']),
                    'prior': float(prior['total_ad_sales']),
                    'change_percent': ad_sales_change
                },
                'ad_units': {
                    'current': float(current['total_ad_units']),
                    'prior': float(prior['total_ad_units']),
                    'change_percent': ad_units_change
                },
                'ad_spend': {
                    'current': float(current['total_ad_spend']),
                    'prior': float(prior['total_ad_spend']),
                    'change_percent': ad_spend_change
                },
                'ad_clicks': {
                    'current': float(current['total_ad_clicks']),
                    'prior': float(prior['total_ad_clicks']),
                    'change_percent': ad_clicks_change
                },
                'ad_impressions': {
                    'current': float(current['total_impressions']),
                    'prior': float(prior['total_impressions']),
                    'change_percent': ad_impressions_change
                },
                'tacos': {
                    'current': round(current_tacos, 2),
                    'prior': round(prior_tacos, 2),
                    'change_percent': tacos_change
                },
                'acos': {
                    'current': round(current_acos, 2),
                    'prior': round(prior_acos, 2),
                    'change_percent': acos_change
                },
                'cpc': {
                    'current': round(current_cpc, 2),
                    'prior': round(prior_cpc, 2),
                    'change_percent': cpc_change
                }
            }
        }
        
    finally:
        cursor.close()
        conn.close()


def get_sales_chart_data(asin, days=30):
    """
    Get daily sales chart data for a specific ASIN with ALL metrics
    Returns time series + summary metrics with prior period comparison
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Calculate date ranges
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        prior_start = start_date - timedelta(days=days)
        prior_end = start_date - timedelta(days=1)
        
        # Get daily time series for current period - ALL METRICS
        cursor.execute("""
            SELECT 
                date,
                COALESCE(SUM(units_sold), 0) as units_sold,
                COALESCE(SUM(sales_amount), 0) as sales,
                COALESCE(SUM(sessions), 0) as sessions,
                COALESCE(AVG(conversion_rate), 0) as conversion_rate,
                COALESCE(SUM(sales_amount) / NULLIF(SUM(units_sold), 0), 0) as price
            FROM daily_product_metrics
            WHERE asin = %s 
                AND date >= %s 
                AND date <= %s
                AND date IS NOT NULL
            GROUP BY date
            ORDER BY date ASC
        """, (asin, start_date, end_date))
        
        daily_data = cursor.fetchall()
        
        # Get current period totals
        cursor.execute("""
            SELECT 
                COALESCE(SUM(units_sold), 0) as total_units,
                COALESCE(SUM(sales_amount), 0) as total_sales,
                COALESCE(SUM(sessions), 0) as total_sessions,
                COALESCE(AVG(conversion_rate), 0) as avg_conversion_rate,
                COALESCE(SUM(sales_amount) / NULLIF(SUM(units_sold), 0), 0) as avg_price,
                COALESCE((SUM(ad_sales) / NULLIF(SUM(sales_amount), 0)) * 100, 0) as ad_sales_percent
            FROM daily_product_metrics
            WHERE asin = %s 
                AND date >= %s 
                AND date <= %s
                AND date IS NOT NULL
        """, (asin, start_date, end_date))
        
        current = cursor.fetchone()
        
        # Get prior period totals for comparison
        cursor.execute("""
            SELECT 
                COALESCE(SUM(units_sold), 0) as total_units,
                COALESCE(SUM(sales_amount), 0) as total_sales,
                COALESCE(SUM(sessions), 0) as total_sessions,
                COALESCE(AVG(conversion_rate), 0) as avg_conversion_rate,
                COALESCE(SUM(sales_amount) / NULLIF(SUM(units_sold), 0), 0) as avg_price,
                COALESCE((SUM(ad_sales) / NULLIF(SUM(sales_amount), 0)) * 100, 0) as ad_sales_percent
            FROM daily_product_metrics
            WHERE asin = %s 
                AND date >= %s 
                AND date <= %s
                AND date IS NOT NULL
        """, (asin, prior_start, prior_end))
        
        prior = cursor.fetchone()
        
        # Calculate percentage changes
        def calc_change(current_val, prior_val):
            if prior_val and prior_val > 0:
                return round(((float(current_val) - float(prior_val)) / float(prior_val)) * 100, 1)
            return 0
        
        units_change = calc_change(current['total_units'], prior['total_units'])
        sales_change = calc_change(current['total_sales'], prior['total_sales'])
        sessions_change = calc_change(current['total_sessions'], prior['total_sessions'])
        conversion_change = calc_change(current['avg_conversion_rate'], prior['avg_conversion_rate'])
        price_change = calc_change(current['avg_price'], prior['avg_price'])
        ad_sales_percent_change = calc_change(current['ad_sales_percent'], prior['ad_sales_percent'])
        
        return {
            'asin': asin,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'chart_data': [
                {
                    'date': row['date'].isoformat() if isinstance(row['date'], date) else str(row['date']),
                    'units_sold': float(row['units_sold']),
                    'sales': float(row['sales']),
                    'sessions': float(row['sessions']),
                    'conversion_rate': round(float(row['conversion_rate']), 2),
                    'price': round(float(row['price']), 2)
                }
                for row in daily_data
            ],
            'summary': {
                'units_sold': {
                    'current': float(current['total_units']),
                    'prior': float(prior['total_units']),
                    'change_percent': units_change
                },
                'sales': {
                    'current': float(current['total_sales']),
                    'prior': float(prior['total_sales']),
                    'change_percent': sales_change
                },
                'sessions': {
                    'current': float(current['total_sessions']),
                    'prior': float(prior['total_sessions']),
                    'change_percent': sessions_change
                },
                'conversion_rate': {
                    'current': round(float(current['avg_conversion_rate']), 2),
                    'prior': round(float(prior['avg_conversion_rate']), 2),
                    'change_percent': conversion_change
                },
                'price': {
                    'current': round(float(current['avg_price']), 2),
                    'prior': round(float(prior['avg_price']), 2),
                    'change_percent': price_change
                },
                'ad_sales_percent': {
                    'current': round(float(current['ad_sales_percent']), 2),
                    'prior': round(float(prior['ad_sales_percent']), 2),
                    'change_percent': ad_sales_percent_change
                }
            }
        }
        
    finally:
        cursor.close()
        conn.close()


def get_weekly_metrics(asin, year=None):
    """
    Get weekly metrics for ASIN organized by Gregorian calendar weeks
    Returns data from week 1 to the current/latest week of the specified year
    """
    if year is None:
        year = datetime.now().year
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get the first day and last day of the year
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        
        # Get current date to limit to "up to current week"
        today = date.today()
        if year == today.year:
            end_date = today
        else:
            end_date = year_end
        
        # Query to get weekly aggregated data
        # We'll use PostgreSQL's date_trunc to group by week (ISO week starting Monday)
        cursor.execute("""
            WITH weekly_data AS (
                SELECT 
                    DATE_TRUNC('week', date)::date as week_start,
                    EXTRACT(WEEK FROM date) as week_number,
                    
                    -- Sales metrics
                    COALESCE(SUM(sales_amount), 0) as total_sales,
                    COALESCE(SUM(units_sold), 0) as units_sold,
                    CASE 
                        WHEN SUM(units_sold) > 0 
                        THEN (SUM(sales_amount)::float / SUM(units_sold)::float)
                        ELSE 0 
                    END as avg_price,
                    
                    -- Traffic metrics
                    COALESCE(SUM(sessions), 0) as sessions,
                    CASE 
                        WHEN SUM(sessions) > 0 
                        THEN (SUM(units_sold)::float / SUM(sessions)::float * 100)
                        ELSE 0 
                    END as conversion_rate,
                    
                    -- Ad metrics
                    COALESCE(SUM(ad_spend), 0) as ad_spend,
                    COALESCE(SUM(ad_sales), 0) as ad_sales,
                    COALESCE(SUM(ad_orders), 0) as ad_orders,
                    COALESCE(SUM(ad_impressions), 0) as ad_impressions,
                    COALESCE(SUM(ad_clicks), 0) as ad_clicks,
                    
                    -- Calculated metrics
                    CASE 
                        WHEN SUM(sales_amount) > 0 
                        THEN (SUM(ad_spend)::float / SUM(sales_amount)::float * 100)
                        ELSE 0 
                    END as tacos,
                    
                    CASE 
                        WHEN SUM(ad_sales) > 0 
                        THEN (SUM(ad_spend)::float / SUM(ad_sales)::float * 100)
                        ELSE 0 
                    END as acos,
                    
                    CASE 
                        WHEN SUM(ad_clicks) > 0 
                        THEN (SUM(ad_spend)::float / SUM(ad_clicks)::float)
                        ELSE 0 
                    END as cpc
                    
                FROM daily_product_metrics
                WHERE asin = %s
                  AND date >= %s
                  AND date <= %s
                GROUP BY DATE_TRUNC('week', date), EXTRACT(WEEK FROM date)
                ORDER BY week_start
            )
            SELECT * FROM weekly_data
        """, (asin, year_start, end_date))
        
        rows = cursor.fetchall()
        
        if not rows:
            return {
                'error': 'No data found',
                'message': f'No metrics found for ASIN {asin} in year {year}'
            }
        
        # Format the response
        weekly_data = []
        for row in rows:
            weekly_data.append({
                'week_number': int(row['week_number']),
                'week_start': row['week_start'].isoformat() if row['week_start'] else None,
                'total_sales': round(float(row['total_sales']), 2) if row['total_sales'] else 0,
                'units_sold': int(row['units_sold']) if row['units_sold'] else 0,
                'avg_price': round(float(row['avg_price']), 2) if row['avg_price'] else 0,
                'sessions': int(row['sessions']) if row['sessions'] else 0,
                'conversion_rate': round(float(row['conversion_rate']), 2) if row['conversion_rate'] else 0,
                'ad_spend': round(float(row['ad_spend']), 2) if row['ad_spend'] else 0,
                'ad_sales': round(float(row['ad_sales']), 2) if row['ad_sales'] else 0,
                'ad_orders': int(row['ad_orders']) if row['ad_orders'] else 0,
                'ad_impressions': int(row['ad_impressions']) if row['ad_impressions'] else 0,
                'ad_clicks': int(row['ad_clicks']) if row['ad_clicks'] else 0,
                'tacos': round(float(row['tacos']), 2) if row['tacos'] else 0,
                'acos': round(float(row['acos']), 2) if row['acos'] else 0,
                'cpc': round(float(row['cpc']), 2) if row['cpc'] else 0
            })
        
        # Get product info
        cursor.execute("""
            SELECT asin, product_name, size, brand
            FROM products
            WHERE asin = %s
            LIMIT 1
        """, (asin,))
        
        product_row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return {
            'success': True,
            'year': year,
            'asin': asin,
            'product': {
                'asin': asin,
                'name': product_row['product_name'] if product_row else None,
                'size': product_row['size'] if product_row else None,
                'brand': product_row['brand'] if product_row else None
            },
            'weeks': weekly_data,
            'total_weeks': len(weekly_data),
            'summary': {
                'total_sales': round(sum(w['total_sales'] for w in weekly_data), 2),
                'total_units': sum(w['units_sold'] for w in weekly_data),
                'total_sessions': sum(w['sessions'] for w in weekly_data),
                'total_ad_spend': round(sum(w['ad_spend'] for w in weekly_data), 2),
                'total_ad_impressions': sum(w['ad_impressions'] for w in weekly_data),
                'avg_conversion_rate': round(sum(w['conversion_rate'] for w in weekly_data) / len(weekly_data), 2) if weekly_data else 0,
                'avg_tacos': round(sum(w['tacos'] for w in weekly_data) / len(weekly_data), 2) if weekly_data else 0
            }
        }
        
    except Exception as e:
        cursor.close()
        conn.close()
        import traceback
        return {
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def lambda_handler(event, context):
    """
    Main Lambda handler
    
    Routes:
        GET /products - List all products
        GET /planning - Get planning table for all products
        GET /product/{asin} - Get product details + inventory
        GET /forecast/{asin} - Get forecast days calculation
        GET /chart/{asin} - Get chart data
        GET /sales-chart/{asin} - Get daily sales chart data
        GET /ads-chart/{asin} - Get daily ads chart data
        GET /weekly-metrics/{asin} - Get weekly metrics by Gregorian calendar
        OPTIONS /* - CORS preflight
    """
    
    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {'message': 'OK'})
    
    # Parse path and method
    # Handle both REST API and HTTP API formats
    path = event.get('path', '') or event.get('rawPath', '')
    method = event.get('httpMethod', '') or event.get('requestContext', {}).get('http', {}).get('method', 'GET')
    path_params = event.get('pathParameters') or {}
    query_params = event.get('queryStringParameters') or {}
    
    # Debug logging
    print(f"Event: {json.dumps(event)}")
    print(f"Path: {path}, Method: {method}, PathParams: {path_params}")
    
    # Helper function to extract ASIN from path or path params
    def get_asin_from_path(prefix):
        # Try path parameters first (API Gateway configured)
        asin = path_params.get('asin')
        if asin:
            return asin
        
        # Fallback: parse from path directly
        if path.startswith(prefix):
            parts = path[len(prefix):].split('/')
            if parts and parts[0]:
                return parts[0]
        
        return None
    
    try:
        # Route: GET /products
        if path == '/products' and method == 'GET':
            data = get_all_products()
            return cors_response(200, data)
        
        # Route: GET /planning
        if path == '/planning' and method == 'GET':
            page = int(query_params.get('page', 1))
            limit = int(query_params.get('limit', 50))
            data = get_planning_table(page, limit)
            return cors_response(200, data)
        
        # Route: GET /product/{asin}
        if path.startswith('/product/') and method == 'GET':
            asin = get_asin_from_path('/product/')
            if not asin:
                return cors_response(400, {'error': 'ASIN required'})
            
            data = get_product_inventory(asin)
            if 'error' in data:
                return cors_response(404, data)
            return cors_response(200, data)
        
        # Route: GET /metrics/{asin}
        if path.startswith('/metrics/') and method == 'GET':
            asin = get_asin_from_path('/metrics/')
            if not asin:
                return cors_response(400, {'error': 'ASIN required'})
            
            days = int(query_params.get('days', 30))
            data = get_product_metrics(asin, days)
            
            if 'error' in data:
                return cors_response(404, data)
            return cors_response(200, data)
        
        # Route: GET /forecast/{asin}
        if path.startswith('/forecast/') and method == 'GET':
            asin = get_asin_from_path('/forecast/')
            if not asin:
                return cors_response(400, {'error': 'ASIN required'})
            
            settings = {
                'doi_goal': int(query_params.get('doi_goal', 120)),
                'lead_time': int(query_params.get('lead_time', 37))
            }
            
            data = calculate_forecast_days(asin, settings)
            return cors_response(200, data)
        
        # Route: GET /chart/{asin}
        if path.startswith('/chart/') and method == 'GET':
            asin = get_asin_from_path('/chart/')
            if not asin:
                return cors_response(400, {'error': 'ASIN required'})
            
            weeks_ahead = int(query_params.get('weeks', 52))
            
            # Parse velocity weights (support both decimal 0-1 and percentage 0-100)
            sales_vel_weight = query_params.get('sales_velocity_weight')
            sv_vel_weight = query_params.get('sv_velocity_weight')
            
            # Convert percentage to decimal if needed (e.g., 25 -> 0.25)
            if sales_vel_weight is not None:
                sales_vel_weight = float(sales_vel_weight)
                if sales_vel_weight > 1:
                    sales_vel_weight = sales_vel_weight / 100.0
            
            if sv_vel_weight is not None:
                sv_vel_weight = float(sv_vel_weight)
                if sv_vel_weight > 1:
                    sv_vel_weight = sv_vel_weight / 100.0
            
            data = get_forecast_chart_data(
                asin, 
                weeks_ahead, 
                sales_velocity_weight=sales_vel_weight,
                sv_velocity_weight=sv_vel_weight
            )
            
            if 'error' in data:
                return cors_response(404, data)
            return cors_response(200, data)
        
        # Route: GET /sales-chart/{asin}
        if path.startswith('/sales-chart/') and method == 'GET':
            asin = get_asin_from_path('/sales-chart/')
            if not asin:
                return cors_response(400, {'error': 'ASIN required'})
            
            days = int(query_params.get('days', 30))
            
            # Validate days range
            if days < 7 or days > 365:
                return cors_response(400, {
                    'error': 'Invalid days parameter',
                    'message': 'Days must be between 7 and 365',
                    'received': days
                })
            
            data = get_sales_chart_data(asin, days)
            
            if 'error' in data:
                return cors_response(404, data)
            return cors_response(200, data)
        
        # Route: GET /ads-chart/{asin}
        if path.startswith('/ads-chart/') and method == 'GET':
            asin = get_asin_from_path('/ads-chart/')
            if not asin:
                return cors_response(400, {'error': 'ASIN required'})
            
            days = int(query_params.get('days', 30))
            
            # Validate days range
            if days < 7 or days > 365:
                return cors_response(400, {
                    'error': 'Invalid days parameter',
                    'message': 'Days must be between 7 and 365',
                    'received': days
                })
            
            data = get_ads_chart_data(asin, days)
            
            if 'error' in data:
                return cors_response(404, data)
            return cors_response(200, data)
        
        # Route: GET /weekly-metrics/{asin}
        if path.startswith('/weekly-metrics/') and method == 'GET':
            asin = get_asin_from_path('/weekly-metrics/')
            if not asin:
                return cors_response(400, {'error': 'ASIN required'})
            
            year = int(query_params.get('year', datetime.now().year))
            
            data = get_weekly_metrics(asin, year)
            
            if 'error' in data:
                return cors_response(404, data)
            return cors_response(200, data)
        
        # Route not found
        return cors_response(404, {
            'error': 'Route not found',
            'path': path,
            'method': method,
            'available_routes': [
                '/products',
                '/planning',
                '/product/{asin}',
                '/metrics/{asin}',
                '/forecast/{asin}',
                '/chart/{asin}',
                '/sales-chart/{asin}',
                '/ads-chart/{asin}',
                '/weekly-metrics/{asin}'
            ]
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return cors_response(500, {'error': str(e)})

