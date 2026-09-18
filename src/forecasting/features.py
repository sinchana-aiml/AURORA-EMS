# src/forecasting/features.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Feature Engineering Engine
# Member 3: Renewable Energy & Station Load Forecasting
#
# Generates deterministic, physically grounded features for polar forecasting:
# - Calendar & Cyclical temporal representations
# - Astronomical solar geometry for Bharati Station (-69.4069° N, 76.1956° E)
# - Backward-looking weather rate-of-change indicators
# - Strictly causal lag features (t - k)
# - Backward-looking rolling statistics (mean, std, min, max)
#
# GUARANTEE: Zero target leakage. Future observations are NEVER consumed to
# construct features for a prediction timestamp.
# ─────────────────────────────────────────────────────────────────────────────

import numpy as np
import pandas as pd
from typing import List, Optional, Tuple, Sequence

# Station Coordinates (Bharati Station, Larsemann Hills, Antarctica)
BHARATI_LATITUDE = -69.4069
BHARATI_LONGITUDE = 76.1956

# Standard lag horizons in hours
DEFAULT_LAGS: Tuple[int, ...] = (1, 2, 3, 6, 12, 24, 48)

# Standard rolling window horizons in hours
DEFAULT_ROLLING_WINDOWS: Tuple[int, ...] = (6, 24)

# Weather variables suitable for lag and rolling calculations
WEATHER_FEATURE_COLS: Tuple[str, ...] = (
    "temperature_c",
    "wind_speed_ms",
    "irradiance_w_m2",
    "surface_pressure_kpa",
    "precipitation_mm",
)


def compute_solar_geometry(
    timestamps: Sequence[pd.Timestamp],
    latitude_deg: float = BHARATI_LATITUDE,
    longitude_deg: float = BHARATI_LONGITUDE,
) -> pd.DataFrame:
    """
    Computes rigorous astronomical solar geometry for polar coordinates.

    Because Bharati Station is at -69.4° S (inside the Antarctic Circle),
    polar night (24h darkness in winter) and polar day (midnight sun in summer)
    strongly govern solar PV potential.

    Formulas:
    ---------
    - Day of year (1-366) and fractional year angle gamma.
    - Solar declination (delta) via astronomical approximation.
    - Solar hour angle (omega) adjusted for local station longitude.
    - Solar elevation angle: sin(alpha) = sin(lat)*sin(delta) + cos(lat)*cos(delta)*cos(omega).
    - Solar zenith angle: theta_z = 90° - alpha.

    Parameters:
    -----------
    timestamps : Sequence of pandas Timestamps (UTC-aware or naive UTC).
    latitude_deg : float, Station latitude in degrees.
    longitude_deg : float, Station longitude in degrees.

    Returns:
    --------
    pd.DataFrame with columns:
      - solar_elevation_deg: Solar elevation angle in degrees (-90 to +90)
      - solar_zenith_deg: Solar zenith angle in degrees (0 to 180)
      - sun_above_horizon: Binary indicator (1 if elevation > 0, else 0)
      - extraterrestrial_irradiance_proxy: Theoretical clear-sky geometric index
      - is_polar_day: 1 if sun stays above horizon throughout day-of-year
      - is_polar_night: 1 if sun never rises on that day-of-year
    """
    ts = pd.Series(pd.to_datetime(timestamps, utc=True))
    doy = ts.dt.dayofyear.to_numpy()
    hour = ts.dt.hour.to_numpy() + ts.dt.minute.to_numpy() / 60.0

    # Latitude in radians
    lat_rad = np.radians(latitude_deg)

    # Fractional year angle in radians
    gamma = 2.0 * np.pi * (doy - 1 + (hour - 12.0) / 24.0) / 365.25

    # Solar declination angle in radians (Spencer / NOAA approximation)
    declination_rad = (
        0.006918
        - 0.399912 * np.cos(gamma)
        + 0.070257 * np.sin(gamma)
        - 0.006758 * np.cos(2.0 * gamma)
        + 0.000907 * np.sin(2.0 * gamma)
        - 0.002697 * np.cos(3.0 * gamma)
        + 0.001480 * np.sin(3.0 * gamma)
    )

    # Equation of time in minutes
    eqtime_min = 229.18 * (
        0.000075
        + 0.001868 * np.cos(gamma)
        - 0.032077 * np.sin(gamma)
        - 0.014615 * np.cos(2.0 * gamma)
        - 0.040849 * np.sin(2.0 * gamma)
    )

    # True solar time in minutes
    solar_time_offset_min = 4.0 * longitude_deg + eqtime_min
    tst_min = (hour * 60.0 + solar_time_offset_min) % 1440.0

    # Solar hour angle in radians
    hour_angle_rad = np.radians((tst_min / 4.0) - 180.0)

    # Sine of solar elevation angle
    sin_elevation = (
        np.sin(lat_rad) * np.sin(declination_rad)
        + np.cos(lat_rad) * np.cos(declination_rad) * np.cos(hour_angle_rad)
    )
    sin_elevation = np.clip(sin_elevation, -1.0, 1.0)
    elevation_rad = np.arcsin(sin_elevation)
    elevation_deg = np.degrees(elevation_rad)

    # Zenith angle in degrees
    zenith_deg = 90.0 - elevation_deg

    # Extraterrestrial irradiance geometric factor (solar constant 1361 W/m2 * max(0, sin(alpha)))
    # Accounts for annual variation in Earth-Sun distance (eccentricity)
    eccentricity_factor = 1.0 + 0.033 * np.cos(2.0 * np.pi * doy / 365.25)
    solar_constant = 1361.0  # W/m2
    extra_irr = np.maximum(0.0, sin_elevation) * solar_constant * eccentricity_factor

    # Polar day and polar night indicators:
    # At polar latitude, midnight sun occurs when min solar elevation > 0
    # Polar night occurs when max solar elevation <= 0
    # Minimum daily elevation occurs at hour_angle = pi (midnight solar time)
    # Maximum daily elevation occurs at hour_angle = 0 (solar noon)
    sin_noon_elevation = np.sin(lat_rad) * np.sin(declination_rad) + np.cos(lat_rad) * np.cos(declination_rad)
    sin_midnight_elevation = np.sin(lat_rad) * np.sin(declination_rad) - np.cos(lat_rad) * np.cos(declination_rad)

    is_polar_day = (sin_midnight_elevation > 0).astype(int)
    is_polar_night = (sin_noon_elevation <= 0).astype(int)
    sun_above_horizon = (elevation_deg > 0.0).astype(int)

    return pd.DataFrame(
        {
            "solar_elevation_deg": np.round(elevation_deg, 4),
            "solar_zenith_deg": np.round(zenith_deg, 4),
            "sun_above_horizon": sun_above_horizon,
            "extraterrestrial_irradiance_proxy": np.round(extra_irr, 4),
            "is_polar_day": is_polar_day,
            "is_polar_night": is_polar_night,
        }
    )


def add_calendar_features(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
) -> pd.DataFrame:
    """
    Extracts calendar and continuous cyclical sinusoidal representations.

    Cyclical encodings prevent artificial discontinuity between hour 23 and hour 0,
    and between day 365 and day 1.
    """
    out = df.copy()
    ts = pd.to_datetime(out[timestamp_col], utc=True)

    out["hour"] = ts.dt.hour
    out["day_of_week"] = ts.dt.dayofweek
    out["month"] = ts.dt.month
    out["day_of_year"] = ts.dt.dayofyear

    # Cyclical hour features (period = 24)
    out["hour_sin"] = np.round(np.sin(2.0 * np.pi * out["hour"] / 24.0), 6)
    out["hour_cos"] = np.round(np.cos(2.0 * np.pi * out["hour"] / 24.0), 6)

    # Cyclical day-of-year features (period = 365.25)
    out["doy_sin"] = np.round(np.sin(2.0 * np.pi * (out["day_of_year"] - 1) / 365.25), 6)
    out["doy_cos"] = np.round(np.cos(2.0 * np.pi * (out["day_of_year"] - 1) / 365.25), 6)

    return out


def add_weather_change_rates(
    df: pd.DataFrame,
    cols: Optional[Sequence[str]] = None,
    periods: Sequence[int] = (1, 3),
) -> pd.DataFrame:
    """
    Computes backward-looking rate-of-change (deltas) for weather variables.

    Rapid barometric pressure drops (pressure tendency) and temperature plunges
    are classic precursors of severe Antarctic katabatic and blizzard storms.

    Guarantees no future leakage: delta = value(t) - value(t - p).
    """
    out = df.copy()
    if cols is None:
        target_candidates = ["temperature_c", "wind_speed_ms", "surface_pressure_kpa"]
        cols = [c for c in target_candidates if c in out.columns]

    for col in cols:
        for p in periods:
            col_name = f"{col}_diff_{p}h"
            out[col_name] = np.round(out[col].diff(periods=p), 4)

    return out


def add_lag_features(
    df: pd.DataFrame,
    cols: Optional[Sequence[str]] = None,
    lags: Sequence[int] = DEFAULT_LAGS,
) -> pd.DataFrame:
    """
    Creates strictly causal lag features from historical observations:
      feature_lag_k(t) = feature(t - k)

    Negative shift is NEVER used. Guarantees zero look-ahead bias.
    """
    out = df.copy()
    if cols is None:
        target_candidates = list(WEATHER_FEATURE_COLS)
        cols = [c for c in target_candidates if c in out.columns]

    for col in cols:
        for k in lags:
            col_name = f"{col}_lag_{k}h"
            out[col_name] = out[col].shift(k)

    return out


def add_rolling_features(
    df: pd.DataFrame,
    cols: Optional[Sequence[str]] = None,
    windows: Sequence[int] = DEFAULT_ROLLING_WINDOWS,
    min_periods: int = 1,
) -> pd.DataFrame:
    """
    Computes backward-looking rolling statistics (mean, std, min, max).

    CRITICAL LEAKAGE PREVENTION:
    Rolling calculations use only historical observations [t - W + 1, t]
    via pandas standard rolling with closed='right' (the default) or
    shifted history. For strictly causal prediction where origin is t,
    the current observation at t is the latest available.
    """
    out = df.copy()
    if cols is None:
        target_candidates = ["temperature_c", "wind_speed_ms", "irradiance_w_m2"]
        cols = [c for c in target_candidates if c in out.columns]

    for col in cols:
        for w in windows:
            roll = out[col].rolling(window=w, min_periods=min_periods)
            out[f"{col}_rolling_mean_{w}h"] = np.round(roll.mean(), 4)
            out[f"{col}_rolling_std_{w}h"] = np.round(roll.std().fillna(0.0), 4)
            out[f"{col}_rolling_min_{w}h"] = np.round(roll.min(), 4)
            out[f"{col}_rolling_max_{w}h"] = np.round(roll.max(), 4)

    return out


def build_features(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
    include_lags: bool = True,
    include_rolling: bool = True,
    include_change_rates: bool = True,
    drop_na: bool = False,
) -> pd.DataFrame:
    """
    Master feature engineering pipeline.

    Combines:
    1. Calendar & Cyclical time encodings.
    2. Polar solar geometry for Bharati Station.
    3. Weather change-rate features.
    4. Causal historical lags.
    5. Causal rolling statistics.

    Parameters:
    -----------
    df : pd.DataFrame
        Preprocessed weather DataFrame (with standardized columns).
    timestamp_col : str
        Column name containing timestamps.
    include_lags : bool
        Whether to generate lag features.
    include_rolling : bool
        Whether to generate rolling statistic features.
    include_change_rates : bool
        Whether to generate delta change features.
    drop_na : bool
        If True, drops initial warm-up rows (e.g. first 48h) containing NaNs.

    Returns:
    --------
    pd.DataFrame with all feature columns added deterministically.
    """
    out = df.copy()

    # 1. Calendar & Cyclical features
    out = add_calendar_features(out, timestamp_col=timestamp_col)

    # 2. Polar Solar geometry
    solar_df = compute_solar_geometry(
        out[timestamp_col],
        latitude_deg=BHARATI_LATITUDE,
        longitude_deg=BHARATI_LONGITUDE,
    )
    for col in solar_df.columns:
        out[col] = solar_df[col].values

    # 3. Weather change rates
    if include_change_rates:
        out = add_weather_change_rates(out)

    # 4. Causal lags
    if include_lags:
        out = add_lag_features(out)

    # 5. Causal rolling statistics
    if include_rolling:
        out = add_rolling_features(out)

    if drop_na:
        out = out.dropna().reset_index(drop=True)

    return out


def get_feature_column_names(
    include_lags: bool = True,
    include_rolling: bool = True,
    include_change_rates: bool = True,
) -> List[str]:
    """
    Returns the deterministic ordered list of feature column names produced by
    the build_features pipeline (excluding targets and raw identifiers).
    """
    cols: List[str] = [
        # Calendar & Cyclical
        "hour",
        "day_of_week",
        "month",
        "day_of_year",
        "hour_sin",
        "hour_cos",
        "doy_sin",
        "doy_cos",
        # Solar Geometry
        "solar_elevation_deg",
        "solar_zenith_deg",
        "sun_above_horizon",
        "extraterrestrial_irradiance_proxy",
        "is_polar_day",
        "is_polar_night",
        # Raw instantaneous weather
        "temperature_c",
        "wind_speed_ms",
        "irradiance_w_m2",
        "surface_pressure_kpa",
        "precipitation_mm",
    ]

    if include_change_rates:
        for var in ["temperature_c", "wind_speed_ms", "surface_pressure_kpa"]:
            for p in (1, 3):
                cols.append(f"{var}_diff_{p}h")

    if include_lags:
        for var in WEATHER_FEATURE_COLS:
            for k in DEFAULT_LAGS:
                cols.append(f"{var}_lag_{k}h")

    if include_rolling:
        for var in ["temperature_c", "wind_speed_ms", "irradiance_w_m2"]:
            for w in DEFAULT_ROLLING_WINDOWS:
                cols.extend([
                    f"{var}_rolling_mean_{w}h",
                    f"{var}_rolling_std_{w}h",
                    f"{var}_rolling_min_{w}h",
                    f"{var}_rolling_max_{w}h",
                ])

    return cols


FEATURE_COLUMNS = get_feature_column_names()
