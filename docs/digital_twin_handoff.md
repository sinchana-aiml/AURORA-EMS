# Digital-Twin Handoff — Member 2 Weather Export
## Purpose

This document describes the weather data export produced by Member 2 for use
by Member 1's Digital Twin simulation engine.  It covers the data source,
column mapping, units, timezone, quality flags, and how to load the export.

---

## Files Produced

| File | Description |
|------|-------------|
| `data/digital_twin_weather_full.csv` | Full 10-year export (87,672 rows) — **gitignored, regenerate with script below** |
| `data/sample/digital_twin_weather_24h.csv` | First 24 hours — committed, used for integration testing |
| `scripts/export_for_digital_twin.py` | Adapter script that produces both files |
| `tests/test_digital_twin_export.py` | 13 automated tests — all passing |
| `requirements-dev.txt` | Dev dependencies (pytest) — install before running tests |

The original cleaned dataset `data/polar_weather_clean.csv` is **not modified**
by the export process.

### Regenerating the full export

The full 87,672-row CSV is excluded from version control (`.gitignore`).
Run this once after cloning to produce it locally:

```bash
python scripts/export_for_digital_twin.py
```

---

## Digital-Twin Required Columns

These four columns are the only ones the Digital Twin must consume.

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| `timestamp` | datetime, UTC ISO-8601 | — | Hourly timestamp, chronological, no gaps |
| `temperature_c` | float64 | °C | 2 m air temperature (NASA POWER T2M) |
| `irradiance_w_m2` | float64 | W/m² | All-sky surface shortwave downwelling (NASA POWER ALLSKY_SFC_SW_DWN) |
| `wind_speed_ms` | float64 | m/s | 10 m wind speed (NASA POWER WS10M) |

### Important rule for Member 1

Do **not** use `pv_available_kw` or `wind_available_kw` from the cleaned
dataset as inputs to the Digital Twin.  Those are Member 2 reference
calculations using a simplified proxy model.  Member 1's Digital Twin must
calculate `solar_power_kw` and `wind_power_kw` from its own verified equipment
models using `irradiance_w_m2`, `wind_speed_ms`, and `temperature_c`.

---

## Optional Quality / Provenance Columns

These columns are present in the export and may be used for filtering or
diagnostics.  They do not affect the required interface.

| Column | Values | Description |
|--------|--------|-------------|
| `weather_quality_flag` | `good` | Data quality label assigned by Member 2 pipeline |
| `scenario_name` | `baseline`, `storm` | `storm` when wind_speed_ms >= 20 m/s |
| `weather_source` | `NASA_POWER` | Data origin |
| `latitude` | -69.4069 | Bharati station, Antarctica |
| `longitude` | 76.1956 | Bharati station, Antarctica |

---

## Source Dataset Column Dictionary

Full column list of `data/polar_weather_clean.csv` (13 columns, 87,672 rows).

| Column | Unit | Source / Notes |
|--------|------|----------------|
| `timestamp_utc` | UTC ISO-8601 | Index; hourly 2015-01-01 to 2024-12-31 |
| `latitude` | decimal degrees | -69.4069 (Bharati station) |
| `longitude` | decimal degrees | 76.1956 |
| `temperature_c` | °C | NASA POWER T2M |
| `wind_speed_mps` | m/s | NASA POWER WS10M |
| `solar_irradiance_wm2` | W/m² | NASA POWER ALLSKY_SFC_SW_DWN |
| `precipitation_mm` | mm/hr | NASA POWER PRECTOTCORR |
| `surface_pressure_kpa` | kPa | NASA POWER PS |
| `pv_available_kw` | kW | Derived — Member 2 reference only, do not use in DT |
| `wind_available_kw` | kW | Derived — Member 2 reference only, do not use in DT |
| `weather_quality_flag` | categorical | `good` for all 87,672 rows |
| `weather_source` | string | `NASA_POWER` for all rows |
| `scenario_name` | categorical | `baseline` (87,243) / `storm` (429) |

---

## Column Mapping (Cleaned Dataset -> DT Export)

```
timestamp_utc        ->  timestamp
temperature_c        ->  temperature_c    (unchanged)
solar_irradiance_wm2 ->  irradiance_w_m2
wind_speed_mps       ->  wind_speed_ms
```

---

## Data Quality Summary

| Check | Result |
|-------|--------|
| Total rows | 87,672 |
| Missing values in required fields | 0 |
| Negative irradiance values | 0 |
| Negative wind speed values | 0 |
| Duplicate timestamps | 0 |
| Quality flag | 100% `good` |
| Timestamp coverage | 2015-01-01 00:00 UTC to 2024-12-31 23:00 UTC |
| Storm hours (wind >= 20 m/s) | 429 |
| Baseline hours | 87,243 |

---

## Timezone

All timestamps are UTC.  The `timestamp` column in the DT export is a
timezone-aware ISO-8601 string with `+00:00` suffix.

Load example:

```python
import pandas as pd

df = pd.read_csv(
    "data/digital_twin_weather_full.csv",
    parse_dates=["timestamp"]
)
# timestamp column will be UTC-aware after parse_dates
```

---

## Station Information

- Station: Bharati (Indian Antarctic Research Station)
- Latitude: -69.4069 N
- Longitude: 76.1956 E
- Data source: NASA POWER Hourly API (no API key required)
- Parameters fetched: T2M, WS10M, ALLSKY_SFC_SW_DWN, PRECTOTCORR, PS
- Community: RE (Renewable Energy)
- Time standard: UTC

---

## Assumptions and Limitations

1. Ambient air temperature (T2M at 2 m) is used as a proxy for PV module
   temperature in the Member 2 reference calculations.  Member 1 should apply
   its own thermal model if needed.

2. Wind speed is measured at 10 m height (WS10M).  If the turbine hub height
   differs, Member 1 should apply a wind-shear correction using the
   logarithmic or power-law profile.

3. The storm threshold (wind_speed_ms >= 20 m/s) is defined in `config.py`
   as `STORM_WIND_THRESHOLD_MS`.  The Digital Twin may use `scenario_name`
   to apply different operational rules during storm hours.

4. NASA POWER data is a reanalysis product, not direct station measurements.
   Spatial resolution is approximately 0.5 degrees.

5. The export contains no leap-second corrections.  All gaps in the original
   NASA POWER data were verified to be zero before export.
