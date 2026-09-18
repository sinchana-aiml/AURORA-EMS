# src/forecasting/__init__.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Forecasting Module
# Member 3: Renewable Energy & Station Load Forecasting
#
# Foundation package providing deterministic data preprocessing,
# feature engineering, target generation using Member 1 physics,
# and chronological split preparation.
# ─────────────────────────────────────────────────────────────────────────────

from .preprocessor import (
    load_and_prepare_dataset,
    compute_ground_truth_targets,
    create_chronological_splits,
    validate_preprocessed_data,
    TARGET_COLUMNS,
    TARGET_PHYSICAL_LIMITS,
)
from .features import (
    build_features,
    compute_solar_geometry,
    add_calendar_features,
    add_weather_change_rates,
    add_lag_features,
    add_rolling_features,
    FEATURE_COLUMNS,
)

__all__ = [
    "load_and_prepare_dataset",
    "compute_ground_truth_targets",
    "create_chronological_splits",
    "validate_preprocessed_data",
    "TARGET_COLUMNS",
    "TARGET_PHYSICAL_LIMITS",
    "build_features",
    "compute_solar_geometry",
    "add_calendar_features",
    "add_weather_change_rates",
    "add_lag_features",
    "add_rolling_features",
    "FEATURE_COLUMNS",
]
