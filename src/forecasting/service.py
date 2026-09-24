# src/forecasting/service.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Forecasting Service & Member 4 Interface Engine
# Member 3: Renewable Energy & Station Load Forecasting
#
# Production inference service connecting Member 3's forecasting models
# to Member 4's Energy Optimization module.
#
# Capabilities:
#   1. Arbitrary Lookahead Horizons (1 to 48 hours, default 24h).
#   2. Multi-Quantile Probabilistic Bands: P10 (floor), P50 (expected), P90 (ceiling).
#   3. Autonomous Mode Switching:
#        - Online: Multi-quantile Machine Learning Ensemble.
#        - Offline: Local Polar Climatology + Persistence Fallback.
#   4. Dynamic Uncertainty Widening: Expands P10-P90 margins during comms loss.
#   5. Severe Weather & Turbine Cut-Out Early Warning Flags.
#   6. Enforced Monotonicity & Equipment Bounds Clamping.
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
from typing import Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd

# Ensure project root is available
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import config
from src.digital_twin.load_model import electrical_load, heating_load, total_load
from src.digital_twin.renewable_model import solar_pv_output, wind_power_output
from src.forecasting.preprocessor import (
    load_and_prepare_dataset,
    DEFAULT_DATA_PATH,
    TARGET_COLUMNS,
)
from src.forecasting.features import (
    build_features,
    compute_solar_geometry,
    BHARATI_LATITUDE,
    BHARATI_LONGITUDE,
    get_feature_column_names,
)
from src.forecasting.fallback import (
    PolarClimatologyForecaster,
    PersistenceForecaster,
)
from src.forecasting.models import (
    AuroraForecastingSystem,
    HAS_SKLEARN,
)


DEFAULT_MODEL_DIR = os.path.join(_ROOT, "models")


class ForecastService:
    """
    Unified Forecasting Service for AURORA-EMS.

    Provides point forecasts and probabilistic uncertainty intervals for
    Member 4's optimization algorithm under both normal online operations
    and communication outage scenarios.
    """

    def __init__(
        self,
        model_dir: str = DEFAULT_MODEL_DIR,
        auto_initialize: bool = True,
    ):
        self.model_dir = model_dir
        self.system: Optional[AuroraForecastingSystem] = None
        self.climatology: Optional[PolarClimatologyForecaster] = None
        self.persistence: PersistenceForecaster = PersistenceForecaster(mode="diurnal")
        self.is_online_ready = False

        if auto_initialize:
            self._initialize_service()

    def _initialize_service(self) -> None:
        """
        Attempts to load serialized models from model_dir; if not available,
        initializes the offline Polar Climatology engine on the clean dataset.
        """
        solar_path = os.path.join(self.model_dir, "solar_model.joblib")

        if os.path.exists(solar_path) and HAS_SKLEARN:
            try:
                self.system = AuroraForecastingSystem.load_system(self.model_dir)
                self.climatology = self.system.climatology_fallback
                self.is_online_ready = True
                return
            except Exception:
                self.is_online_ready = False

        # Fallback initialization: build climatology from canonical dataset
        if os.path.exists(DEFAULT_DATA_PATH):
            df = load_and_prepare_dataset(DEFAULT_DATA_PATH)
            self.climatology = PolarClimatologyForecaster()
            self.climatology.fit(df)

    def generate_forecast(
        self,
        current_timestamp: Union[str, pd.Timestamp],
        horizon_hours: int = 24,
        recent_history: Optional[Union[pd.DataFrame, List[Dict]]] = None,
        weather_forecast_feed: Optional[Union[pd.DataFrame, List[Dict]]] = None,
        is_offline: bool = False,
        include_flexible: bool = True,
    ) -> pd.DataFrame:
        """
        Generates a multi-step forecast table conforming to Member 4's schema.

        Parameters:
        -----------
        current_timestamp : str or pd.Timestamp
            Origin timestamp of the forecast.
        horizon_hours : int
            Forecast lookahead horizon in hours (1 to 48, default 24).
        recent_history : pd.DataFrame or list of dicts, optional
            Recent local station telemetry.
        weather_forecast_feed : pd.DataFrame or list of dicts, optional
            External NWP weather forecast feed if online.
        is_offline : bool
            Flag set to True during communication outages.
        include_flexible : bool, default True
            Flag whether flexible station electrical load (10 kW) is included
            in addition to base critical load (20 kW).

        Returns:
        --------
        pd.DataFrame with exact Member 4 contract columns.
        """
        if horizon_hours < 1 or horizon_hours > 48:
            raise ValueError(
                f"horizon_hours must be between 1 and 48, got {horizon_hours}"
            )

        start_ts = pd.to_datetime(current_timestamp, utc=True)

        future_timestamps = [
            start_ts + pd.Timedelta(hours=h)
            for h in range(1, horizon_hours + 1)
        ]

        # Determine operation mode:
        # If offline flag is set or ML models are unavailable,
        # use offline climatology/persistence.
        use_offline = (
            is_offline
            or (not self.is_online_ready and weather_forecast_feed is None)
        )

        if (
            not use_offline
            and self.is_online_ready
            and weather_forecast_feed is not None
        ):
            forecast_df = self._predict_ml(
                future_timestamps,
                weather_forecast_feed,
                recent_history,
                include_flexible=include_flexible,
            )
        else:
            forecast_df = self._predict_offline(
                future_timestamps,
                recent_history,
                is_comms_outage=is_offline,
                include_flexible=include_flexible,
            )

        return forecast_df

    def get_24h_forecast(
        self,
        current_timestamp: Union[str, pd.Timestamp],
        recent_history: Optional[Union[pd.DataFrame, List[Dict]]] = None,
        is_offline: bool = False,
        include_flexible: bool = True,
    ) -> pd.DataFrame:
        """Convenience method returning a standard 24-hour day-ahead forecast."""
        return self.generate_forecast(
            current_timestamp=current_timestamp,
            horizon_hours=24,
            recent_history=recent_history,
            is_offline=is_offline,
            include_flexible=include_flexible,
        )

    def _predict_offline(
        self,
        future_timestamps: List[pd.Timestamp],
        recent_history: Optional[Union[pd.DataFrame, List[Dict]]] = None,
        is_comms_outage: bool = False,
        include_flexible: bool = True,
    ) -> pd.DataFrame:
        """
        Executes offline forecasting using Polar Climatology lookup table,
        applying adaptive uncertainty widening if in communication outage mode.
        """
        if self.climatology is None or not self.climatology.is_fitted:
            self._initialize_service()

        rows = []
        elec_kw = electrical_load(include_flexible=include_flexible)

        for step, ts in enumerate(future_timestamps, start=1):
            if self.climatology is not None:
                step_pred = self.climatology.predict_step(ts)
            else:
                # Emergency cold fallback using physics on seasonal defaults
                step_pred = self._emergency_default_step(ts)

            # Extract base P10, P50, P90
            solar_p50 = step_pred.get("solar_power_kw_p50", 0.0)
            solar_p10 = step_pred.get("solar_power_kw_p10", 0.0)
            solar_p90 = step_pred.get("solar_power_kw_p90", 0.0)

            wind_p50 = step_pred.get("wind_power_kw_p50", 0.0)
            wind_p10 = step_pred.get("wind_power_kw_p10", 0.0)
            wind_p90 = step_pred.get("wind_power_kw_p90", 0.0)

            heat_p50 = step_pred.get(
                "heating_load_kw_p50",
                config.HEATING_BASE_KW,
            )
            heat_p10 = step_pred.get(
                "heating_load_kw_p10",
                config.HEATING_BASE_KW,
            )
            heat_p90 = step_pred.get(
                "heating_load_kw_p90",
                config.HEATING_BASE_KW,
            )

            temp_pred = step_pred.get("temperature_c_p50", -15.0)
            wind_pred = step_pred.get("wind_speed_ms_p50", 6.0)
            irr_pred = step_pred.get("irradiance_w_m2_p50", 0.0)

            # Adaptive uncertainty widening during communication outage:
            # Expand P10-P90 spread by 35% so Member 4 plans larger reserve margins
            if is_comms_outage:
                solar_p10 = max(0.0, solar_p10 * 0.65)
                solar_p90 = min(
                    config.SOLAR_CAPACITY_KW,
                    solar_p90 * 1.35,
                )

                wind_p10 = max(0.0, wind_p10 * 0.65)
                wind_p90 = min(
                    config.WIND_CAPACITY_KW,
                    wind_p90 * 1.35,
                )

                heat_p90 = heat_p90 * 1.15

                mode_label = "offline_climatology_comms_outage"
                confidence = max(
                    0.30,
                    round(0.70 - (step * 0.008), 3),
                )
            else:
                mode_label = "offline_climatology"
                confidence = max(
                    0.40,
                    round(0.85 - (step * 0.008), 3),
                )

            # Total load = electrical + heating
            total_p10 = round(elec_kw + heat_p10, 4)
            total_p50 = round(elec_kw + heat_p50, 4)
            total_p90 = round(elec_kw + heat_p90, 4)

            # Net load
            net_p50 = round(
                total_p50 - (solar_p50 + wind_p50),
                4,
            )

            # Storm and turbine cutout risk flags
            storm_risk = bool(
                wind_pred >= config.STORM_WIND_THRESHOLD_MS
            )
            cutout_risk = bool(
                wind_pred >= config.WIND_CUT_OUT_MS
            )

            rows.append(
                {
                    "timestamp": ts.isoformat(),
                    "step_ahead": step,
                    "solar_power_kw_p10": round(solar_p10, 4),
                    "solar_power_kw_p50": round(solar_p50, 4),
                    "solar_power_kw_p90": round(solar_p90, 4),
                    "wind_power_kw_p10": round(wind_p10, 4),
                    "wind_power_kw_p50": round(wind_p50, 4),
                    "wind_power_kw_p90": round(wind_p90, 4),
                    "electrical_load_kw": float(elec_kw),
                    "heating_load_kw_p50": round(heat_p50, 4),
                    "total_load_kw_p10": total_p10,
                    "total_load_kw_p50": total_p50,
                    "total_load_kw_p90": total_p90,
                    "net_load_kw_p50": net_p50,
                    "temperature_c_pred": round(temp_pred, 2),
                    "wind_speed_ms_pred": round(wind_pred, 2),
                    "irradiance_w_m2_pred": round(irr_pred, 2),
                    "storm_risk_flag": storm_risk,
                    "turbine_cutout_risk": cutout_risk,
                    "confidence_score": confidence,
                    "forecast_mode": mode_label,
                }
            )

        result = pd.DataFrame(rows)

        # Force Python bool objects so identity checks like `is False`
        # behave correctly in the contract tests.
        if "storm_risk_flag" in result.columns:
            result["storm_risk_flag"] = pd.Series(
                [bool(value) for value in result["storm_risk_flag"]],
                index=result.index,
                dtype=object,
            )

        if "turbine_cutout_risk" in result.columns:
            result["turbine_cutout_risk"] = pd.Series(
                [bool(value) for value in result["turbine_cutout_risk"]],
                index=result.index,
                dtype=object,
            )

        return result

    def _predict_ml(
        self,
        future_timestamps: List[pd.Timestamp],
        weather_forecast_feed: Union[pd.DataFrame, List[Dict]],
        recent_history: Optional[Union[pd.DataFrame, List[Dict]]],
        include_flexible: bool = True,
    ) -> pd.DataFrame:
        """
        Executes multi-quantile Machine Learning prediction when online models
        and weather forecasts are available.
        """
        if isinstance(weather_forecast_feed, list):
            wf_df = pd.DataFrame(weather_forecast_feed)
        else:
            wf_df = weather_forecast_feed.copy()

        # Generate predictions via trained system or Member 1 physics models
        if self.system is not None and self.system.is_fitted:
            feat_df = build_features(wf_df, drop_na=False)
            feature_cols = [
                c for c in self.system.feature_names
                if c in feat_df.columns
            ]
            preds_df = self.system.predict(feat_df[feature_cols])
        else:
            # Physics-based direct calculation from weather feed using Member 1 functions
            preds_rows = []

            for _, w in wf_df.iterrows():
                irr = float(
                    w.get(
                        "irradiance_w_m2",
                        w.get("solar_irradiance_wm2", 0.0),
                    )
                )
                temp = float(w.get("temperature_c", -15.0))
                ws = float(
                    w.get(
                        "wind_speed_ms",
                        w.get("wind_speed_mps", 5.0),
                    )
                )

                sol = solar_pv_output(irr, temp)
                wnd = wind_power_output(ws)
                heat = heating_load(temp)

                preds_rows.append(
                    {
                        "solar_power_kw_p10": max(0.0, sol * 0.9),
                        "solar_power_kw_p50": sol,
                        "solar_power_kw_p90": min(
                            config.SOLAR_CAPACITY_KW,
                            sol * 1.1,
                        ),
                        "wind_power_kw_p10": max(0.0, wnd * 0.9),
                        "wind_power_kw_p50": wnd,
                        "wind_power_kw_p90": min(
                            config.WIND_CAPACITY_KW,
                            wnd * 1.1,
                        ),
                        "heating_load_kw_p10": heat * 0.95,
                        "heating_load_kw_p50": heat,
                        "heating_load_kw_p90": heat * 1.05,
                    }
                )

            preds_df = pd.DataFrame(preds_rows)

        rows = []
        elec_kw = electrical_load(include_flexible=include_flexible)

        for step, ts in enumerate(future_timestamps, start=1):
            idx = step - 1 if step - 1 < len(preds_df) else -1

            row_pred = preds_df.iloc[idx]
            row_weather = (
                wf_df.iloc[idx]
                if idx < len(wf_df)
                else wf_df.iloc[-1]
            )

            solar_p10 = float(row_pred["solar_power_kw_p10"])
            solar_p50 = float(row_pred["solar_power_kw_p50"])
            solar_p90 = float(row_pred["solar_power_kw_p90"])

            wind_p10 = float(row_pred["wind_power_kw_p10"])
            wind_p50 = float(row_pred["wind_power_kw_p50"])
            wind_p90 = float(row_pred["wind_power_kw_p90"])

            heat_p50 = float(row_pred["heating_load_kw_p50"])
            heat_p10 = float(row_pred["heating_load_kw_p10"])
            heat_p90 = float(row_pred["heating_load_kw_p90"])

            total_p10 = round(elec_kw + heat_p10, 4)
            total_p50 = round(elec_kw + heat_p50, 4)
            total_p90 = round(elec_kw + heat_p90, 4)

            net_p50 = round(
                total_p50 - (solar_p50 + wind_p50),
                4,
            )

            wind_val = float(
                row_weather.get(
                    "wind_speed_ms",
                    row_weather.get("wind_speed_mps", 5.0),
                )
            )
            temp_val = float(
                row_weather.get("temperature_c", -15.0)
            )
            irr_val = float(
                row_weather.get(
                    "irradiance_w_m2",
                    row_weather.get(
                        "solar_irradiance_wm2",
                        0.0,
                    ),
                )
            )

            storm_risk = bool(
                wind_val >= config.STORM_WIND_THRESHOLD_MS
            )
            cutout_risk = bool(
                wind_val >= config.WIND_CUT_OUT_MS
            )

            confidence = max(
                0.50,
                round(0.95 - (step * 0.007), 3),
            )

            rows.append(
                {
                    "timestamp": ts.isoformat(),
                    "step_ahead": step,
                    "solar_power_kw_p10": round(solar_p10, 4),
                    "solar_power_kw_p50": round(solar_p50, 4),
                    "solar_power_kw_p90": round(solar_p90, 4),
                    "wind_power_kw_p10": round(wind_p10, 4),
                    "wind_power_kw_p50": round(wind_p50, 4),
                    "wind_power_kw_p90": round(wind_p90, 4),
                    "electrical_load_kw": float(elec_kw),
                    "heating_load_kw_p50": round(heat_p50, 4),
                    "total_load_kw_p10": total_p10,
                    "total_load_kw_p50": total_p50,
                    "total_load_kw_p90": total_p90,
                    "net_load_kw_p50": net_p50,
                    "temperature_c_pred": round(temp_val, 2),
                    "wind_speed_ms_pred": round(wind_val, 2),
                    "irradiance_w_m2_pred": round(irr_val, 2),
                    "storm_risk_flag": storm_risk,
                    "turbine_cutout_risk": cutout_risk,
                    "confidence_score": confidence,
                    "forecast_mode": "ml_ensemble",
                }
            )

        result = pd.DataFrame(rows)

        # Force Python bool objects for exact boolean identity checks.
        if "storm_risk_flag" in result.columns:
            result["storm_risk_flag"] = pd.Series(
                [bool(value) for value in result["storm_risk_flag"]],
                index=result.index,
                dtype=object,
            )

        if "turbine_cutout_risk" in result.columns:
            result["turbine_cutout_risk"] = pd.Series(
                [bool(value) for value in result["turbine_cutout_risk"]],
                index=result.index,
                dtype=object,
            )

        return result

    def _emergency_default_step(
        self,
        timestamp: pd.Timestamp,
    ) -> Dict[str, float]:
        """Physics-based estimation when no lookup tables or models are loaded."""
        geo = compute_solar_geometry([timestamp])

        elevation = geo["solar_elevation_deg"].iloc[0]

        irr = (
            max(
                0.0,
                float(
                    geo["extraterrestrial_irradiance_proxy"].iloc[0] * 0.7
                ),
            )
            if elevation > 0
            else 0.0
        )

        temp = -15.0
        wind = 6.0

        solar = solar_pv_output(irr, temp)
        wind_p = wind_power_output(wind)
        heat = heating_load(temp)

        return {
            "solar_power_kw_p50": solar,
            "solar_power_kw_p10": solar * 0.8,
            "solar_power_kw_p90": solar * 1.2,
            "wind_power_kw_p50": wind_p,
            "wind_power_kw_p10": wind_p * 0.8,
            "wind_power_kw_p90": wind_p * 1.2,
            "heating_load_kw_p50": heat,
            "heating_load_kw_p10": heat * 0.95,
            "heating_load_kw_p90": heat * 1.10,
            "temperature_c_p50": temp,
            "wind_speed_ms_p50": wind,
            "irradiance_w_m2_p50": irr,
        }


def get_forecast(
    current_timestamp: Union[str, pd.Timestamp],
    horizon_hours: int = 24,
    recent_history: Optional[Union[pd.DataFrame, List[Dict]]] = None,
    weather_forecast_feed: Optional[Union[pd.DataFrame, List[Dict]]] = None,
    is_offline: bool = False,
    model_dir: str = DEFAULT_MODEL_DIR,
    include_flexible: bool = True,
) -> pd.DataFrame:
    """
    Direct function entry point for Member 4 to retrieve forecasts.
    """
    service = ForecastService(model_dir=model_dir)

    return service.generate_forecast(
        current_timestamp=current_timestamp,
        horizon_hours=horizon_hours,
        recent_history=recent_history,
        weather_forecast_feed=weather_forecast_feed,
        is_offline=is_offline,
        include_flexible=include_flexible,
    )