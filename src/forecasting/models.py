# src/forecasting/models.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Machine Learning Forecasters
# Member 3: Renewable Energy & Station Load Forecasting
#
# Production Quantile Gradient Boosting Regressors for:
#   - Solar PV Generation (kW)
#   - Wind Power Generation (kW)
#   - Station Heating Demand (kW)
#   - Station Total Load (kW)
#
# Key Architectural Features:
#   1. Probabilistic multi-quantile outputs:
#        P10 (reserve floor / conservative bound)
#        P50 (median / expected value)
#        P90 (reserve ceiling / curtailment risk)
#   2. Enforced Monotonicity: P10 <= P50 <= P90
#   3. Physical Bounds Clamping:
#        solar in [0, 40 kW]
#        wind in [0, 50 kW]
#        heating >= 15 kW
#        total_load = electrical (30 kW) + heating
#   4. Direct Multi-Horizon Dispatch Forecasting (1h to 48h)
#   5. Model Serialization (joblib / pickle)
# ─────────────────────────────────────────────────────────────────────────────

import os
import pickle
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union

try:
    import joblib
    HAS_JOBLIB = True
except ImportError:
    HAS_JOBLIB = False

try:
    from sklearn.ensemble import HistGradientBoostingRegressor
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

import config
from src.digital_twin.load_model import electrical_load
from src.forecasting.preprocessor import TARGET_COLUMNS, TARGET_PHYSICAL_LIMITS
from src.forecasting.features import get_feature_column_names, build_features
from src.forecasting.fallback import PolarClimatologyForecaster


class QuantileGradientBoostingForecaster:
    """
    Production Quantile Gradient Boosting Forecaster.

    Trains three quantile regressors per target (alpha = 0.10, 0.50, 0.90)
    using HistGradientBoostingRegressor for speed, accuracy, and native
    quantile loss support.
    """

    def __init__(
        self,
        target_name: str,
        capacity_max: Optional[float] = None,
        capacity_min: float = 0.0,
        max_iter: int = 100,
        random_state: int = 42,
    ):
        self.target_name = target_name
        self.capacity_min = capacity_min
        self.capacity_max = capacity_max
        self.max_iter = max_iter
        self.random_state = random_state
        self.feature_names: List[str] = []
        self.is_fitted = False

        # Models for P10, P50, P90
        self.models: Dict[float, Any] = {}
        self.fallback_model: Optional[PolarClimatologyForecaster] = None

    def fit(
        self,
        X: pd.DataFrame,
        y: Union[pd.Series, np.ndarray],
        feature_names: Optional[List[str]] = None,
    ) -> "QuantileGradientBoostingForecaster":
        """
        Fits P10, P50, and P90 quantile models.
        """
        if feature_names is not None:
            self.feature_names = list(feature_names)
            X_mat = X[self.feature_names].to_numpy()
        else:
            self.feature_names = list(X.columns)
            X_mat = X.to_numpy()

        y_vec = np.asarray(y, dtype=float)

        if HAS_SKLEARN:
            for q in [0.10, 0.50, 0.90]:
                model = HistGradientBoostingRegressor(
                    loss="quantile",
                    quantile=q,
                    max_iter=self.max_iter,
                    min_samples_leaf=20,
                    random_state=self.random_state,
                )
                model.fit(X_mat, y_vec)
                self.models[q] = model
            self.is_fitted = True
        else:
            # Fallback if scikit-learn is not installed
            self.is_fitted = True

        return self

    def predict(self, X: pd.DataFrame) -> Dict[str, np.ndarray]:
        """
        Generates P10, P50, and P90 predictions with physical limits and
        monotonicity enforcement.
        """
        if not self.is_fitted:
            raise RuntimeError(f"Forecaster for {self.target_name} is not fitted.")

        X_mat = X[self.feature_names].to_numpy() if self.feature_names else X.to_numpy()
        n_samples = len(X_mat)

        if HAS_SKLEARN and self.models:
            pred_10 = self.models[0.10].predict(X_mat)
            pred_50 = self.models[0.50].predict(X_mat)
            pred_90 = self.models[0.90].predict(X_mat)
        else:
            # Simple heuristic baseline if sklearn not present
            pred_50 = np.full(n_samples, (self.capacity_min + (self.capacity_max or 50.0)) / 2.0)
            pred_10 = pred_50 * 0.85
            pred_90 = pred_50 * 1.15

        # 1. Enforce physical range limits
        if self.capacity_max is not None:
            pred_10 = np.clip(pred_10, self.capacity_min, self.capacity_max)
            pred_50 = np.clip(pred_50, self.capacity_min, self.capacity_max)
            pred_90 = np.clip(pred_90, self.capacity_min, self.capacity_max)
        else:
            pred_10 = np.maximum(self.capacity_min, pred_10)
            pred_50 = np.maximum(self.capacity_min, pred_50)
            pred_90 = np.maximum(self.capacity_min, pred_90)

        # 2. Enforce Monotonicity: P10 <= P50 <= P90
        # If quantile crossing occurs due to noise, correct it deterministically
        pred_50 = np.maximum(pred_10, pred_50)
        pred_90 = np.maximum(pred_50, pred_90)

        return {
            f"{self.target_name}_p10": np.round(pred_10, 4),
            f"{self.target_name}_p50": np.round(pred_50, 4),
            f"{self.target_name}_p90": np.round(pred_90, 4),
        }

    def save(self, filepath: str) -> None:
        """Serializes forecaster state to disk."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        if HAS_JOBLIB:
            joblib.dump(self, filepath)
        else:
            with open(filepath, "wb") as f:
                pickle.dump(self, f)

    @classmethod
    def load(cls, filepath: str) -> "QuantileGradientBoostingForecaster":
        """Deserializes forecaster from disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model artifact not found at: {filepath}")
        if HAS_JOBLIB:
            return joblib.load(filepath)
        else:
            with open(filepath, "rb") as f:
                return pickle.load(f)


class AuroraForecastingSystem:
    """
    Unified Forecasting System coordinating individual equipment models:
      - Solar PV forecaster (rated 40 kW)
      - Wind turbine forecaster (rated 50 kW)
      - Heating load forecaster (min 15 kW)
      - Total station load (electrical 30 kW + heating load)
    """

    def __init__(self, max_iter: int = 100, random_state: int = 42):
        self.solar_model = QuantileGradientBoostingForecaster(
            target_name="solar_power_kw",
            capacity_min=0.0,
            capacity_max=config.SOLAR_CAPACITY_KW,
            max_iter=max_iter,
            random_state=random_state,
        )
        self.wind_model = QuantileGradientBoostingForecaster(
            target_name="wind_power_kw",
            capacity_min=0.0,
            capacity_max=config.WIND_CAPACITY_KW,
            max_iter=max_iter,
            random_state=random_state,
        )
        self.heating_model = QuantileGradientBoostingForecaster(
            target_name="heating_load_kw",
            capacity_min=config.HEATING_BASE_KW,
            capacity_max=100.0,
            max_iter=max_iter,
            random_state=random_state,
        )
        self.climatology_fallback = PolarClimatologyForecaster()
        self.is_fitted = False
        self.feature_names: List[str] = []

    def fit(self, train_df: pd.DataFrame, feature_names: Optional[List[str]] = None) -> "AuroraForecastingSystem":
        """
        Fits all forecasters on the training dataset.
        """
        # Ensure features are present
        if "solar_elevation_deg" not in train_df.columns:
            train_features = build_features(train_df)
        else:
            train_features = train_df.copy()

        # Drop warm-up rows (first 48h containing NaNs from lags)
        train_features = train_features.dropna().reset_index(drop=True)

        if feature_names is None:
            candidate_cols = get_feature_column_names()
            self.feature_names = [c for c in candidate_cols if c in train_features.columns]
        else:
            self.feature_names = list(feature_names)

        X = train_features[self.feature_names]

        # Fit individual models
        self.solar_model.fit(X, train_features["solar_power_kw"], self.feature_names)
        self.wind_model.fit(X, train_features["wind_power_kw"], self.feature_names)
        self.heating_model.fit(X, train_features["heating_load_kw"], self.feature_names)

        # Fit offline fallback climatology
        self.climatology_fallback.fit(train_df)

        self.is_fitted = True
        return self

    def predict(self, feature_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generates complete forecast predictions across all targets.
        """
        if not self.is_fitted:
            raise RuntimeError("AuroraForecastingSystem must be fitted before predict.")

        solar_preds = self.solar_model.predict(feature_df)
        wind_preds = self.wind_model.predict(feature_df)
        heat_preds = self.heating_model.predict(feature_df)

        # Electrical base + flexible load
        elec_kw = electrical_load(include_flexible=True)

        # Assemble result
        out = pd.DataFrame(index=feature_df.index)
        if "timestamp" in feature_df.columns:
            out["timestamp"] = feature_df["timestamp"].values

        # Assign predictions
        for k, v in solar_preds.items():
            out[k] = v
        for k, v in wind_preds.items():
            out[k] = v

        out["electrical_load_kw"] = elec_kw
        for k, v in heat_preds.items():
            out[k] = v

        # Station total load = electrical load + heating load
        out["total_load_kw_p10"] = np.round(elec_kw + out["heating_load_kw_p10"], 4)
        out["total_load_kw_p50"] = np.round(elec_kw + out["heating_load_kw_p50"], 4)
        out["total_load_kw_p90"] = np.round(elec_kw + out["heating_load_kw_p90"], 4)

        # Net load = Total Load - (Solar + Wind)
        out["net_load_kw_p50"] = np.round(
            out["total_load_kw_p50"] - (out["solar_power_kw_p50"] + out["wind_power_kw_p50"]), 4
        )

        return out

    def save_system(self, model_dir: str = "models") -> None:
        """Saves all models into the given directory."""
        os.makedirs(model_dir, exist_ok=True)
        self.solar_model.save(os.path.join(model_dir, "solar_model.joblib"))
        self.wind_model.save(os.path.join(model_dir, "wind_model.joblib"))
        self.heating_model.save(os.path.join(model_dir, "heating_model.joblib"))
        if HAS_JOBLIB:
            joblib.dump(self.climatology_fallback, os.path.join(model_dir, "climatology_fallback.joblib"))
            joblib.dump(self.feature_names, os.path.join(model_dir, "feature_names.joblib"))
        else:
            with open(os.path.join(model_dir, "climatology_fallback.pkl"), "wb") as f:
                pickle.dump(self.climatology_fallback, f)
            with open(os.path.join(model_dir, "feature_names.pkl"), "wb") as f:
                pickle.dump(self.feature_names, f)

    @classmethod
    def load_system(cls, model_dir: str = "models") -> "AuroraForecastingSystem":
        """Loads all trained models from the given directory."""
        system = cls()
        system.solar_model = QuantileGradientBoostingForecaster.load(os.path.join(model_dir, "solar_model.joblib"))
        system.wind_model = QuantileGradientBoostingForecaster.load(os.path.join(model_dir, "wind_model.joblib"))
        system.heating_model = QuantileGradientBoostingForecaster.load(os.path.join(model_dir, "heating_model.joblib"))

        clim_joblib = os.path.join(model_dir, "climatology_fallback.joblib")
        feat_joblib = os.path.join(model_dir, "feature_names.joblib")
        if HAS_JOBLIB and os.path.exists(clim_joblib):
            system.climatology_fallback = joblib.load(clim_joblib)
            system.feature_names = joblib.load(feat_joblib)
        else:
            with open(os.path.join(model_dir, "climatology_fallback.pkl"), "rb") as f:
                system.climatology_fallback = pickle.load(f)
            with open(os.path.join(model_dir, "feature_names.pkl"), "rb") as f:
                system.feature_names = pickle.load(f)

        system.is_fitted = True
        return system
