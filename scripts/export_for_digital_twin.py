"""
export_for_digital_twin.py
--------------------------
Adapter that reads the Member 2 cleaned weather dataset and produces a
Digital-Twin-compatible CSV containing only raw environmental inputs.

Member 1's Digital Twin calculates its own solar_power_kw and wind_power_kw
from its verified equipment models.  This module intentionally does NOT
include pv_available_kw or wind_available_kw in the DT export.

Digital-Twin required columns
------------------------------
  timestamp        - UTC ISO-8601, chronological order
  temperature_c    - degrees C  (2 m air temperature)
  irradiance_w_m2  - W/m2 (all-sky surface shortwave downwelling)
  wind_speed_ms    - m/s  (10 m wind speed)

Optional quality/provenance columns (preserved, do not affect DT interface)
----------------------------------------------------------------------------
  weather_quality_flag, scenario_name, weather_source, latitude, longitude
"""

import os
import sys
import pandas as pd

# -- Paths -------------------------------------------------------------------
ROOT        = os.path.join(os.path.dirname(__file__), "..")
SOURCE_CSV  = os.path.normpath(os.path.join(ROOT, "data", "polar_weather_clean.csv"))
SAMPLE_DIR  = os.path.normpath(os.path.join(ROOT, "data", "sample"))
SAMPLE_CSV  = os.path.join(SAMPLE_DIR, "digital_twin_weather_24h.csv")
FULL_CSV    = os.path.normpath(os.path.join(ROOT, "data", "digital_twin_weather_full.csv"))

# Required DT columns (in order)
DT_REQUIRED = ["timestamp", "temperature_c", "irradiance_w_m2", "wind_speed_ms"]

# Optional provenance columns to carry through
DT_OPTIONAL = [
    "weather_quality_flag",
    "scenario_name",
    "weather_source",
    "latitude",
    "longitude",
]


def load_cleaned_weather(path: str = SOURCE_CSV) -> pd.DataFrame:
    """Load the canonical cleaned weather CSV.  Index is NOT set here so that
    timestamp_utc is available as a plain column for renaming."""
    df = pd.read_csv(path, parse_dates=["timestamp_utc"])
    return df


def build_dt_export(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map cleaned-weather columns → Digital-Twin columns.

    Mapping
    -------
    timestamp_utc        → timestamp
    temperature_c        → temperature_c   (unchanged)
    solar_irradiance_wm2 → irradiance_w_m2
    wind_speed_mps       → wind_speed_ms

    Validation applied
    ------------------
    - Rows with any missing value in the four required fields are dropped and
      reported; they are NOT silently passed to the Digital Twin.
    - Negative irradiance is rejected (set to NaN then dropped).
    - Negative wind speed is rejected (set to NaN then dropped).
    - Output is sorted chronologically by timestamp.
    - Required columns are cast to numeric (timestamp stays datetime).
    """
    out = df.copy()

    # -- Rename to DT names --------------------------------------------------
    out = out.rename(columns={
        "timestamp_utc":       "timestamp",
        "solar_irradiance_wm2": "irradiance_w_m2",
        "wind_speed_mps":      "wind_speed_ms",
    })

    # -- Cast numeric fields -------------------------------------------------
    for col in ["temperature_c", "irradiance_w_m2", "wind_speed_ms"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    # -- Reject negative irradiance and negative wind speed ------------------
    out.loc[out["irradiance_w_m2"] < 0, "irradiance_w_m2"] = float("nan")
    out.loc[out["wind_speed_ms"]   < 0, "wind_speed_ms"]   = float("nan")

    # -- Drop rows missing any required field --------------------------------
    before = len(out)
    out = out.dropna(subset=DT_REQUIRED)
    dropped = before - len(out)
    if dropped:
        print(f"  WARNING: {dropped} rows dropped - missing/invalid required field(s).")

    # -- Chronological order -------------------------------------------------
    out = out.sort_values("timestamp").reset_index(drop=True)

    # -- Select and order columns: required first, then optional if present --
    optional_present = [c for c in DT_OPTIONAL if c in out.columns]
    out = out[DT_REQUIRED + optional_present]

    return out


def export_full(df_dt: pd.DataFrame, path: str = FULL_CSV) -> None:
    df_dt.to_csv(path, index=False)
    print(f"  Full export saved: {path}  ({len(df_dt)} rows)")


def export_sample_24h(df_dt: pd.DataFrame, path: str = SAMPLE_CSV) -> pd.DataFrame:
    """Export the first 24 rows as an integration-test sample."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sample = df_dt.head(24).copy()
    sample.to_csv(path, index=False)
    print(f"  24-hour sample saved: {path}  ({len(sample)} rows)")
    return sample


def print_summary(df_dt: pd.DataFrame, sample: pd.DataFrame) -> None:
    print("\n--- Digital-Twin export summary ---")
    print(f"  Rows (full):        {len(df_dt)}")
    print(f"  Rows (sample):      {len(sample)}")
    print(f"  Columns:            {df_dt.columns.tolist()}")
    print(f"  Timestamp range:    {df_dt['timestamp'].iloc[0]}  to  {df_dt['timestamp'].iloc[-1]}")
    print(f"  Timezone:           UTC (ISO-8601)")
    print(f"  Temperature range:  {df_dt['temperature_c'].min():.2f} to {df_dt['temperature_c'].max():.2f} C")
    print(f"  Irradiance range:   {df_dt['irradiance_w_m2'].min():.2f} to {df_dt['irradiance_w_m2'].max():.2f} W/m2")
    print(f"  Wind speed range:   {df_dt['wind_speed_ms'].min():.2f} to {df_dt['wind_speed_ms'].max():.2f} m/s")
    print(f"  Missing (required): {df_dt[DT_REQUIRED].isna().sum().sum()}")
    print(f"  Quality flags:      {df_dt['weather_quality_flag'].value_counts().to_dict()}")
    print(f"  Scenarios:          {df_dt['scenario_name'].value_counts().to_dict()}")
    print(f"  Source:             {df_dt['weather_source'].unique().tolist()}")
    print(f"  Station coords:     lat {df_dt['latitude'].iloc[0]}, lon {df_dt['longitude'].iloc[0]}")
    print("\n  First 5 rows of 24-hour sample:")
    print(sample.head(5).to_string(index=False))
    print("-----------------------------------")


if __name__ == "__main__":
    print("Loading cleaned weather data...")
    raw = load_cleaned_weather()
    print(f"  Source rows: {len(raw)},  columns: {raw.columns.tolist()}")

    print("\nBuilding Digital-Twin export...")
    df_dt = build_dt_export(raw)

    export_full(df_dt)
    sample = export_sample_24h(df_dt)
    print_summary(df_dt, sample)
