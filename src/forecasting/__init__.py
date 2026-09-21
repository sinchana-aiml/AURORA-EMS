# src/forecasting/__init__.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Forecasting Module
# Member 3: Renewable Energy & Station Load Forecasting
#
# Production forecasting package providing:
#   - Preprocessing and Member 1 physics target generation
#   - Deterministic feature engineering and solar geometry
#   - Quantile Gradient Boosting regressors (P10, P50, P90)
#   - Station-level coordination (AuroraForecastingSystem)
#   - Offline polar climatology and persistence fallbacks
#   - Comprehensive evaluation metrics
#   - Production inference service & Member 4 interface (ForecastService)
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
    get_feature_column_names,
)
from .models import (
    QuantileGradientBoostingForecaster,
    AuroraForecastingSystem,
    HAS_SKLEARN,
)
from .fallback import (
    PolarClimatologyForecaster,
    PersistenceForecaster,
)
from .evaluation import (
    evaluate_forecast,
    mean_absolute_error,
    root_mean_squared_error,
    normalized_rmse,
    r2_score,
    pinball_loss,
    prediction_interval_coverage,
    mean_prediction_interval_width,
)
from .service import (
    ForecastService,
    get_forecast,
)

__all__ = [
    # Preprocessing
    "load_and_prepare_dataset",
    "compute_ground_truth_targets",
    "create_chronological_splits",
    "validate_preprocessed_data",
    "TARGET_COLUMNS",
    "TARGET_PHYSICAL_LIMITS",
    # Features
    "build_features",
    "compute_solar_geometry",
    "add_calendar_features",
    "add_weather_change_rates",
    "add_lag_features",
    "add_rolling_features",
    "FEATURE_COLUMNS",
    "get_feature_column_names",
    # Models
    "QuantileGradientBoostingForecaster",
    "AuroraForecastingSystem",
    "HAS_SKLEARN",
    # Fallback
    "PolarClimatologyForecaster",
    "PersistenceForecaster",
    # Evaluation
    "evaluate_forecast",
    "mean_absolute_error",
    "root_mean_squared_error",
    "normalized_rmse",
    "r2_score",
    "pinball_loss",
    "prediction_interval_coverage",
    "mean_prediction_interval_width",
    # Production Service / Member 4 Interface
    "ForecastService",
    "get_forecast",
]
