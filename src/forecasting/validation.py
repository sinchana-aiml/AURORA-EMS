"""
Validation utilities for the AURORA-EMS forecasting service.

This module validates the existing Phase 3 forecasting contract
without changing the public ForecastService output schema.
"""

import os
import sys
from typing import List

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------

_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import config


# ---------------------------------------------------------------------------
# Phase 3 Forecast Contract
# ---------------------------------------------------------------------------

EXPECTED_CONTRACT_COLUMNS: List[str] = [
    "timestamp",
    "step_ahead",
    "solar_power_kw_p10",
    "solar_power_kw_p50",
    "solar_power_kw_p90",
    "wind_power_kw_p10",
    "wind_power_kw_p50",
    "wind_power_kw_p90",
    "electrical_load_kw",
    "heating_load_kw_p50",
    "total_load_kw_p10",
    "total_load_kw_p50",
    "total_load_kw_p90",
    "net_load_kw_p50",
    "temperature_c_pred",
    "wind_speed_ms_pred",
    "irradiance_w_m2_pred",
    "storm_risk_flag",
    "turbine_cutout_risk",
    "confidence_score",
    "forecast_mode",
]


NUMERIC_FORECAST_COLUMNS: List[str] = [
    "step_ahead",
    "solar_power_kw_p10",
    "solar_power_kw_p50",
    "solar_power_kw_p90",
    "wind_power_kw_p10",
    "wind_power_kw_p50",
    "wind_power_kw_p90",
    "electrical_load_kw",
    "heating_load_kw_p50",
    "total_load_kw_p10",
    "total_load_kw_p50",
    "total_load_kw_p90",
    "net_load_kw_p50",
    "temperature_c_pred",
    "wind_speed_ms_pred",
    "irradiance_w_m2_pred",
    "confidence_score",
]


VALID_FORECAST_MODES = {
    "online_ml",
    "ml_ensemble",
    "offline_fallback",
    "offline_climatology",
    "offline_climatology_comms_outage",
    "persistence_diurnal",
    "persistence_last_value",
}


# ---------------------------------------------------------------------------
# Weather compatibility
# ---------------------------------------------------------------------------

CANONICAL_WEATHER_FIELDS = [
    "timestamp",
    "temperature_c",
    "irradiance_w_m2",
    "wind_speed_ms",
]


WEATHER_ALIASES = {
    "timestamp_utc": "timestamp",
    "solar_irradiance_wm2": "irradiance_w_m2",
    "wind_speed_mps": "wind_speed_ms",
}


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class ForecastValidationError(ValueError):
    """Raised when forecast output violates the agreed contract."""


# ---------------------------------------------------------------------------
# Forecast validation helpers
# ---------------------------------------------------------------------------

def _require_columns(
    df: pd.DataFrame,
    required_columns: List[str],
) -> None:
    """Ensure all required columns are present."""

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ForecastValidationError(
            f"Forecast output is missing required contract column(s): {missing}"
        )


def _validate_numeric_columns(
    df: pd.DataFrame,
) -> None:
    """Ensure numeric forecast fields contain finite numeric values."""

    for column in NUMERIC_FORECAST_COLUMNS:
        values = pd.to_numeric(df[column], errors="coerce")

        if values.isna().any():
            raise ForecastValidationError(
                f"Forecast column '{column}' contains non-numeric or NaN values."
            )

        if not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ForecastValidationError(
                f"Forecast column '{column}' contains non-finite values."
            )


def _validate_step_sequence(
    df: pd.DataFrame,
) -> None:
    """Validate that forecast horizons are consecutive starting at one."""

    steps = df["step_ahead"].astype(int).tolist()
    expected = list(range(1, len(df) + 1))

    if steps != expected:
        raise ForecastValidationError(
            "Forecast 'step_ahead' must be consecutive starting at 1."
        )


def _validate_quantile_monotonicity(
    df: pd.DataFrame,
) -> None:
    """Ensure P10 <= P50 <= P90 for probabilistic forecasts."""

    quantile_groups = {
        "solar_power": (
            "solar_power_kw_p10",
            "solar_power_kw_p50",
            "solar_power_kw_p90",
        ),
        "wind_power": (
            "wind_power_kw_p10",
            "wind_power_kw_p50",
            "wind_power_kw_p90",
        ),
        "total_load": (
            "total_load_kw_p10",
            "total_load_kw_p50",
            "total_load_kw_p90",
        ),
    }

    for name, columns in quantile_groups.items():
        p10, p50, p90 = columns

        invalid = (
            (df[p10] > df[p50])
            | (df[p50] > df[p90])
        )

        if invalid.any():
            raise ForecastValidationError(
                f"Forecast quantiles for '{name}' violate "
                "P10 <= P50 <= P90."
            )


def _validate_physical_limits(
    df: pd.DataFrame,
) -> None:
    """Validate renewable generation and load physical constraints."""

    # Solar generation must remain within installed capacity.
    if (
        (df["solar_power_kw_p10"] < 0).any()
        or (df["solar_power_kw_p50"] < 0).any()
        or (df["solar_power_kw_p90"] < 0).any()
    ):
        raise ForecastValidationError(
            "Solar power forecast contains negative values."
        )

    if (
        (df["solar_power_kw_p10"] > config.SOLAR_CAPACITY_KW).any()
        or (df["solar_power_kw_p50"] > config.SOLAR_CAPACITY_KW).any()
        or (df["solar_power_kw_p90"] > config.SOLAR_CAPACITY_KW).any()
    ):
        raise ForecastValidationError(
            "Solar power forecast exceeds configured solar capacity."
        )

    # Wind generation must remain within installed capacity.
    if (
        (df["wind_power_kw_p10"] < 0).any()
        or (df["wind_power_kw_p50"] < 0).any()
        or (df["wind_power_kw_p90"] < 0).any()
    ):
        raise ForecastValidationError(
            "Wind power forecast contains negative values."
        )

    if (
        (df["wind_power_kw_p10"] > config.WIND_CAPACITY_KW).any()
        or (df["wind_power_kw_p50"] > config.WIND_CAPACITY_KW).any()
        or (df["wind_power_kw_p90"] > config.WIND_CAPACITY_KW).any()
    ):
        raise ForecastValidationError(
            "Wind power forecast exceeds configured wind capacity."
        )

    # Physical load components must be non-negative.
    #
    # IMPORTANT:
    # net_load_kw_p50 is intentionally NOT included here.
    # Net load can legitimately be negative when renewable generation
    # exceeds station demand.
    non_negative_load_columns = [
        "electrical_load_kw",
        "heating_load_kw_p50",
        "total_load_kw_p10",
        "total_load_kw_p50",
        "total_load_kw_p90",
    ]

    for column in non_negative_load_columns:
        if (df[column] < 0).any():
            raise ForecastValidationError(
                f"Load forecast '{column}' contains negative values."
            )


def _validate_net_load_identity(
    df: pd.DataFrame,
) -> None:
    """
    Validate:

        net_load = total_load - solar_power - wind_power
    """

    expected_net_load = (
        df["total_load_kw_p50"]
        - df["solar_power_kw_p50"]
        - df["wind_power_kw_p50"]
    )

    actual_net_load = df["net_load_kw_p50"]

    if not np.allclose(
        actual_net_load.to_numpy(dtype=float),
        expected_net_load.to_numpy(dtype=float),
        atol=0.05,
        rtol=0.0,
    ):
        raise ForecastValidationError(
            "Forecast violates net-load identity: "
            "net_load_kw_p50 must equal "
            "total_load_kw_p50 - solar_power_kw_p50 - wind_power_kw_p50."
        )


def _validate_timestamps(
    df: pd.DataFrame,
) -> None:
    """Validate forecast timestamps."""

    timestamps = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True,
    )

    if timestamps.isna().any():
        raise ForecastValidationError(
            "Forecast contains invalid timestamp values."
        )

    if not timestamps.is_monotonic_increasing:
        raise ForecastValidationError(
            "Forecast timestamps must be monotonically increasing."
        )


def _validate_risk_flags(
    df: pd.DataFrame,
) -> None:
    """Validate risk flag fields."""

    for column in [
        "storm_risk_flag",
        "turbine_cutout_risk",
    ]:
        values = df[column]

        for value in values:
            if not isinstance(value, (bool, np.bool_)):
                raise ForecastValidationError(
                    f"Forecast column '{column}' must contain boolean values."
                )


def _validate_confidence(
    df: pd.DataFrame,
) -> None:
    """Validate confidence score range."""

    if (
        (df["confidence_score"] < 0).any()
        or (df["confidence_score"] > 1).any()
    ):
        raise ForecastValidationError(
            "Forecast confidence_score must be between 0 and 1."
        )


def _validate_forecast_mode(
    df: pd.DataFrame,
) -> None:
    """Validate forecast mode values."""

    modes = set(df["forecast_mode"].dropna().unique())

    invalid_modes = modes - VALID_FORECAST_MODES

    if invalid_modes:
        raise ForecastValidationError(
            f"Forecast contains unsupported forecast_mode value(s): "
            f"{sorted(invalid_modes)}"
        )


# ---------------------------------------------------------------------------
# Public forecast validator
# ---------------------------------------------------------------------------

def validate_forecast_output(
    forecast: pd.DataFrame,
) -> pd.DataFrame:
    """
    Validate a ForecastService output DataFrame.

    The function does not modify the input DataFrame.

    Returns
    -------
    pandas.DataFrame
        The original validated DataFrame.
    """

    if not isinstance(forecast, pd.DataFrame):
        raise ForecastValidationError(
            "Forecast output must be a pandas DataFrame."
        )

    if forecast.empty:
        raise ForecastValidationError(
            "Forecast output must contain at least one row."
        )

    df = forecast.copy()

    # Contract schema
    _require_columns(
        df,
        EXPECTED_CONTRACT_COLUMNS,
    )

    # Basic structure
    _validate_timestamps(df)
    _validate_numeric_columns(df)
    _validate_step_sequence(df)

    # Probabilistic forecast correctness
    _validate_quantile_monotonicity(df)

    # Physical constraints
    _validate_physical_limits(df)

    # Energy-balance identity
    _validate_net_load_identity(df)

    # Risk and confidence metadata
    _validate_risk_flags(df)
    _validate_confidence(df)
    _validate_forecast_mode(df)

    return forecast


# ---------------------------------------------------------------------------
# Weather input compatibility
# ---------------------------------------------------------------------------

def normalize_weather_columns(
    weather_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalize Member 1 / Member 2 weather column aliases
    into the canonical forecasting names.

    Supported aliases:

        timestamp_utc          -> timestamp
        solar_irradiance_wm2   -> irradiance_w_m2
        wind_speed_mps         -> wind_speed_ms
    """

    if not isinstance(weather_df, pd.DataFrame):
        raise ValueError(
            "Weather input must be a pandas DataFrame."
        )

    df = weather_df.copy()

    rename_map = {}

    for source, target in WEATHER_ALIASES.items():
        if source in df.columns and target not in df.columns:
            rename_map[source] = target

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


def validate_weather_input(
    weather_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Validate and normalize weather input required by forecasting.

    Required canonical fields:

        timestamp
        temperature_c
        irradiance_w_m2
        wind_speed_ms
    """

    df = normalize_weather_columns(weather_df)

    missing = [
        column
        for column in CANONICAL_WEATHER_FIELDS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Weather input is missing required column(s): {missing}"
        )

    timestamps = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True,
    )

    if timestamps.isna().any():
        raise ValueError(
            "Weather input contains invalid timestamp values."
        )

    numeric_columns = [
        "temperature_c",
        "irradiance_w_m2",
        "wind_speed_ms",
    ]

    for column in numeric_columns:
        values = pd.to_numeric(
            df[column],
            errors="coerce",
        )

        if values.isna().any():
            raise ValueError(
                f"Weather input column '{column}' contains "
                "non-numeric or NaN values."
            )

        if not np.isfinite(
            values.to_numpy(dtype=float)
        ).all():
            raise ValueError(
                f"Weather input column '{column}' contains "
                "non-finite values."
            )

    # Physical weather constraints from Member 1's weather loader.
    if (df["irradiance_w_m2"] < 0).any():
        raise ValueError(
            "Weather irradiance cannot be negative."
        )

    if (df["wind_speed_ms"] < 0).any():
        raise ValueError(
            "Weather wind speed cannot be negative."
        )

    if (
        (df["temperature_c"] < -90.0).any()
        or (df["temperature_c"] > 60.0).any()
    ):
        raise ValueError(
            "Weather temperature must remain within "
            "the supported range of -90°C to 60°C."
        )

    if not timestamps.is_monotonic_increasing:
        raise ValueError(
            "Weather timestamps must be monotonically increasing."
        )

    return df