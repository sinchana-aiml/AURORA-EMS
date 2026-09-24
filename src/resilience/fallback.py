# src/resilience/fallback.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Safe Fallback Dispatch Policy
# Member: Resilience & Offline Integration
#
# The forecasting and optimization modules are the "smart" layer. This module
# is what runs when that layer is unavailable, raises, or times out.
#
# Design decision: the fallback does NOT reimplement dispatch. It delegates to
# the already-validated Digital Twin (energy_balance_step), which performs
# deterministic priority dispatch — renewables, then battery, then Generator 1,
# then Generator 2 — with no ML dependency. A fallback must never depend on the
# component that just failed.
# ─────────────────────────────────────────────────────────────────────────────

import config
from src.digital_twin import energy_balance_step

# Dispatch modes reported to the dashboard.
MODE_OPTIMIZED = "OPTIMIZED"           # AI forecast + optimizer produced this
MODE_FALLBACK  = "FALLBACK_TWIN"       # deterministic Digital Twin dispatch


def _load_shed_advice(result):
    """
    Flexible-load guidance derived from the Twin's own output.

    The Twin serves total load and reports unmet_load_kw. When load is unmet,
    the operator should shed flexible load first so the critical block
    (config.CRITICAL_LOAD_KW) stays served.
    """
    unmet = result["unmet_load_kw"]
    if unmet <= 0:
        return False, "All load served; no shedding required."
    if unmet <= config.FLEXIBLE_LOAD_KW:
        return True, (
            f"Shed flexible load ({config.FLEXIBLE_LOAD_KW:.0f} kW available) "
            f"to cover {unmet:.1f} kW shortfall and protect critical load."
        )
    return True, (
        f"Shortfall {unmet:.1f} kW exceeds flexible load "
        f"({config.FLEXIBLE_LOAD_KW:.0f} kW); shed all flexible load and "
        f"alert operator — critical load may be at risk."
    )


def _explain(result, shed_reason, fuel_warning):
    """Builds the operator-facing reason string for this dispatch decision."""
    parts = []
    renewable = result["renewable_used_kw"]
    gen_total = result["generator_total_kw"]
    discharge = result["battery_discharge_kw"]

    if renewable > 0:
        parts.append(f"Renewables supplied {renewable:.1f} kW.")
    if discharge > 0:
        parts.append(f"Battery discharged {discharge:.1f} kW within the "
                     f"{config.BATTERY_MIN_SOC_FRACTION:.0%} reserve limit.")
    if gen_total > 0:
        parts.append(f"Generators supplied {gen_total:.1f} kW "
                     f"({result['fuel_used_litres']:.2f} L used).")
    if result["curtailed_power_kw"] > 0:
        parts.append(f"{result['curtailed_power_kw']:.1f} kW curtailed "
                     f"(battery could not absorb surplus).")
    parts.append(shed_reason)
    if fuel_warning:
        parts.append(f"LOW FUEL: {result['fuel_remaining_litres']:.0f} L remaining "
                     f"(threshold {config.LOW_FUEL_THRESHOLD_L:.0f} L).")
    return " ".join(parts)


def fallback_dispatch(weather_record, battery_soc_kwh, fuel_remaining_litres,
                      generator_1_available=True, generator_2_available=True,
                      timestep_hours=config.SIMULATION_TIMESTEP_HOURS):
    """
    Deterministic dispatch for one timestep, via the validated Digital Twin.

    Returns the Twin's full result dict plus resilience fields:
      dispatch_mode, flexible_load_shed, low_fuel_warning, reasoning
    """
    result = energy_balance_step(
        temperature_c         = weather_record["temperature_c"],
        irradiance_w_m2       = weather_record["irradiance_w_m2"],
        wind_speed_ms         = weather_record["wind_speed_ms"],
        battery_soc_kwh       = battery_soc_kwh,
        fuel_remaining_litres = fuel_remaining_litres,
        generator_1_available = generator_1_available,
        generator_2_available = generator_2_available,
        timestep_hours        = timestep_hours,
    )

    shed, shed_reason = _load_shed_advice(result)
    fuel_warning = result["fuel_remaining_litres"] <= config.LOW_FUEL_THRESHOLD_L

    result["dispatch_mode"]      = MODE_FALLBACK
    result["flexible_load_shed"] = shed
    result["low_fuel_warning"]   = fuel_warning
    result["reasoning"]          = _explain(result, shed_reason, fuel_warning)
    return result


def safe_dispatch(weather_record, battery_soc_kwh, fuel_remaining_litres,
                  generator_1_available=True, generator_2_available=True,
                  timestep_hours=config.SIMULATION_TIMESTEP_HOURS,
                  optimizer=None):
    """
    Single entry point the rest of the system should call instead of invoking
    the optimizer directly.

    optimizer : callable with the same signature as fallback_dispatch, or None.
                Pass the forecasting/optimization module here once it exists
                (feature/forecasting). Any exception it raises is caught and
                the deterministic Twin dispatch is used instead.

    Always returns a dispatch result — never raises, never returns None.
    A polar station must not lose its dispatch decision because a model failed.
    """
    if optimizer is None:
        result = fallback_dispatch(
            weather_record, battery_soc_kwh, fuel_remaining_litres,
            generator_1_available, generator_2_available, timestep_hours,
        )
        result["fallback_triggered"] = True
        result["fallback_reason"]    = (
            "No optimizer supplied — running deterministic Digital Twin dispatch."
        )
        return result

    try:
        result = optimizer(
            weather_record, battery_soc_kwh, fuel_remaining_litres,
            generator_1_available, generator_2_available, timestep_hours,
        )
        if result is None or "battery_soc_kwh" not in result:
            raise ValueError("Optimizer returned an incomplete result.")
        result.setdefault("dispatch_mode", MODE_OPTIMIZED)
        result["fallback_triggered"] = False
        return result
    except Exception as exc:                      # noqa: BLE001 — must catch all
        result = fallback_dispatch(
            weather_record, battery_soc_kwh, fuel_remaining_litres,
            generator_1_available, generator_2_available, timestep_hours,
        )
        result["fallback_triggered"] = True
        result["fallback_reason"]    = f"Optimizer failed ({type(exc).__name__}: {exc})."
        return result
