# Clickable Metrics Guide - Interactive Chart Selection

## Overview
Both `/sales-chart/{asin}` and `/ads-chart/{asin}` endpoints now return ALL available metrics in the daily `chart_data` array. Users can click metric cards to show/hide specific metrics on the graph dynamically.

---

## Sales Tab - Available Metrics

### Returned Data Structure
```json
{
  "asin": "B0BRTK1P8Z",
  "date_range": {
    "start": "2025-10-18",
    "end": "2025-11-16",
    "days": 30
  },
  "chart_data": [
    {
      "date": "2025-10-18",
      "units_sold": 160.0,
      "sales": 1915.20,
      "sessions": 450.0,
      "conversion_rate": 1.49,
      "price": 11.13,
      "profit": 892.45,
      "profit_margin": 46.6,
      "profit_total": 402.88
    }
  ],
  "summary": {
    "units_sold": {
      "current": 252,
      "prior": 769,
      "change_percent": -65.2
    },
    "sales": {
      "current": 2806.26,
      "prior": 8298.12,
      "change_percent": -63.9
    },
    "sessions": {
      "current": 2084,
      "prior": 2943,
      "change_percent": -29.2
    },
    "conversion_rate": {
      "current": 1.49,
      "prior": 1.01,
      "change_percent": 101.4
    },
    "price": {
      "current": 11.13,
      "prior": 10.79,
      "change_percent": 3.8
    },
    "profit": {
      "current": 1309.67,
      "prior": 3871.22,
      "change_percent": -66.2
    },
    "profit_margin": {
      "current": 76.3,
      "prior": 74.1,
      "change_percent": 4.2
    },
    "profit_total": {
      "current": 820.25,
      "prior": 2981.80,
      "change_percent": -63.1
    },
    "organic_sales_percent": {
      "current": 62.0,
      "prior": 65.3
    }
  }
}
```

### Sales Metrics Configuration
```javascript
const SALES_METRICS = [
  {
    id: 'units_sold',
    label: 'Units Sold',
    color: '#4169E1',      // Blue
    valueKey: 'units_sold',
    formatType: 'number',
    defaultVisible: true
  },
  {
    id: 'sales',
    label: 'Sales',
    color: '#FF8C00',      // Orange
    valueKey: 'sales',
    formatType: 'currency',
    defaultVisible: true
  },
  {
    id: 'sessions',
    label: 'Sessions',
    color: '#32CD32',      // Green
    valueKey: 'sessions',
    formatType: 'number',
    defaultVisible: false
  },
  {
    id: 'conversion_rate',
    label: 'Conversion Rate',
    color: '#9370DB',      // Purple
    valueKey: 'conversion_rate',
    formatType: 'percentage',
    defaultVisible: false
  },
  {
    id: 'price',
    label: 'Price',
    color: '#FFD700',      // Gold
    valueKey: 'price',
    formatType: 'currency',
    defaultVisible: false
  },
  {
    id: 'ad_sales_percent',
    label: 'Ad Sales %',
    color: '#20B2AA',      // Light Sea Green
    valueKey: 'ad_sales_percent',
    formatType: 'percentage',
    defaultVisible: false
  }
];
```

---

## Ads Tab - Available Metrics

### Returned Data Structure
```json
{
  "asin": "B0BRTK1P8Z",
  "date_range": {
    "start": "2025-10-18",
    "end": "2025-11-16",
    "days": 30
  },
  "chart_data": [
    {
      "date": "2025-10-18",
      "total_sales": 1915.20,
      "ad_sales": 890.42,
      "ad_units": 78,
      "ad_spend": 489.42,
      "ad_clicks": 365,
      "ad_impressions": 12450,
      "tacos": 17.4,
      "acos": 54.9,
      "cpc": 1.34
    }
  ],
  "summary": {
    "total_sales": {
      "current": 2806.26,
      "prior": 8298.12,
      "change_percent": -63.9
    },
    "ad_sales": {
      "current": 1560.80,
      "prior": 4892.33,
      "change_percent": -68.1
    },
    "ad_units": {
      "current": 140,
      "prior": 441,
      "change_percent": -68.3
    },
    "ad_spend": {
      "current": 489.42,
      "prior": 1423.55,
      "change_percent": -65.6
    },
    "ad_clicks": {
      "current": 365,
      "prior": 1062,
      "change_percent": -65.6
    },
    "ad_impressions": {
      "current": 45200,
      "prior": 128400,
      "change_percent": -64.8
    },
    "tacos": {
      "current": 17.4,
      "prior": 17.2,
      "change_percent": 1.2
    },
    "acos": {
      "current": 31.4,
      "prior": 29.1,
      "change_percent": 7.9
    },
    "cpc": {
      "current": 1.34,
      "prior": 1.34,
      "change_percent": 0.0
    }
  }
}
```

### Ads Metrics Configuration
```javascript
const ADS_METRICS = [
  {
    id: 'total_sales',
    label: 'Total Sales',
    color: '#4169E1',      // Blue
    valueKey: 'total_sales',
    formatType: 'currency',
    defaultVisible: true
  },
  {
    id: 'tacos',
    label: 'TACOS',
    color: '#FF8C00',      // Orange
    valueKey: 'tacos',
    formatType: 'percentage',
    defaultVisible: true
  },
  {
    id: 'ad_spend',
    label: 'Ad Spend',
    color: '#DC143C',      // Crimson
    valueKey: 'ad_spend',
    formatType: 'currency',
    defaultVisible: false
  },
  {
    id: 'ad_sales',
    label: 'Ad Sales',
    color: '#32CD32',      // Green
    valueKey: 'ad_sales',
    formatType: 'currency',
    defaultVisible: false
  },
  {
    id: 'ad_units',
    label: 'Ad Units',
    color: '#9370DB',      // Purple
    valueKey: 'ad_units',
    formatType: 'number',
    defaultVisible: false
  },
  {
    id: 'acos',
    label: 'ACOS',
    color: '#FF69B4',      // Hot Pink
    valueKey: 'acos',
    formatType: 'percentage',
    defaultVisible: false
  },
  {
    id: 'cpc',
    label: 'Ad CPC',
    color: '#FFD700',      // Gold
    valueKey: 'cpc',
    formatType: 'currency',
    defaultVisible: false
  },
  {
    id: 'ad_clicks',
    label: 'Ad Clicks',
    color: '#20B2AA',      // Light Sea Green
    valueKey: 'ad_clicks',
    formatType: 'number',
    defaultVisible: false
  },
  {
    id: 'ad_impressions',
    label: 'Impressions',
    color: '#778899',      // Light Slate Gray
    valueKey: 'ad_impressions',
    formatType: 'number',
    defaultVisible: false
  }
];
```

---

## React Implementation Example

### 1. State Management
```javascript
import React, { useState, useEffect } from 'react';

const SalesTab = ({ asin }) => {
  const [chartData, setChartData] = useState(null);
  const [visibleMetrics, setVisibleMetrics] = useState(
    SALES_METRICS.filter(m => m.defaultVisible).map(m => m.id)
  );
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    fetchSalesData();
  }, [asin, days]);
  
  const fetchSalesData = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/sales-chart/${asin}?days=${days}`
      );
      const data = await response.json();
      setChartData(data);
    } catch (error) {
      console.error('Failed to fetch sales data:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const toggleMetric = (metricId) => {
    setVisibleMetrics(prev =>
      prev.includes(metricId)
        ? prev.filter(id => id !== metricId)
        : [...prev, metricId]
    );
  };
  
  // ... rest of component
};
```

### 2. Metric Cards (Clickable)
```jsx
<div className="metrics-grid">
  {SALES_METRICS.map(metric => {
    const summaryData = chartData?.summary?.[metric.id];
    const isVisible = visibleMetrics.includes(metric.id);
    
    return (
      <div
        key={metric.id}
        className={`metric-card ${isVisible ? 'active' : ''}`}
        onClick={() => toggleMetric(metric.id)}
        style={{
          borderColor: isVisible ? metric.color : 'transparent',
          cursor: 'pointer'
        }}
      >
        {/* Indicator dot */}
        <div
          className="metric-indicator"
          style={{
            backgroundColor: metric.color,
            opacity: isVisible ? 1 : 0.3
          }}
        />
        
        {/* Metric value */}
        <div className="metric-value">
          {formatValue(summaryData?.current, metric.formatType)}
        </div>
        
        {/* Metric label */}
        <div className="metric-label">{metric.label}</div>
        
        {/* Change percentage */}
        {summaryData?.change_percent !== undefined && (
          <div
            className={`metric-change ${
              summaryData.change_percent >= 0 ? 'positive' : 'negative'
            }`}
          >
            {summaryData.change_percent >= 0 ? '+' : ''}
            {summaryData.change_percent}%
          </div>
        )}
      </div>
    );
  })}
  
  {/* Add Metric Button */}
  <div className="metric-card add-metric-card">
    <div className="add-icon">+</div>
    <div className="metric-label">Add Metric</div>
  </div>
</div>
```

### 3. Chart Rendering (Using recharts)
```jsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const renderChart = () => {
  if (!chartData) return null;
  
  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData.chart_data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3a" />
        <XAxis
          dataKey="date"
          stroke="#8b92a7"
          tick={{ fill: '#8b92a7' }}
        />
        <YAxis stroke="#8b92a7" tick={{ fill: '#8b92a7' }} />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1a1d29',
            border: '1px solid #2a2d3a',
            borderRadius: '8px'
          }}
          labelStyle={{ color: '#fff' }}
        />
        <Legend
          wrapperStyle={{ color: '#8b92a7' }}
          onClick={(e) => toggleMetric(e.dataKey)}
        />
        
        {/* Render lines for visible metrics */}
        {SALES_METRICS.filter(m => visibleMetrics.includes(m.id)).map(metric => (
          <Line
            key={metric.id}
            type="monotone"
            dataKey={metric.valueKey}
            stroke={metric.color}
            strokeWidth={2}
            dot={false}
            name={metric.label}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
};
```

### 4. Format Helper Functions
```javascript
const formatValue = (value, formatType) => {
  if (value === null || value === undefined) return '-';
  
  switch (formatType) {
    case 'currency':
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
      }).format(value);
    
    case 'percentage':
      return `${value.toFixed(2)}%`;
    
    case 'number':
      return new Intl.NumberFormat('en-US').format(Math.round(value));
    
    default:
      return value.toString();
  }
};
```

---

## CSS Styling

```css
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  background: #1a1d29;
  border: 2px solid transparent;
  border-radius: 12px;
  padding: 20px;
  position: relative;
  transition: all 0.3s ease;
  cursor: pointer;
}

.metric-card:hover {
  background: #1f2330;
  transform: translateY(-2px);
}

.metric-card.active {
  border-color: currentColor;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.metric-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  position: absolute;
  top: 16px;
  right: 16px;
  transition: opacity 0.3s ease;
}

.metric-value {
  font-size: 32px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 8px;
}

.metric-label {
  font-size: 14px;
  color: #8b92a7;
  margin-bottom: 8px;
}

.metric-change {
  font-size: 14px;
  font-weight: 600;
}

.metric-change.positive {
  color: #32CD32;
}

.metric-change.negative {
  color: #FF4444;
}

.add-metric-card {
  border: 2px dashed #2a2d3a;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.add-icon {
  font-size: 36px;
  color: #8b92a7;
  margin-bottom: 8px;
}

/* Chart container */
.chart-container {
  background: #1a1d29;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
}
```

---

## User Experience Flow

1. **Default View**: Units Sold (blue) and Sales (orange) are shown by default
2. **Click to Add**: User clicks any metric card → that line appears on the graph
3. **Click to Remove**: User clicks an active (highlighted) metric card → that line disappears
4. **Visual Feedback**:
   - Active cards have colored border matching their line color
   - Color dot indicator shows opacity: 100% (active) vs 30% (inactive)
   - Hover effect on all cards
5. **Chart Legend**: Clicking legend items also toggles lines
6. **Add Metric Button**: Reserved for future custom metrics or additional data sources

---

## Testing Checklist

- [ ] Default metrics (Units Sold, Sales / Total Sales, TACOS) appear on load
- [ ] Clicking inactive metric adds its line to chart
- [ ] Clicking active metric removes its line from chart
- [ ] Border color matches line color for active metrics
- [ ] Color indicator dot changes opacity
- [ ] All metrics from API are rendered as cards
- [ ] Chart updates smoothly without flicker
- [ ] Legend click also toggles metrics
- [ ] Percentage changes display correctly (+ for positive, - for negative)
- [ ] Values format correctly (currency, percentage, number)
- [ ] Works on both Sales and Ads tabs
- [ ] Responsive on mobile/tablet

---

## Performance Notes

- All metrics are fetched in a single API call (no additional requests when toggling)
- Chart re-renders only when `visibleMetrics` state changes
- Use `React.memo` for metric cards to prevent unnecessary re-renders
- Chart library (recharts) handles animation automatically

---

## Future Enhancements

1. **Save Preferences**: Store user's preferred visible metrics in localStorage
2. **Metric Comparison**: Allow selecting 2-3 metrics for side-by-side comparison
3. **Custom Metrics**: Add calculated metrics (e.g., AOV = Sales / Units)
4. **Export Data**: Download chart data as CSV with selected metrics
5. **Annotations**: Add notes to specific dates on the chart

