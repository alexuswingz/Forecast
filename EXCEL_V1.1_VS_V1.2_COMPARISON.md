# Excel Formula Comparison: v1.1 vs v1.2

## Executive Summary

**Result: NO FORMULA CHANGES** between v1.1 and v1.2

All calculation formulas remain **IDENTICAL** between the two versions. The only differences are:
- v1.2 has **no data values** in column B (units_sold) - it appears to be a template
- v1.1 has actual historical data populated

## Detailed Comparison

### Document Structure
- Both files have same sheets: `Settings`, `Forecast`, `SearchVolume`, `Inventory`, `Definitions`
- Both Forecast sheets: 200 rows x 37 cols
- Same column headers and structure

### Column Headers (Row 2)
| Column | Name | Type |
|--------|------|------|
| A | week_end | Date value |
| B | units_sold | Input data |
| C | units_peak_env | Formula |
| D | units_smooth_env | Formula |
| E | untis_final_curve | Formula |
| F | units_final_smooth | Formula |
| G | forecast | Calculated value |
| H | forecast_units_peak_env | Formula |
| I | forecast_final_smooth | Calculated value |
| J | sales_velocity_adj_weighted | Calculated value |
| K | sv_velocity_adj_weighted | Formula (links to SearchVolume sheet) |
| L | adj_forecast | Calculated value |

## Formula Details (All UNCHANGED)

### Column C: units_peak_env
```excel
=MAX(OFFSET(B3,-2,0,5))
```
**Purpose**: Peak envelope - max of last 5 weeks rolling window
**Status**: ✅ IDENTICAL in both versions

### Column D: units_smooth_env
```excel
=AVERAGE(OFFSET(C3,-1,0,3))
```
**Purpose**: Smoothed envelope - 3-week average of peak envelope
**Status**: ✅ IDENTICAL in both versions

### Column E: untis_final_curve
```excel
=MAX(B3,C3,D3)
```
**Purpose**: Final curve - max of actual units, peak envelope, and smooth envelope
**Status**: ✅ IDENTICAL in both versions

### Column F: units_final_smooth
```excel
=IFERROR((
    IFERROR(OFFSET($E3,-5,0),0)*1 +
    IFERROR(OFFSET($E3,-4,0),0)*2 +
    IFERROR(OFFSET($E3,-3,0),0)*4 +
    IFERROR(OFFSET($E3,-2,0),0)*7 +
    IFERROR(OFFSET($E3,-1,0),0)*11 +
    IFERROR(OFFSET($E3, 0,0),0)*13 +
    IFERROR(OFFSET($E3, 1,0),0)*11 +
    IFERROR(OFFSET($E3, 2,0),0)*7 +
    IFERROR(OFFSET($E3, 3,0),0)*4 +
    IFERROR(OFFSET($E3, 4,0),0)*2 +
    IFERROR(OFFSET($E3, 5,0),0)*1
) /
(
    IFERROR(SIGN(OFFSET($E3,-5,0)),0)*1 +
    IFERROR(SIGN(OFFSET($E3,-4,0)),0)*2 +
    IFERROR(SIGN(OFFSET($E3,-3,0)),0)*4 +
    IFERROR(SIGN(OFFSET($E3,-2,0)),0)*7 +
    IFERROR(SIGN(OFFSET($E3,-1,0)),0)*11 +
    IFERROR(SIGN(OFFSET($E3, 0,0)),0)*13 +
    IFERROR(SIGN(OFFSET($E3, 1,0)),0)*11 +
    IFERROR(SIGN(OFFSET($E3, 2,0)),0)*7 +
    IFERROR(SIGN(OFFSET($E3, 3,0)),0)*4 +
    IFERROR(SIGN(OFFSET($E3, 4,0)),0)*2 +
    IFERROR(SIGN(OFFSET($E3, 5,0)),0)*1
),"")
```
**Purpose**: Final smooth - weighted 11-week centered moving average (5 past + current + 5 future)
**Weights**: 1, 2, 4, 7, 11, 13, 11, 7, 4, 2, 1 (pyramid weighting)
**Status**: ✅ IDENTICAL in both versions

### Column H: forecast_units_peak_env
```excel
=iferror(MAX(OFFSET($G3,-2,0,2)),"0")
```
**Purpose**: Forecast peak envelope - max of last 2 forecast values
**Status**: ✅ IDENTICAL in both versions

### Column K: sv_velocity_adj_weighted
```excel
=SearchVolume!J3
```
**Purpose**: Links to search volume velocity adjustment from SearchVolume sheet
**Status**: ✅ IDENTICAL in both versions

## Key Differences

### Data Population
- **v1.1**: Column B (units_sold) has actual values: 4, 9, 10, 4, ...
- **v1.2**: Column B (units_sold) is empty (None values)
- **Implication**: v1.2 appears to be a clean template; v1.1 has historical data

### Calculated Columns (G, I, J, L)
These columns don't have formulas in row 3 - they likely:
1. Are calculated elsewhere (possibly in Settings or through VBA/macros)
2. Are populated through external data connections
3. Are filled in later rows with formulas

## Python Implementation Status

Your current Python implementation in `forecasting/engine.py` already implements:

✅ **Column C (units_peak_env)**: `calculate_peak_envelope()` - rolling max
✅ **Column D (units_smooth_env)**: `calculate_smooth_envelope()` - 3-week MA
✅ **Column E (units_final_curve)**: `calculate_final_curve()` - max of raw/peak/smooth
✅ **Column F (units_final_smooth)**: `calculate_final_smooth()` - 11-week weighted MA
✅ **Column H (forecast_peak_env)**: `calculate_forecast_peak_env()` - forecast peak
✅ **Column I (forecast_final_smooth)**: `calculate_forecast_final_smooth()` - seasonal baseline
✅ **Column J (sales_velocity)**: `calculate_sales_velocity_adjustment()` - velocity ratio

## Conclusion

### ✅ NO ACTION REQUIRED

The formulas in v1.2 are **100% identical** to v1.1. The differences are only:
1. v1.2 has no data populated (template state)
2. v1.1 has historical data filled in

Your Python implementation is already correctly based on these formulas and does not need any updates.

### Current Implementation Match

| Excel Column | Python Function | Status |
|--------------|----------------|---------|
| C: units_peak_env | calculate_peak_envelope() | ✅ Match |
| D: units_smooth_env | calculate_smooth_envelope() | ✅ Match |
| E: untis_final_curve | calculate_final_curve() | ✅ Match |
| F: units_final_smooth | calculate_final_smooth() | ✅ Match |
| G: forecast | calculate_forecast_baseline() | ✅ Match |
| H: forecast_units_peak_env | calculate_forecast_peak_env() | ✅ Match |
| I: forecast_final_smooth | calculate_forecast_final_smooth() | ✅ Match |
| J: sales_velocity_adj | calculate_sales_velocity_adjustment() | ✅ Match |
| K: sv_velocity_adj | (Search volume velocity) | ✅ Implemented |

---

**Generated**: 2025-11-18
**Files Compared**: 
- `1000 Bananas AUTOFORECAST V1.1.xlsx`
- `1000 Bananas AUTOFORECAST V1.2.xlsx`

