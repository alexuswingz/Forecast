# Frontend Integration Guide - Adjustable Velocity Sliders

## Overview
The `/chart/{asin}` endpoint now supports real-time forecast adjustments via adjustable velocity weights. Users can change these settings and see the forecast update instantly.

## Implementation

### 1. State Management (React Example)

```javascript
const [velocitySettings, setVelocitySettings] = useState({
  salesVelocityWeight: 25,  // Default 25%
  svVelocityWeight: 15       // Default 15%
});
const [chartData, setChartData] = useState(null);
const [isLoading, setIsLoading] = useState(false);
```

### 2. Fetch Function

```javascript
const fetchChartData = async (asin, settings) => {
  setIsLoading(true);
  try {
    const response = await fetch(
      `${API_BASE_URL}/chart/${asin}?` +
      `weeks=52&` +
      `sales_velocity_weight=${settings.salesVelocityWeight}&` +
      `sv_velocity_weight=${settings.svVelocityWeight}`
    );
    const data = await response.json();
    setChartData(data);
  } catch (error) {
    console.error('Failed to fetch chart data:', error);
  } finally {
    setIsLoading(false);
  }
};
```

### 3. UI Components

```jsx
<div className="adjustment-controls">
  <h3>Adjustment Weights</h3>
  
  {/* Sales Velocity Slider */}
  <div className="slider-group">
    <label>
      Sales Velocity
      <input
        type="number"
        value={velocitySettings.salesVelocityWeight}
        min="0"
        max="100"
        readOnly
      />
      <span>%</span>
    </label>
    <input
      type="range"
      min="0"
      max="100"
      step="1"
      value={velocitySettings.salesVelocityWeight}
      onChange={(e) =>
        setVelocitySettings({
          ...velocitySettings,
          salesVelocityWeight: parseInt(e.target.value)
        })
      }
      className="slider"
    />
  </div>
  
  {/* Search Volume Velocity Slider */}
  <div className="slider-group">
    <label>
      Search Volume Velocity
      <input
        type="number"
        value={velocitySettings.svVelocityWeight}
        min="0"
        max="100"
        readOnly
      />
      <span>%</span>
    </label>
    <input
      type="range"
      min="0"
      max="100"
      step="1"
      value={velocitySettings.svVelocityWeight}
      onChange={(e) =>
        setVelocitySettings({
          ...velocitySettings,
          svVelocityWeight: parseInt(e.target.value)
        })
      }
      className="slider"
    />
  </div>
  
  {/* Action Buttons */}
  <div className="button-group">
    <button
      onClick={() => {
        // Reset to defaults
        setVelocitySettings({
          salesVelocityWeight: 25,
          svVelocityWeight: 15
        });
      }}
      className="btn-secondary"
    >
      Cancel
    </button>
    <button
      onClick={() => fetchChartData(currentAsin, velocitySettings)}
      disabled={isLoading}
      className="btn-primary"
    >
      {isLoading ? 'Applying...' : 'Apply'}
    </button>
  </div>
</div>
```

### 4. Display Velocity Adjustments

```jsx
{chartData?.metadata && (
  <div className="velocity-info">
    <div className="info-item">
      <span className="label">Sales Velocity Adjustment:</span>
      <span className="value">
        {(chartData.metadata.sales_velocity_adj * 100).toFixed(2)}%
      </span>
    </div>
    <div className="info-item">
      <span className="label">Search Volume Velocity Adjustment:</span>
      <span className="value">
        {(chartData.metadata.sv_velocity_adj * 100).toFixed(2)}%
      </span>
    </div>
    <div className="info-item">
      <span className="label">Total Adjustment:</span>
      <span className="value total">
        {(chartData.metadata.total_adjustment * 100).toFixed(2)}%
      </span>
    </div>
  </div>
)}
```

### 5. Example CSS

```css
.adjustment-controls {
  background: #1a1d29;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.slider-group {
  margin-bottom: 20px;
}

.slider-group label {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  color: #fff;
}

.slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(
    to right,
    #0066ff 0%,
    #0066ff var(--slider-progress, 25%),
    #2a2d3a var(--slider-progress, 25%),
    #2a2d3a 100%
  );
  outline: none;
  -webkit-appearance: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.button-group {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.btn-primary {
  background: #0066ff;
  color: white;
  padding: 10px 24px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #2a2d3a;
  color: white;
  padding: 10px 24px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}

.velocity-info {
  background: #1a1d29;
  padding: 16px;
  border-radius: 8px;
  margin-top: 20px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  color: #fff;
}

.info-item .label {
  color: #8b92a7;
}

.info-item .value {
  font-weight: 600;
}

.info-item .value.total {
  color: #0066ff;
  font-size: 1.1em;
}
```

## API Response Structure

### Request
```
GET /chart/B0BRTK1P8Z?weeks=52&sales_velocity_weight=30&sv_velocity_weight=20
```

### Response
```json
{
  "historical": [
    {
      "week_end": "2024-11-17",
      "units_sold": 182.0,
      "units_smooth": 560.7
    }
  ],
  "forecast": [
    {
      "week_end": "2025-11-23",
      "forecast_base": 774.0,
      "forecast_adjusted": 850.2
    }
  ],
  "metadata": {
    "sales_velocity_adj": 0.0856,
    "sv_velocity_adj": 0.0421,
    "total_adjustment": 0.1319,
    "sales_velocity_weight": 0.3,
    "sv_velocity_weight": 0.2,
    "forecast_weeks": 52,
    "avg_weekly_sales": 1420.5
  }
}
```

## Key Features

1. **Real-Time Updates**: Forecast recalculates instantly when "Apply" is clicked
2. **Excel-Accurate**: Uses the same formulas as 1000 Bananas AUTOFORECAST V1.1.xlsx
3. **Flexible Input**: Accepts both percentage (0-100) and decimal (0-1) formats
4. **Individual Breakdowns**: See how each velocity type contributes to the total adjustment
5. **Reset Capability**: "Cancel" button resets to default values (25%, 15%)

## Performance Notes

- Calculation time: ~2-3 seconds (on-the-fly smoothing + velocity calculations)
- No caching: Each request generates fresh forecast with current weights
- Search volume velocity requires at least 24 weeks of traffic data
- If search volume data is unavailable, `sv_velocity_adj` will be 0.0

## Modal/Drawer Implementation

For the modal shown in the image, you would typically:
1. Display it when user clicks a "Settings" or "Adjust Forecast" button
2. Show current values with sliders
3. "Cancel" closes modal without changes
4. "Apply" fetches new data and closes modal
5. Chart updates with new forecast curve

```jsx
const [isSettingsOpen, setIsSettingsOpen] = useState(false);

// Button to open settings
<button onClick={() => setIsSettingsOpen(true)}>
  Adjust Forecast Settings
</button>

// Modal/Drawer component
{isSettingsOpen && (
  <Modal onClose={() => setIsSettingsOpen(false)}>
    <AdjustmentControls
      settings={velocitySettings}
      onSettingsChange={setVelocitySettings}
      onApply={(newSettings) => {
        fetchChartData(currentAsin, newSettings);
        setIsSettingsOpen(false);
      }}
      onCancel={() => {
        setVelocitySettings({ salesVelocityWeight: 25, svVelocityWeight: 15 });
        setIsSettingsOpen(false);
      }}
    />
  </Modal>
)}
```

## Testing

Test with different weight combinations:
- Default (25%, 15%) - baseline forecast
- Conservative (15%, 10%) - lower adjustment
- Aggressive (40%, 25%) - higher adjustment
- Sales-only (50%, 0%) - ignore search volume
- Balanced (25%, 25%) - equal weighting


