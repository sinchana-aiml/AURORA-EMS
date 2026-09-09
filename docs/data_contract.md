
- G = solar irradiance (W/m²)
- panel_area = 166.67 m² (inferred from 30 kW rated capacity at 18% efficiency)
- efficiency = 0.18
- temp_coeff = -0.004 per °C
- T = ambient temperature (°C), used as proxy for module temperature
- Output clipped to [0, 30] kW

---

## Wind Power Formula

Generic cubic power curve (assumed — not a manufacturer curve):

- Below 3 m/s → 0 kW
- 3 to 12 m/s → 50 × ((v - 3) / (12 - 3))³ kW
- 12 to 25 m/s → 50 kW
- Above 25 m/s → 0 kW (turbine shutdown)

---

## How Other Members Should Use This File

```python
import pandas as pd

df = pd.read_csv(
    "data/polar_weather_clean.csv",
    index_col="timestamp_utc",
    parse_dates=True
)
