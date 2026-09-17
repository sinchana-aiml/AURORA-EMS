# AURORA-EMS
# Member 4 — Dispatch Constraints
#
# Centralized checks for battery, generator, and load limits.
# All physical limits come from config.py.

import config


def limit_battery_discharge(requested_kw, battery_soc_kwh):
    """
    Limit battery discharge according to:
    - maximum battery discharge power
    - minimum allowed battery SOC
    """

    requested_kw = max(0.0, requested_kw)
    battery_soc_kwh = max(0.0, battery_soc_kwh)

    available_energy_kwh = max(
        0.0,
        battery_soc_kwh - config.BATTERY_MIN_SOC,
    )

    max_soc_limited_kw = (
        available_energy_kwh / config.TIMESTEP_HOURS
    )

    return min(
        requested_kw,
        config.BATTERY_MAX_DISCHARGE_KW,
        max_soc_limited_kw,
    )


def limit_generator_output(requested_kw, generator_id):
    """
    Limit generator output to its rated capacity.
    """

    requested_kw = max(0.0, requested_kw)

    if generator_id == "G1":
        rated_kw = config.GENERATOR_1_RATED_KW
    elif generator_id == "G2":
        rated_kw = config.GENERATOR_2_RATED_KW
    else:
        raise ValueError(f"Unknown generator: {generator_id}")

    return min(requested_kw, rated_kw)


def calculate_unmet_load(demand_kw, supplied_kw):
    """
    Calculate remaining load that could not be supplied.
    """

    demand_kw = max(0.0, demand_kw)
    supplied_kw = max(0.0, supplied_kw)

    return max(0.0, demand_kw - supplied_kw)