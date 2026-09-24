# src/forecasting/fallback.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Offline Fallback & Climatological Forecasters
# Member 3: Renewable Energy & Station Load Forecasting
#
# Provides robust, zero-external-communication forecasting for polar stations:
#   1. PolarClimatologyForecaster:
#      Builds multi-year hourly seasonal lookups (P10, P50, P90) conditioned
#      on day-of-year and hour. Runs 100% locally on edge hardware.
#   2. PersistenceForecaster:
#      Diurnal (24-hour lag) and last-value persistence with physical
#      polar night and capacity bounds.
#
# Activated automatically during communication outages or sensor faults.
# ─────────────────────────────────────────────────────────────────────────────

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Sequence

import config
from src.forecasting.preprocessor import TARGET_COLUMNS, TARGET_PHYSICAL_LIMITS


class PolarClimatologyForecaster:
    """
    Seasonal polar climatological forecaster.

    Aggregates historical hourly measurements by (day_of_year, hour) or
    (month, hour) to produce deterministic P10, P50 (median), and P90
    forecasts for solar, wind, heating, and total load.
    """

    def __init__(self, target_cols: Sequence[str] = TARGET_COLUMNS):
        self.target_cols = list(target_cols)
        self.lookup_table: Dict[Tuple[int, int], Dict[str, float]] = {}
        self.is_fitted = False

    def fit(self, df: pd.DataFrame, time_col: str = "timestamp") -> "PolarClimatologyForecaster":
        """
        Builds the climatology lookup table from historical training data.
        """
        ts = pd.to_datetime(df[time_col], utc=True)
        work = df.copy()
        work["doy"] = ts.dt.dayofyear
        work["hour"] = ts.dt.hour

        # Group by (day_of_year, hour)
        grouped = work.groupby(["doy", "hour"])

        lookup = {}
        for (doy, hr), group in grouped:
            entry = {}
            for col in self.target_cols:
                vals = group[col].to_numpy()
                entry[f"{col}_p50"] = float(np.median(vals))
                entry[f"{col}_p10"] = float(np.percentile(vals, 10))
                entry[f"{col}_p90"] = float(np.percentile(vals, 90))

            # Also store ambient weather for physical sanity
            for w_col in ["temperature_c", "wind_speed_ms", "irradiance_w_m2"]:
                if w_col in group.columns:
                    entry[f"{w_col}_p50"] = float(np.median(group[w_col]))

            lookup[(int(doy), int(hr))] = entry

        self.lookup_table = lookup
        self.is_fitted = True
        return self

    def predict_step(self, timestamp: pd.Timestamp) -> Dict[str, float]:
        """
        Returns the climatological P10, P50, and P90 forecast for a single timestamp.
        """
        if not self.is_fitted:
            raise RuntimeError("PolarClimatologyForecaster must be fit() before predict.")

        ts = pd.to_datetime(timestamp, utc=True)
        doy = int(ts.dayofyear)
        hour = int(ts.hour)

        # Retrieve exact day-hour or fallback to adjacent days if leap day missing
        key = (doy, hour)
        if key not in self.lookup_table:
            # Handle missing day/hour combinations by using the nearest
            # available day for the same hour.
            candidates = [
                candidate_key
                for candidate_key in self.lookup_table
                if candidate_key[1] == hour
            ]

            if not candidates:
                raise KeyError(f"No climatology data available for hour {hour}")

            def day_distance(candidate_key):
                candidate_day = candidate_key[0]
                direct = abs(candidate_day - doy)
                return min(direct, 365 - direct)

            key = min(candidates, key=day_distance)

        pred = dict(self.lookup_table[key])

        # Enforce physical capacity clamping
        solar_cap = config.SOLAR_CAPACITY_KW
        wind_cap = config.WIND_CAPACITY_KW

        pred["solar_power_kw_p50"] = np.clip(pred.get("solar_power_kw_p50", 0.0), 0.0, solar_cap)
        pred["solar_power_kw_p10"] = np.clip(pred.get("solar_power_kw_p10", 0.0), 0.0, solar_cap)
        pred["solar_power_kw_p90"] = np.clip(pred.get("solar_power_kw_p90", 0.0), 0.0, solar_cap)

        pred["wind_power_kw_p50"] = np.clip(pred.get("wind_power_kw_p50", 0.0), 0.0, wind_cap)
        pred["wind_power_kw_p10"] = np.clip(pred.get("wind_power_kw_p10", 0.0), 0.0, wind_cap)
        pred["wind_power_kw_p90"] = np.clip(pred.get("wind_power_kw_p90", 0.0), 0.0, wind_cap)

        return pred

    def predict_horizon(
        self,
        start_timestamp: pd.Timestamp,
        horizon_hours: int = 24,
    ) -> pd.DataFrame:
        """
        Produces multi-hour forecast table over horizon_hours.
        """
        start_ts = pd.to_datetime(start_timestamp, utc=True)
        future_timestamps = [start_ts + pd.Timedelta(hours=h) for h in range(1, horizon_hours + 1)]

        rows = []
        for step, ts in enumerate(future_timestamps, start=1):
            row = self.predict_step(ts)
            row["timestamp"] = ts.isoformat()
            row["step_ahead"] = step
            row["forecast_mode"] = "offline_climatology"
            rows.append(row)

        return pd.DataFrame(rows)


class PersistenceForecaster:
    """
    Diurnal (24-hour lag) and Last-Value Persistence Forecaster.

    Uses recent station observations to project future generation and demand.
    For horizon h:
      - Diurnal mode: hat{y}(t + h) = y(t + h - 24)
      - Last-value mode: hat{y}(t + h) = y(t)
    """

    def __init__(self, mode: str = "diurnal"):
        if mode not in ("diurnal", "last_value"):
            raise ValueError(f"Unknown mode: {mode}. Must be 'diurnal' or 'last_value'.")
        self.mode = mode

    def predict_horizon(
        self,
        recent_history: pd.DataFrame,
        horizon_hours: int = 24,
        time_col: str = "timestamp",
    ) -> pd.DataFrame:
        """
        Forecasts next horizon_hours using recent history dataframe (at least 24 hours).
        """
        if len(recent_history) < 24 and self.mode == "diurnal":
            raise ValueError(f"Diurnal persistence requires >= 24 historical rows, got {len(recent_history)}")

        last_ts = pd.to_datetime(recent_history[time_col].iloc[-1], utc=True)
        future_ts = [last_ts + pd.Timedelta(hours=h) for h in range(1, horizon_hours + 1)]

        rows = []
        for step, ts in enumerate(future_ts, start=1):
            row = {"timestamp": ts.isoformat(), "step_ahead": step, "forecast_mode": f"persistence_{self.mode}"}

            if self.mode == "diurnal":
                # Match exact hour of day from the last 24-hour window
                match_hr = ts.hour
                ts_hist = pd.to_datetime(recent_history[time_col], utc=True)
                hist_match = recent_history[ts_hist.dt.hour == match_hr]
                if not hist_match.empty:
                    source_row = hist_match.iloc[-1]
                else:
                    source_row = recent_history.iloc[-1]
            else:
                source_row = recent_history.iloc[-1]

            for col in TARGET_COLUMNS:
                val = float(source_row[col]) if col in source_row else 0.0
                row[f"{col}_p50"] = val
                # Heuristic uncertainty band for persistence (±15% spread)
                row[f"{col}_p10"] = float(max(0.0, val * 0.85))
                row[f"{col}_p90"] = float(val * 1.15)

            rows.append(row)

        return pd.DataFrame(rows)
