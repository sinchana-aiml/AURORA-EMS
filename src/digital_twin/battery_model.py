# src/digital_twin/battery_model.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Battery Energy Storage Model
# Simulates one timestep of charging or discharging the station battery bank.
# All formulas are PROTOTYPE / SIMULATED — not real NCPOR measurements.
# ─────────────────────────────────────────────────────────────────────────────

import config


def battery_step(current_soc_kwh, requested_power_kw, timestep_hours=1.0):
    """
    Simulates one timestep of battery charging or discharging.

    current_soc_kwh    : energy currently stored in the battery (kWh)
    requested_power_kw : positive = charge, negative = discharge, 0 = idle
    timestep_hours     : length of this simulation step in hours

    Returns a dict with:
      new_soc_kwh         : battery energy level after this step (kWh)
      actual_charge_kw    : power actually charged (kW), 0 if discharging
      actual_discharge_kw : power actually discharged (kW), 0 if charging
    """
    # Derived limits from config
    min_soc_kwh = config.BATTERY_CAPACITY_KWH * config.BATTERY_MIN_SOC_FRACTION  # 75 kWh
    max_soc_kwh = config.BATTERY_CAPACITY_KWH                                     # 300 kWh

    actual_charge_kw    = 0.0
    actual_discharge_kw = 0.0
    new_soc_kwh         = current_soc_kwh

    if requested_power_kw > 0:
        # ── CHARGING ──────────────────────────────────────────────────────────
        # Step 1: cap charging power at the hardware limit
        charge_kw = min(requested_power_kw, config.BATTERY_MAX_CHARGE_KW)

        # Step 2: energy that would enter the battery after efficiency loss
        energy_in_kwh = charge_kw * timestep_hours * config.BATTERY_CHARGE_EFFICIENCY

        # Step 3: don't overfill — only charge as much as the battery can hold
        energy_in_kwh = min(energy_in_kwh, max_soc_kwh - current_soc_kwh)

        # Step 4: back-calculate the actual grid power drawn for charging
        actual_charge_kw = energy_in_kwh / (timestep_hours * config.BATTERY_CHARGE_EFFICIENCY)
        new_soc_kwh      = current_soc_kwh + energy_in_kwh

    elif requested_power_kw < 0:
        # ── DISCHARGING ───────────────────────────────────────────────────────
        # Step 1: cap discharge power at the hardware limit (work with positive numbers)
        discharge_kw = min(-requested_power_kw, config.BATTERY_MAX_DISCHARGE_KW)

        # Step 2: energy that would leave the battery (efficiency means more leaves than delivered)
        energy_out_kwh = discharge_kw * timestep_hours / config.BATTERY_DISCHARGE_EFFICIENCY

        # Step 3: don't over-drain — only discharge down to the minimum reserve
        energy_out_kwh = min(energy_out_kwh, current_soc_kwh - min_soc_kwh)

        # Step 4: back-calculate the actual power delivered to the grid
        actual_discharge_kw = energy_out_kwh * config.BATTERY_DISCHARGE_EFFICIENCY / timestep_hours
        new_soc_kwh         = current_soc_kwh - energy_out_kwh

    return {
        "new_soc_kwh":         round(new_soc_kwh, 4),
        "actual_charge_kw":    round(actual_charge_kw, 4),
        "actual_discharge_kw": round(actual_discharge_kw, 4),
    }
