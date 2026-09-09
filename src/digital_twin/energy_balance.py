# src/digital_twin/energy_balance.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Energy Balance Dispatcher
# Runs one simulation timestep: dispatches load across renewables, battery,
# and generators in priority order and returns every power-flow field.
# All formulas are PROTOTYPE / SIMULATED — not real NCPOR measurements.
#
# Dispatch priority (highest -> lowest):
#   1. Renewables (solar + wind)  -- free, use first
#   2. Battery discharge          -- stored energy, no fuel cost
#   3. Generator 1                -- lower fuel rate
#   4. Generator 2                -- backup
# ─────────────────────────────────────────────────────────────────────────────

import config
from .load_model      import electrical_load, heating_load
from .renewable_model import solar_pv_output, wind_power_output
from .battery_model   import battery_step
from .generator_model import generator_output_and_fuel


def energy_balance_step(
    temperature_c,
    irradiance_w_m2,
    wind_speed_ms,
    battery_soc_kwh,
    fuel_remaining_litres,
    generator_1_available=True,
    generator_2_available=True,
    timestep_hours=1.0,
):
    """
    Runs one timestep of the digital twin energy balance.

    Surplus renewable energy charges the battery first, then is curtailed.
    Returns a full dict of every power flow and state variable.
    """
    # Step 1: station load
    elec_kw    = electrical_load(include_flexible=True)
    heat_kw    = heating_load(temperature_c)
    demand_kw  = elec_kw + heat_kw
    deficit_kw = demand_kw

    # Step 2: renewables
    solar_kw     = solar_pv_output(irradiance_w_m2, temperature_c)
    wind_kw      = wind_power_output(wind_speed_ms)
    renewable_kw = solar_kw + wind_kw

    renewable_used_kw = min(renewable_kw, deficit_kw)
    deficit_kw       -= renewable_used_kw
    surplus_kw        = renewable_kw - renewable_used_kw

    # Step 3: battery
    curtailed_kw = 0.0
    if surplus_kw > 0:
        # surplus renewable -> charge battery
        batt            = battery_step(battery_soc_kwh, surplus_kw, timestep_hours)
        battery_soc_kwh = batt["new_soc_kwh"]
        charge_kw       = batt["actual_charge_kw"]
        discharge_kw    = 0.0
        curtailed_kw    = surplus_kw - charge_kw
    elif deficit_kw > 0:
        # deficit -> discharge battery
        batt            = battery_step(battery_soc_kwh, -deficit_kw, timestep_hours)
        battery_soc_kwh = batt["new_soc_kwh"]
        discharge_kw    = batt["actual_discharge_kw"]
        charge_kw       = 0.0
        deficit_kw     -= discharge_kw
    else:
        charge_kw    = 0.0
        discharge_kw = 0.0

    # Step 4: Generator 1
    g1 = generator_output_and_fuel(1, deficit_kw,
                                   available=generator_1_available,
                                   timestep_hours=timestep_hours)
    deficit_kw            -= g1["actual_output_kw"]
    fuel_remaining_litres  = max(0.0, fuel_remaining_litres - g1["fuel_used_litres"])

    # Step 5: Generator 2
    g2 = generator_output_and_fuel(2, deficit_kw,
                                   available=generator_2_available,
                                   timestep_hours=timestep_hours)
    deficit_kw            -= g2["actual_output_kw"]
    fuel_remaining_litres  = max(0.0, fuel_remaining_litres - g2["fuel_used_litres"])

    # Step 6: handle excess generation from generator minimum loading.
    # deficit_kw is now negative when generators produced more than needed.
    # Try to absorb that excess into the battery first, then curtail the rest.
    gen_to_batt_kw = 0.0
    excess_kw      = max(0.0, -deficit_kw)   # positive = generators over-produced
    if excess_kw > 0:
        batt2           = battery_step(battery_soc_kwh, excess_kw, timestep_hours)
        battery_soc_kwh = batt2["new_soc_kwh"]
        gen_to_batt_kw  = batt2["actual_charge_kw"]
        charge_kw      += gen_to_batt_kw           # add to total battery charging
        curtailed_kw   += excess_kw - gen_to_batt_kw  # anything battery couldn't take

    # Step 7: unmet load and critical load check.
    # When generators over-produced, deficit is negative -- unmet load is zero.
    unmet_kw        = max(0.0, round(deficit_kw, 6))
    supplied_kw     = demand_kw - unmet_kw
    critical_served = supplied_kw >= config.CRITICAL_LOAD_KW

    return {
        "temperature_c":                  temperature_c,
        "irradiance_w_m2":                irradiance_w_m2,
        "wind_speed_ms":                  wind_speed_ms,
        "electrical_load_kw":             round(elec_kw, 4),
        "heating_load_kw":                round(heat_kw, 4),
        "total_load_kw":                  round(demand_kw, 4),
        "solar_power_kw":                 round(solar_kw, 4),
        "wind_power_kw":                  round(wind_kw, 4),
        "renewable_used_kw":              round(renewable_used_kw, 4),
        "battery_charge_kw":              round(charge_kw, 4),
        "battery_discharge_kw":           round(discharge_kw, 4),
        "battery_soc_kwh":                round(battery_soc_kwh, 4),
        "generator_1_power_kw":           round(g1["actual_output_kw"], 4),
        "generator_2_power_kw":           round(g2["actual_output_kw"], 4),
        "generator_total_kw":             round(g1["actual_output_kw"] + g2["actual_output_kw"], 4),
        "generator_to_battery_charge_kw": round(gen_to_batt_kw, 4),
        "excess_generation_kw":           round(excess_kw, 4),
        "curtailed_power_kw":             round(curtailed_kw, 4),
        "fuel_used_litres":               round(g1["fuel_used_litres"] + g2["fuel_used_litres"], 4),
        "fuel_remaining_litres":          round(fuel_remaining_litres, 4),
        "unmet_load_kw":                  round(unmet_kw, 4),
        "supplied_load_kw":               round(supplied_kw, 4),
        "critical_load_served":           critical_served,
    }
