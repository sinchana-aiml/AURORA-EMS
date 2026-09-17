# src/digital_twin/generator_model.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Diesel Generator Model
# Simulates one timestep of either station generator including minimum-load
# enforcement and two-part fuel consumption.
# All formulas are PROTOTYPE / SIMULATED — not real NCPOR measurements.
# ─────────────────────────────────────────────────────────────────────────────

import config

# Map generator_id -> its config constants (avoids long if/else chains later)
_GEN_PARAMS = {
    1: {
        "rated_kw":      config.GENERATOR_1_RATED_KW,
        "minimum_kw":    config.GENERATOR_1_MINIMUM_KW,
        "idle_fuel_lph": config.GENERATOR_1_IDLE_FUEL_LPH,
        "fuel_per_kwh":  config.GENERATOR_1_FUEL_PER_KWH,
    },
    2: {
        "rated_kw":      config.GENERATOR_2_RATED_KW,
        "minimum_kw":    config.GENERATOR_2_MINIMUM_KW,
        "idle_fuel_lph": config.GENERATOR_2_IDLE_FUEL_LPH,
        "fuel_per_kwh":  config.GENERATOR_2_FUEL_PER_KWH,
    },
}


def generator_output_and_fuel(generator_id, requested_power_kw,
                               available=True, timestep_hours=1.0,
                               available_fuel_litres=None):
    """
    Simulates one timestep of a diesel generator.

    generator_id       : 1 or 2
    requested_power_kw : how much power the station needs from this generator
    available          : False if the generator has failed or is offline
    timestep_hours     : length of this simulation step in hours
    available_fuel_litres : fuel available to this generator for this step.
                             None preserves the legacy unlimited-fuel behavior.

    Returns a dict with:
      actual_output_kw  : power actually produced (kW)
      fuel_used_litres  : diesel consumed this timestep (litres)
      status            : human-readable string describing generator state
    """
    p = _GEN_PARAMS[generator_id]

    # Rule 1: generator is broken or switched off — produces nothing
    if not available:
        return {"actual_output_kw": 0.0, "fuel_used_litres": 0.0, "status": "unavailable"}

    # Rule 2: no power requested — generator stays off
    if requested_power_kw <= 0:
        return {"actual_output_kw": 0.0, "fuel_used_litres": 0.0, "status": "off"}

    # Rule 3: an empty tank prevents the generator from starting.
    if available_fuel_litres is not None and available_fuel_litres <= 0:
        return {"actual_output_kw": 0.0, "fuel_used_litres": 0.0, "status": "no_fuel"}

    # Rule 4: cap output at rated capacity
    actual_output_kw = min(requested_power_kw, p["rated_kw"])

    # Rule 5: diesel engines cannot run efficiently below a minimum load;
    #         if asked for less than minimum, run at minimum anyway
    if actual_output_kw < p["minimum_kw"]:
        actual_output_kw = p["minimum_kw"]

    # Rule 6: fuel = idle burn (just to keep engine running) + load-dependent burn
    fuel_used_litres = (p["idle_fuel_lph"] * timestep_hours
                        + p["fuel_per_kwh"] * actual_output_kw * timestep_hours)

    # Do not consume more fuel than is present.  A generator needs enough fuel
    # to sustain its minimum operating load; otherwise it stays off.
    if available_fuel_litres is not None and fuel_used_litres > available_fuel_litres:
        fuel_limited_output_kw = (
            available_fuel_litres / timestep_hours - p["idle_fuel_lph"]
        ) / p["fuel_per_kwh"]
        if fuel_limited_output_kw < p["minimum_kw"]:
            return {"actual_output_kw": 0.0, "fuel_used_litres": 0.0, "status": "no_fuel"}
        actual_output_kw = fuel_limited_output_kw
        fuel_used_litres = available_fuel_litres

    return {
        "actual_output_kw": round(actual_output_kw, 4),
        "fuel_used_litres": round(fuel_used_litres, 4),
        "status":           "fuel_limited" if available_fuel_litres is not None and fuel_used_litres == available_fuel_litres else "running",
    }
