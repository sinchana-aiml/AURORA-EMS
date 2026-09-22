# AURORA-EMS Forecasting Service Contract
## Member 3: Renewable Generation & Station Load Forecasting

---

## 1. Purpose

The AURORA-EMS forecasting service provides a unified, deterministic, and probabilistic inference interface for renewable energy generation (Solar PV and Wind Turbine) and station demand (Electrical and Heating Load).

It is specifically engineered to supply Member 4 (Energy Optimization & Dispatch) and Member 1 (Digital Twin Simulation) with a stable, physically bounded forecasting contract under both normal operations and communication-outage scenarios.

---

## 2. Entry Points

The forecasting service exposes two public APIs that produce identical DataFrame outputs.

### 2.1 Primary Class API (`ForecastService`)

```python
from src.forecasting.service import ForecastService

service = ForecastService()

# 24-hour day-ahead forecast (default)
forecast_df = service.generate_forecast(
    current_timestamp="2024-07-01T00:00:00+00:00",
    horizon_hours=24,
    include_flexible=True,  # True: 30 kW electrical; False: 20 kW critical
    validate=True,          # Automatically validate output before return
)

# Convenience method for 24h horizon
forecast_24h = service.get_24h_forecast(
    current_timestamp="2024-07-01T00:00:00+00:00",
)
```

### 2.2 Secondary Function API (`get_forecast`)

```python
from src.forecasting.service import get_forecast

forecast_df = get_forecast(
    current_timestamp="2024-07-01T00:00:00+00:00",
    horizon_hours=24,
    include_flexible=True,
)
```

---

## 3. Output Contract Schema (21 Columns)

Every call to `generate_forecast()` or `get_forecast()` produces a `pandas.DataFrame` containing exactly the following 21 columns:

| Column Name | Type | Units | Description |
|:---|:---|:---|:---|
| `timestamp` | `str` (ISO-8601 UTC) | — | Prediction target timestamp (`YYYY-MM-DDTHH:MM:SS+00:00`) |
| `step_ahead` | `int` | hours | Lookahead horizon step index ($1, 2, \dots, H$) |
| `solar_power_kw_p10` | `float` | kW | Solar PV generation 10th percentile (lower reserve floor) |
| `solar_power_kw_p50` | `float` | kW | Solar PV generation 50th percentile (expected median) |
| `solar_power_kw_p90` | `float` | kW | Solar PV generation 90th percentile (upper potential ceiling) |
| `wind_power_kw_p10` | `float` | kW | Wind turbine generation 10th percentile (conservative floor) |
| `wind_power_kw_p50` | `float` | kW | Wind turbine generation 50th percentile (expected median) |
| `wind_power_kw_p90` | `float` | kW | Wind turbine generation 90th percentile (curtailment risk ceiling) |
| `electrical_load_kw` | `float` | kW | Station electrical demand (30.0 kW with flexible, 20.0 kW critical) |
| `heating_load_kw_p50` | `float` | kW | Expected heating load based on outside temperature |
| `total_load_kw_p10` | `float` | kW | Total station load 10th percentile (`electrical_load + heating_p10`) |
| `total_load_kw_p50` | `float` | kW | Total station load 50th percentile (`electrical_load + heating_p50`) |
| `total_load_kw_p90` | `float` | kW | Total station load 90th percentile (`electrical_load + heating_p90`) |
| `net_load_kw_p50` | `float` | kW | Expected net load: `total_load_p50 - (solar_p50 + wind_p50)` |
| `temperature_c_pred` | `float` | °C | Predicted ambient surface temperature at 2 m |
| `wind_speed_ms_pred` | `float` | m/s | Predicted 10 m wind speed |
| `irradiance_w_m2_pred` | `float` | W/m² | Predicted all-sky surface solar irradiance |
| `storm_risk_flag` | `bool` | — | `True` when predicted wind speed $\ge 20.0\text{ m/s}$ |
| `turbine_cutout_risk` | `bool` | — | `True` when predicted wind speed $\ge 25.0\text{ m/s}$ (shutdown) |
| `confidence_score` | `float` | $[0.0, 1.0]$ | Forecast confidence metric, decaying over lookahead horizon |
| `forecast_mode` | `str` | — | Active operational mode identifier (e.g., `offline_climatology`) |

---

## 4. Horizon and Probabilistic Quantiles

### 4.1 Lookahead Horizon ($1$ to $48$ Hours)
The service supports arbitrary forecast horizons from 1 to 48 hours. The default standard operation uses a 24-hour day-ahead horizon ($H = 24$). Requests with $H < 1$ or $H > 48$ raise a `ValueError`.

### 4.2 Probabilistic Quantiles ($P_{10}, P_{50}, P_{90}$)
Forecasts provide multi-quantile uncertainty bounds to empower risk-aware dispatch optimization in Member 4:
- **$P_{10}$ (Conservative Floor)**: 90% probability that actual generation exceeds this value. Used for firm spinning reserve allocation and minimum capacity commitments.
- **$P_{50}$ (Expected Median)**: Primary baseline for economic dispatch and energy balance calculations.
- **$P_{90}$ (Upper Ceiling)**: 10% probability that actual generation exceeds this value. Used to evaluate battery charging headroom and renewable curtailment risk.
- **Monotonicity Guarantee**: Enforced strictly:
  $$\forall t,\quad P_{10}(t) \le P_{50}(t) \le P_{90}(t)$$

---

## 5. Operational Modes & Autonomous Fallback

The forecasting service operates under multiple operational regimes depending on telemetry availability:

| Mode Identifier | Trigger Condition | Engine Description |
|:---|:---|:---|
| `online_ml` / `ml_ensemble` | External NWP feed & trained models available | Multi-quantile HistGradientBoosting regressors conditioned on astronomical solar geometry and lagged weather features. |
| `offline_climatology` | Standalone operation / local edge deployment | High-resolution historical polar climatology lookup tables conditioned on day-of-year and hour. |
| `offline_climatology_comms_outage` | Communication blackout (`is_offline=True`) | Climatology engine with adaptive uncertainty widening (+35% spread between $P_{10}$ and $P_{90}$). |
| `persistence_diurnal` | Recent sensor history available | Diurnal 24-hour persistence baseline. |

### 5.1 Communication-Outage Uncertainty Widening
During severe storms or communication satellite outages (`is_offline=True`), the service autonomously widens prediction intervals:
- Solar and Wind $P_{10}$ are decreased by 35% ($P_{10} \times 0.65$).
- Solar and Wind $P_{90}$ are increased by 35% ($P_{90} \times 1.35$), clamped to physical capacity.
- Heating load $P_{90}$ is expanded by 15%.
- `confidence_score` is lowered, alerting Member 4 to schedule conservative diesel reserves.

---

## 6. Extreme Weather & Risk Thresholds

Alarms for extreme Antarctic katabatic and blizzard events are directly integrated:
- **Storm Risk (`storm_risk_flag = True`)**: Triggered when predicted wind speed $\ge 20.0\text{ m/s}$ (`config.STORM_WIND_THRESHOLD_MS`).
- **Turbine Cut-Out Risk (`turbine_cutout_risk = True`)**: Triggered when predicted wind speed $\ge 25.0\text{ m/s}$ (`config.WIND_CUT_OUT_MS`). At or above this threshold, turbine output immediately cuts out to $0.0\text{ kW}$ to protect mechanical equipment from structural damage.

---

## 7. Member 1 Digital Twin & Member 2 Weather Compatibility

### 7.1 Canonical Weather Naming
The interface strictly adheres to the unified naming agreed across members:
- `timestamp`: UTC ISO-8601 string.
- `temperature_c`: 2 m ambient air temperature in °C.
- `irradiance_w_m2`: All-sky surface shortwave solar irradiance in W/m².
- `wind_speed_ms`: 10 m wind speed in m/s.

### 7.2 Member 2 Raw Aliases Normalization
The preprocessing and validation engine automatically normalizes historical raw weather data:
```
timestamp_utc        --> timestamp
solar_irradiance_wm2 --> irradiance_w_m2
wind_speed_mps       --> wind_speed_ms
```

### 7.3 Renewable Equipment Physical Ratings
All renewable generation models align exactly with Member 1's physical specifications:
- **Solar PV**: Rated capacity $\le 40.0\text{ kW}$ (`config.SOLAR_CAPACITY_KW`).
  - Reference irradiance: $1000.0\text{ W/m²}$.
  - System performance ratio: $0.82$.
  - Temperature coefficient: $-0.004/\text{°C}$ relative to $25.0\text{°C}$.
- **Wind Turbine**: Rated capacity $\le 50.0\text{ kW}$ (`config.WIND_CAPACITY_KW`).
  - Cut-in speed: $3.0\text{ m/s}$ (linear ramp begins).
  - Rated speed: $12.0\text{ m/s}$ (linear ramp reaches $50.0\text{ kW}$).
  - Cut-out speed: $25.0\text{ m/s}$ (shuts down to $0.0\text{ kW}$).
  - *Note*: Member 1's verified linear power ramp is preserved; generic cubic approximations must not be used.

### 7.4 Station Load Model & Flexible Load Split
Station load conforms directly to Member 1's `load_model.py`:
$$\text{Total Load} = \text{Electrical Load} + \text{Heating Load}(T)$$
- **Electrical Load**:
  - Critical base load: $20.0\text{ kW}$ (`config.BASE_LOAD_KW`), non-sheddable.
  - Flexible load: $10.0\text{ kW}$ (`config.FLEXIBLE_LOAD_KW`), sheddable during shortfalls.
  - With `include_flexible=True`: $\text{electrical\_load} = 30.0\text{ kW}$.
  - With `include_flexible=False`: $\text{electrical\_load} = 20.0\text{ kW}$.
- **Heating Load**:
  - Base heating: $15.0\text{ kW}$ (`config.HEATING_BASE_KW`) at $T \ge 0\text{ °C}$.
  - Cold-temperature increase: $+0.8\text{ kW/°C}$ (`config.HEATING_TEMP_COEFF`) for temperatures below $0\text{ °C}$:
    $$\text{Heating Load}(T) = 15.0 + 0.8 \times \max(0, -T)$$
- **Total Station Load (with flexible load)**:
  $$\text{Total Load}(T) = 45.0 + 0.8 \times \max(0, -T)$$

---

## 8. Forecast Validation Guarantees

All forecast outputs are strictly validated prior to dispatch via `validate_forecast_output()`. The validation engine guarantees:
1. **DataFrame Non-Empty**: Must contain at least 1 row.
2. **Schema Completeness**: All 21 required columns are present with correct naming.
3. **Chronological Monotonicity**: Timestamps are valid UTC datetimes and strictly increasing ($t_1 < t_2 < \dots < t_H$).
4. **Step Sequence**: `step_ahead` forms a consecutive sequence from 1 to $H$.
5. **Numerical Integrity**: No `NaN`, `None`, or infinite values in numerical forecast columns.
6. **Quantile Monotonicity**: $P_{10} \le P_{50} \le P_{90}$ for Solar PV, Wind Turbine, and Total Load.
7. **Physical Limits**:
   - $0.0 \le \text{solar\_power\_kw} \le 40.0\text{ kW}$.
   - $0.0 \le \text{wind\_power\_kw} \le 50.0\text{ kW}$.
8. **Load Non-Negativity**: Electrical, heating, and total load quantiles are $\ge 0.0\text{ kW}$.
9. **Net Load Identity**:
   $$\text{net\_load\_kw\_p50} = \text{total\_load\_kw\_p50} - (\text{solar\_power\_kw\_p50} + \text{wind\_power\_kw\_p50})$$
   (Net load may be negative when renewable generation exceeds total load).
10. **Boolean Risk Flags**: `storm_risk_flag` and `turbine_cutout_risk` strictly contain boolean values.
11. **Confidence Range**: `confidence_score` is strictly within $[0.0, 1.0]$.
12. **Mode Recognition**: `forecast_mode` is one of the supported operational mode strings.

---

## 9. Member 4 Optimization Integration Expectations

Member 4 optimization routines can safely rely on the following behavioral contracts:
- **Deterministic Schema**: Column names and types will not mutate across calls or versions.
- **Zero Look-Ahead Bias**: Features and forecasts are computed strictly causally without future target leakage.
- **Fail-Safe Operation**: If external telemetry is interrupted, the service autonomously switches to offline climatology without throwing exceptions.
- **Direct Battery / Generator Inputs**:
  - `net_load_kw_p50 > 0`: Energy shortfall requiring battery discharge and/or diesel generator dispatch.
  - `net_load_kw_p50 < 0`: Renewable surplus available for battery charging or dump-load absorption.
