# AURORA-EMS
# Member 4 — Optimized Energy Dispatch
#
# Prototype dispatch strategy:
# 1. Use renewable energy first.
# 2. Use the battery for the remaining load.
# 3. Use generators only when necessary.
# 4. Keep generator decisions modular for future forecasting integration.

import config


def optimized_dispatch(
    demand_kw,
    renewable_kw,
    battery_soc_kwh,
    generator_1_available=True,
    generator_2_available=True,
):
    """
    Optimized dispatch for one simulation timestep.

    Parameters
    ----------
    demand_kw : float
        Current electrical demand.

    renewable_kw : float
        Available renewable generation.

    battery_soc_kwh : float
        Current battery state of charge.

    generator_1_available : bool
        Whether Generator 1 is available.

    generator_2_available : bool
        Whether Generator 2 is available.

    Returns
    -------
    dict
        Power supplied by renewables, battery, and generators,
        along with remaining unmet load and updated battery SOC.
    """

    # Start with safe non-negative values.
    demand_kw = max(0.0, demand_kw)
    renewable_kw = max(0.0, renewable_kw)
    battery_soc_kwh = max(0.0, battery_soc_kwh)

    # ---------------------------------------------------------
    # 1. Renewable energy
    # ---------------------------------------------------------

    renewable_used_kw = min(demand_kw, renewable_kw)

    remaining_load_kw = demand_kw - renewable_used_kw

    # ---------------------------------------------------------
    # 2. Battery
    # ---------------------------------------------------------

    battery_discharge_kw = 0.0

    if remaining_load_kw > 0:
        available_battery_energy_kwh = max(
            0.0,
            battery_soc_kwh - config.BATTERY_MIN_SOC,
        )

        max_battery_discharge_kw = min(
            config.BATTERY_MAX_DISCHARGE_KW,
            available_battery_energy_kwh / config.TIMESTEP_HOURS,
        )

        battery_discharge_kw = min(
            remaining_load_kw,
            max_battery_discharge_kw,
        )

        battery_soc_kwh -= (
            battery_discharge_kw
            * config.TIMESTEP_HOURS
            / config.BATTERY_DISCHARGE_EFFICIENCY
        )

        remaining_load_kw -= battery_discharge_kw

    # ---------------------------------------------------------
    # 3. Generator 1
    # ---------------------------------------------------------

    generator_1_kw = 0.0

    if generator_1_available and remaining_load_kw > 0:
        generator_1_kw = min(
            remaining_load_kw,
            config.GENERATOR_1_RATED_KW,
        )

        remaining_load_kw -= generator_1_kw

    # ---------------------------------------------------------
    # 4. Generator 2
    # ---------------------------------------------------------

    generator_2_kw = 0.0

    if generator_2_available and remaining_load_kw > 0:
        generator_2_kw = min(
            remaining_load_kw,
            config.GENERATOR_2_RATED_KW,
        )

        remaining_load_kw -= generator_2_kw

    # ---------------------------------------------------------
    # 5. Final unmet load
    # ---------------------------------------------------------

    unmet_load_kw = max(0.0, remaining_load_kw)

    return {
        "renewable_used_kw": renewable_used_kw,
        "battery_discharge_kw": battery_discharge_kw,
        "generator_1_kw": generator_1_kw,
        "generator_2_kw": generator_2_kw,
        "unmet_load_kw": unmet_load_kw,
        "battery_soc_kwh": battery_soc_kwh,
    }