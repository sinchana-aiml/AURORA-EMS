# src/forecasting/evaluation.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Forecasting Evaluation Metrics
# Member 3: Renewable Energy & Station Load Forecasting
#
# Standard metrics for point forecasts and probabilistic uncertainty intervals:
#   - Mean Absolute Error (MAE)
#   - Root Mean Squared Error (RMSE)
#   - Normalized RMSE (nRMSE) relative to rated capacity
#   - Mean Absolute Percentage Error (MAPE)
#   - Coefficient of Determination (R²)
#   - Quantile Pinball Loss (for P10, P50, P90)
#   - Prediction Interval Coverage Probability (PICP)
#   - Mean Prediction Interval Width (MPIW)
#
# Pure NumPy implementation: zero heavy external dependency required.
# ─────────────────────────────────────────────────────────────────────────────

import numpy as np
from typing import Dict, Union, Optional


def mean_absolute_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Computes Mean Absolute Error (MAE) in kW."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_t - y_p)))


def root_mean_squared_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Computes Root Mean Squared Error (RMSE) in kW."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_t - y_p) ** 2)))


def normalized_rmse(y_true: np.ndarray, y_pred: np.ndarray, capacity: float) -> float:
    """
    Computes Normalized RMSE as a percentage of rated equipment capacity.
    capacity: rated peak capacity in kW (e.g. 40 kW for Solar, 50 kW for Wind).
    """
    if capacity <= 0:
        raise ValueError(f"Capacity must be positive, got {capacity}")
    rmse = root_mean_squared_error(y_true, y_pred)
    return round((rmse / capacity) * 100.0, 4)

def r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Computes Coefficient of Determination (R²)."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    ss_res = np.sum((y_t - y_p) ** 2)
    ss_tot = np.sum((y_t - np.mean(y_t)) ** 2)
    if ss_tot == 0.0:
        return 1.0 if ss_res == 0.0 else 0.0
    return float(1.0 - (ss_res / ss_tot))


def mean_absolute_percentage_error(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    threshold: float = 1.0,
) -> float:
    """
    Computes Mean Absolute Percentage Error (MAPE).
    Filters out near-zero values (< threshold kW) to avoid infinite percentages
    during night hours or calm conditions.
    """
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    mask = y_t >= threshold
    if not np.any(mask):
        return 0.0
    return float(np.mean(np.abs((y_t[mask] - y_p[mask]) / y_t[mask])) * 100.0)


def pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, quantile: float) -> float:
    """
    Computes Pinball (Quantile) Loss for a target quantile alpha in (0, 1).
    Used for evaluating P10, P50, and P90 uncertainty forecasts.
    """
    if not 0.0 < quantile < 1.0:
        raise ValueError(f"Quantile must be in (0, 1), got {quantile}")
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)
    diff = y_t - y_p
    loss = np.maximum(quantile * diff, (quantile - 1.0) * diff)
    return float(np.mean(loss))


def prediction_interval_coverage(
    y_true: np.ndarray,
    y_lower: np.ndarray,
    y_upper: np.ndarray,
) -> float:
    """
    Computes Prediction Interval Coverage Probability (PICP) in percent.
    Percentage of true values that fall within [y_lower, y_upper].
    For an 80% confidence interval (P10 to P90), nominal PICP is 80%.
    """
    y_t = np.asarray(y_true, dtype=float)
    y_l = np.asarray(y_lower, dtype=float)
    y_u = np.asarray(y_upper, dtype=float)
    covered = (y_t >= y_l) & (y_t <= y_u)
    return float(np.mean(covered) * 100.0)


def mean_prediction_interval_width(y_lower: np.ndarray, y_upper: np.ndarray) -> float:
    """Computes Mean Prediction Interval Width (MPIW) in kW."""
    y_l = np.asarray(y_lower, dtype=float)
    y_u = np.asarray(y_upper, dtype=float)
    return float(np.mean(np.maximum(0.0, y_u - y_l)))


def evaluate_forecast(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_lower: Optional[np.ndarray] = None,
    y_upper: Optional[np.ndarray] = None,
    capacity: Optional[float] = None,
) -> Dict[str, float]:
    """
    Computes a comprehensive evaluation metrics summary.

    Parameters:
    -----------
    y_true : Ground truth target array (kW).
    y_pred : Point / median (P50) prediction array (kW).
    y_lower : Optional P10 lower bound array (kW).
    y_upper : Optional P90 upper bound array (kW).
    capacity : Optional rated equipment capacity (kW) for nRMSE.

    Returns:
    --------
    dict with MAE, RMSE, R2, and optional nRMSE, PICP, MPIW.
    """
    metrics = {
        "mae": round(mean_absolute_error(y_true, y_pred), 4),
        "rmse": round(root_mean_squared_error(y_true, y_pred), 4),
        "r2": round(r2_score(y_true, y_pred), 4),
        "mape": round(mean_absolute_percentage_error(y_true, y_pred), 4),
    }

    if capacity is not None and capacity > 0:
        metrics["nrmse_pct"] = round(normalized_rmse(y_true, y_pred, capacity), 2)

    if y_lower is not None:
        metrics["pinball_p10"] = round(pinball_loss(y_true, y_lower, 0.10), 4)

    metrics["pinball_p50"] = round(pinball_loss(y_true, y_pred, 0.50), 4)

    if y_upper is not None:
        metrics["pinball_p90"] = round(pinball_loss(y_true, y_upper, 0.90), 4)

    if y_lower is not None and y_upper is not None:
        metrics["picp_pct"] = round(prediction_interval_coverage(y_true, y_lower, y_upper), 2)
        metrics["mpiw_kw"] = round(mean_prediction_interval_width(y_lower, y_upper), 4)

    return metrics
