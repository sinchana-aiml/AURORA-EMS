# src/forecasting/preprocessor.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Forecasting Preprocessor
# Member 3: Renewable Energy & Station Load Forecasting
#
# Loads historical polar weather data, applies Member 1 Digital Twin physics
# functions to derive supervised ground-truth targets, validates physical bounds,
# and generates chronological train / validation / test splits.
#
# Reuses Member 1 physics directly — zero formula duplication.
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
from typing import Tuple, List, Optional
import numpy as np
import pandas as pd

# Ensure project root is available for imports
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import config
from src.digital_twin.renewable_model import solar_pv_output, wind_power_output
from src.digital_twin.load_model import (
    electrical_load,
    heating_load,
    total_load,
)

# Canonical file path to the cleaned polar weather dataset
DEFAULT_DATA_PATH = os.path.normpath(
    os.path.join(_ROOT, "data", "polar_weather_clean.csv")
)

# Standard targets required for forecasting
TARGET_COLUMNS: List[str] = [
    "solar_power_kw",
    "wind_power_kw",
    "heating_load_kw",
    "total_load_kw",
]

# Physical bounds defined by station configuration
TARGET_PHYSICAL_LIMITS = {
    "solar_power_kw": {
        "min": 0.0,
        "max": config.SOLAR_CAPACITY_KW,  # 40.0 kW
    },
    "wind_power_kw": {
        "min": 0.0,
        "max": config.WIND_CAPACITY_KW,  # 50.0 kW
    },
    "heating_load_kw": {
        "min": config.HEATING_BASE_KW,  # 15.0 kW
        "max": 100.0,  # Physically plausible upper bound for Antarctic conditions
    },
    "total_load_kw": {
        "min": config.BASE_LOAD_KW + config.FLEXIBLE_LOAD_KW + config.HEATING_BASE_KW,  # 45.0 kW
        "max": 150.0,
    },
}

# Standardized weather input columns
RAW_TO_STANDARD_COLS = {
    "timestamp_utc": "timestamp",
    "solar_irradiance_wm2": "irradiance_w_m2",
    "wind_speed_mps": "wind_speed_ms",
}


def compute_ground_truth_targets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply Member 1's physics functions across weather records to compute
    supervised energy generation and load targets.

    Directly invokes:
      - solar_pv_output(irradiance_w_m2, temperature_c)
      - wind_power_output(wind_speed_ms)
      - heating_load(temperature_c)
      - total_load(temperature_c, include_flexible=True)
      - electrical_load(include_flexible=True)

    Does NOT duplicate or re-implement any physics equation.
    Returns a copy of the dataframe with target columns added.
    """
    out = df.copy()

    # Determine column mapping
    irr_col = "irradiance_w_m2" if "irradiance_w_m2" in out.columns else "solar_irradiance_wm2"
    wind_col = "wind_speed_ms" if "wind_speed_ms" in out.columns else "wind_speed_mps"
    temp_col = "temperature_c"

    # Compute targets using Member 1 physics
    solar_targets = [
        solar_pv_output(irr, temp)
        for irr, temp in zip(out[irr_col], out[temp_col])
    ]
    wind_targets = [
        wind_power_output(ws)
        for ws in out[wind_col]
    ]
    heating_targets = [
        heating_load(temp)
        for temp in out[temp_col]
    ]
    total_targets = [
        total_load(temp, include_flexible=True)
        for temp in out[temp_col]
    ]

    out["solar_power_kw"] = np.round(solar_targets, 4)
    out["wind_power_kw"] = np.round(wind_targets, 4)
    out["heating_load_kw"] = np.round(heating_targets, 4)
    out["total_load_kw"] = np.round(total_targets, 4)
    out["electrical_load_kw"] = electrical_load(include_flexible=True)

    return out


def load_and_prepare_dataset(
    csv_path: str = DEFAULT_DATA_PATH,
    standardize_names: bool = True,
) -> pd.DataFrame:
    """
    Load data/polar_weather_clean.csv, parse timestamps, validate continuity,
    and compute ground-truth energy targets via Member 1 physics.

    Parameters:
    -----------
    csv_path : str
        Path to the cleaned polar weather dataset.
    standardize_names : bool
        If True, renames weather columns to match the Digital Twin telemetry schema.

    Returns:
    --------
    pd.DataFrame:
        Full 10-year dataset with standardized weather columns and supervised targets.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Clean weather dataset not found at: {csv_path}")

    # Read CSV, preserving timestamp_utc
    df = pd.read_csv(csv_path)

    # Validate presence of required raw columns
    required_raw = [
        "timestamp_utc",
        "temperature_c",
        "wind_speed_mps",
        "solar_irradiance_wm2",
    ]
    missing = [c for c in required_raw if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset is missing required raw columns: {missing}")

    # Parse timestamps as UTC-aware datetime
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)

    # Sort chronologically to guarantee monotonic order
    df = df.sort_values("timestamp_utc").reset_index(drop=True)

    # Standardize column names if requested
    if standardize_names:
        df = df.rename(columns=RAW_TO_STANDARD_COLS)
        time_col = "timestamp"
    else:
        time_col = "timestamp_utc"

    # Compute supervised ground-truth targets
    df = compute_ground_truth_targets(df)

    # Run validation checks
    validate_preprocessed_data(df, time_col=time_col)

    return df


def validate_preprocessed_data(
    df: pd.DataFrame,
    time_col: str = "timestamp",
) -> bool:
    """
    Validates physical constraints and data integrity on preprocessed data:
    1. Chronological monotonic timestamps with zero gaps.
    2. Zero missing/NaN values in required weather and target columns.
    3. Targets are non-negative.
    4. Targets strictly respect physical equipment ratings from config.py.

    Raises ValueError on constraint violation. Returns True if valid.
    """
    if df.empty:
        raise ValueError("DataFrame is empty.")

    # Check timestamp ordering
    ts = pd.to_datetime(df[time_col], utc=True)
    if not ts.is_monotonic_increasing:
        raise ValueError(f"Timestamps in '{time_col}' are not strictly monotonically increasing.")

    # Check for nulls in required columns
    required_cols = [
        time_col,
        "temperature_c",
        "solar_power_kw",
        "wind_power_kw",
        "heating_load_kw",
        "total_load_kw",
    ]
    null_counts = df[required_cols].isna().sum()
    if null_counts.sum() > 0:
        raise ValueError(f"Missing values detected in required columns:\n{null_counts[null_counts > 0]}")

    # Check non-negativity
    for col in TARGET_COLUMNS:
        neg_count = (df[col] < 0).sum()
        if neg_count > 0:
            raise ValueError(f"Target column '{col}' contains {neg_count} negative values.")

    # Check equipment ratings
    solar_max = TARGET_PHYSICAL_LIMITS["solar_power_kw"]["max"]
    if (df["solar_power_kw"] > solar_max + 1e-4).any():
        max_val = df["solar_power_kw"].max()
        raise ValueError(f"solar_power_kw exceeded rated capacity of {solar_max} kW (max: {max_val})")

    wind_max = TARGET_PHYSICAL_LIMITS["wind_power_kw"]["max"]
    if (df["wind_power_kw"] > wind_max + 1e-4).any():
        max_val = df["wind_power_kw"].max()
        raise ValueError(f"wind_power_kw exceeded rated capacity of {wind_max} kW (max: {max_val})")

    # Check wind cut-out behavior: when wind >= 25 m/s, wind_power_kw must be 0.0
    wind_col = "wind_speed_ms" if "wind_speed_ms" in df.columns else "wind_speed_mps"
    cutout_mask = df[wind_col] >= config.WIND_CUT_OUT_MS
    if cutout_mask.any():
        non_zero_cutout = (df.loc[cutout_mask, "wind_power_kw"] > 0).sum()
        if non_zero_cutout > 0:
            raise ValueError(
                f"Wind turbine produced power at or above cut-out speed ({config.WIND_CUT_OUT_MS} m/s) "
                f"in {non_zero_cutout} records."
            )

    return True


def create_chronological_splits(
    df: pd.DataFrame,
    time_col: str = "timestamp",
    train_end: str = "2022-12-31 23:00:00+00:00",
    val_end: str = "2023-12-31 23:00:00+00:00",
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split the dataset chronologically into Train, Validation, and Test sets.

    Defined Splits:
    ---------------
    - Train      : 2015-01-01 00:00:00+00:00 to 2022-12-31 23:00:00+00:00 (8 years)
    - Validation : 2023-01-01 00:00:00+00:00 to 2023-12-31 23:00:00+00:00 (1 year)
    - Test       : 2024-01-01 00:00:00+00:00 to 2024-12-31 23:00:00+00:00 (1 year)

    Guarantees:
    - Zero temporal overlap.
    - Zero leakage between train, validation, and test periods.
    """
    ts = pd.to_datetime(df[time_col], utc=True)
    t_train_end = pd.to_datetime(train_end, utc=True)
    t_val_end = pd.to_datetime(val_end, utc=True)

    train_mask = ts <= t_train_end
    val_mask = (ts > t_train_end) & (ts <= t_val_end)
    test_mask = ts > t_val_end

    train_df = df[train_mask].copy().reset_index(drop=True)
    val_df = df[val_mask].copy().reset_index(drop=True)
    test_df = df[test_mask].copy().reset_index(drop=True)

    # Verify partition completeness
    total_split_rows = len(train_df) + len(val_df) + len(test_df)
    if total_split_rows != len(df):
        raise ValueError(
            f"Split row count ({total_split_rows}) does not match original DataFrame row count ({len(df)})."
        )

    return train_df, val_df, test_df
