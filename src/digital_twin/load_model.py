# src/digital_twin/load_model.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Station Load Model
# Calculates electrical and heating demand for the virtual polar station.
# All formulas are PROTOTYPE / SIMULATED — not real NCPOR measurements.
# ─────────────────────────────────────────────────────────────────────────────

import config


def electrical_load(include_flexible=True):
    """
    Returns station electrical demand in kW.
    - Critical load is always on.
    - Flexible load can be shed during shortfalls.
    """
    load = config.BASE_LOAD_KW
    if include_flexible:
        load += config.FLEXIBLE_LOAD_KW
    return load  # kW


def heating_load(temperature_c):
    """
    Returns heating demand in kW based on outside temperature.
    - At 0 C and above: base heating load only.
    - Below 0 C: extra heating kicks in per degree.
    """
    extra = max(0, -temperature_c) * config.HEATING_TEMP_COEFF
    return config.HEATING_BASE_KW + extra  # kW


def total_load(temperature_c, include_flexible=True):
    """
    Returns total station load in kW.
    = electrical load + heating load
    """
    return electrical_load(include_flexible) + heating_load(temperature_c)  # kW
