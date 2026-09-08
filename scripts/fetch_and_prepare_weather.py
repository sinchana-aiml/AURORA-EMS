import sys
import os
import requests
import pandas as pd

# Allow importing config.py from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


# ─────────────────────────────────────────────────────────────────────────────
# Station location
# ─────────────────────────────────────────────────────────────────────────────
LATITUDE  = -69.4069   # Bharati station, Antarctica
LONGITUDE =  76.1956


# ─────────────────────────────────────────────────────────────────────────────
# Fetch weather from NASA POWER — one year at a time
# ─────────────────────────────────────────────────────────────────────────────
url   = "https://power.larc.nasa.gov/api/temporal/hourly/point"
YEARS = range(2015, 2025)  # 2015 to 2024 inclusive

yearly_frames = []

for year in YEARS:
    print(f"Fetching {year}...")

    params = {
        "parameters": "T2M,WS10M,ALLSKY_SFC_SW_DWN,PRECTOTCORR,PS",
        "community": "RE",
        "longitude": LONGITUDE,
        "latitude": LATITUDE,
        "start": f"{year}0101",
        "end": f"{year}1231",
        "format": "JSON",
        "time-standard": "UTC",
    }

    response = requests.get(url, params=params, timeout=120)
    response.raise_for_status()

    year_data   = response.json()
    year_params = year_data["properties"]["parameter"]
    year_df     = pd.DataFrame(year_params)
    yearly_frames.append(year_df)
    print(f"  {year}: {len(year_df)} rows")

print("\nAll years fetched. Combining...")
df = pd.concat(yearly_frames)

df.index = pd.to_datetime(df.index, format="%Y%m%d%H", utc=True)
df.index.name = "timestamp_utc"

df = df.rename(columns={
    "T2M":               "temperature_c",
    "WS10M":             "wind_speed_mps",
    "ALLSKY_SFC_SW_DWN": "solar_irradiance_wm2",
    "PRECTOTCORR":       "precipitation_mm",
    "PS":                "surface_pressure_kpa",
})


# ─────────────────────────────────────────────────────────────────────────────
# Data validation
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Data Validation ---")

duplicate_count = df.index.duplicated().sum()
print("Duplicate timestamps:", duplicate_count)

print("\nMissing values:")
print(df.isna().sum())

invalid_temperature   = (df["temperature_c"] < -100) | (df["temperature_c"] > 60)
invalid_wind          = df["wind_speed_mps"] < 0
invalid_solar         = df["solar_irradiance_wm2"] < 0
invalid_precipitation = df["precipitation_mm"] < 0
invalid_pressure      = df["surface_pressure_kpa"] <= 0

print("\nInvalid values:")
print("Temperature:",      invalid_temperature.sum())
print("Wind speed:",       invalid_wind.sum())
print("Solar irradiance:", invalid_solar.sum())
print("Precipitation:",    invalid_precipitation.sum())
print("Surface pressure:", invalid_pressure.sum())

time_diff  = df.index.to_series().diff().dropna()
non_hourly = (time_diff != pd.Timedelta(hours=1)).sum()
print("\nNon-hourly timestamp gaps:", non_hourly)


# ─────────────────────────────────────────────────────────────────────────────
# Weather quality flag
# ─────────────────────────────────────────────────────────────────────────────
df["weather_quality_flag"] = "good"

missing_rows = df[
    ["temperature_c", "wind_speed_mps", "solar_irradiance_wm2",
     "precipitation_mm", "surface_pressure_kpa"]
].isna().any(axis=1)
df.loc[missing_rows, "weather_quality_flag"] = "missing"

invalid_rows = (
    invalid_temperature | invalid_wind | invalid_solar
    | invalid_precipitation | invalid_pressure
)
df.loc[invalid_rows & ~missing_rows, "weather_quality_flag"] = "review"

print("\nWeather quality summary:")
print(df["weather_quality_flag"].value_counts())


# ─────────────────────────────────────────────────────────────────────────────
# PV available power  (derived — NOT measured)
#
# Formula:  P_pv = (G / 1000) * A_panel * eta * (1 + gamma * (T - 25))
#
# Assumptions:
#   - Panel area inferred from rated capacity and efficiency:
#     A_panel = SOLAR_CAPACITY_KW * 1000 / (1000 * SOLAR_EFFICIENCY)
#   - Ambient temperature used as proxy for module temperature (simplification)
#   - Temperature coefficient applied relative to 25 °C STC reference
#   - Output clipped to [0, SOLAR_CAPACITY_KW]
# ─────────────────────────────────────────────────────────────────────────────
panel_area_m2 = (config.SOLAR_CAPACITY_KW * 1000) / (1000 * config.SOLAR_EFFICIENCY)

pv_raw = (
    (df["solar_irradiance_wm2"] / 1000)
    * panel_area_m2
    * config.SOLAR_EFFICIENCY
    * (1 + config.SOLAR_TEMP_COEFF * (df["temperature_c"] - 25))
)


df["pv_available_kw"] = pv_raw.clip(lower=0, upper=config.SOLAR_CAPACITY_KW)


# ─────────────────────────────────────────────────────────────────────────────
# Wind available power  (derived — NOT measured)
#
# Assumed generic cubic power curve:
#   - below cut-in speed     → 0 kW
#   - cut-in to rated speed  → cubic interpolation
#   - rated to cut-out       → rated capacity
#   - above cut-out          → 0 kW (turbine shuts down for safety)
#
# This is NOT a manufacturer curve. It is a standard assumed model.
# ─────────────────────────────────────────────────────────────────────────────
v     = df["wind_speed_mps"]
v_in  = config.WIND_CUT_IN_MS
v_r   = config.WIND_RATED_MS
v_out = config.WIND_CUT_OUT_MS
P_r   = config.WIND_CAPACITY_KW

wind_power = pd.Series(0.0, index=df.index)
ramp_mask  = (v >= v_in) & (v < v_r)
rated_mask = (v >= v_r)  & (v <= v_out)

wind_power[ramp_mask]  = P_r * ((v[ramp_mask] - v_in) / (v_r - v_in)) ** 3
wind_power[rated_mask] = P_r

df["wind_available_kw"] = wind_power


# ─────────────────────────────────────────────────────────────────────────────
# Metadata columns
# ─────────────────────────────────────────────────────────────────────────────
df["latitude"]       = LATITUDE
df["longitude"]      = LONGITUDE
df["weather_source"] = "NASA_POWER"
df["scenario_name"]  = "baseline"


# ─────────────────────────────────────────────────────────────────────────────
# Canonical column order
# ─────────────────────────────────────────────────────────────────────────────
df = df[[
    "latitude",
    "longitude",
    "temperature_c",
    "wind_speed_mps",
    "solar_irradiance_wm2",
    "precipitation_mm",
    "surface_pressure_kpa",
    "pv_available_kw",
    "wind_available_kw",
    "weather_quality_flag",
    "weather_source",
    "scenario_name",
]]


# ─────────────────────────────────────────────────────────────────────────────
# Save canonical dataset
# ─────────────────────────────────────────────────────────────────────────────
output_path = os.path.join(os.path.dirname(__file__), "..", "data", "polar_weather_clean.csv")
df.to_csv(output_path)
print("\nSaved:", os.path.normpath(output_path))


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print("\nDataFrame shape:", df.shape)
print("\nColumns:", df.columns.tolist())
print("\nFirst 3 rows:")
print(df.head(3))
print("\nPV range (kW):   ", round(df["pv_available_kw"].min(), 3), "–", round(df["pv_available_kw"].max(), 3))
print("Wind range (kW): ", round(df["wind_available_kw"].min(), 3), "–", round(df["wind_available_kw"].max(), 3))
