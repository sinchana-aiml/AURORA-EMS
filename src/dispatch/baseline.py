# AURORA-EMS
# Member 4 — Baseline Diesel Dispatch
#
# Reference strategy used to compare against the optimized dispatcher.
# All values are simulated for prototype/research purposes.

import config


def _minimum_battery_soc_kwh():
    """Return the battery's minimum allowed SOC in kWh."""
    return (
        config.BATTERY_CAPACITY_KWH
        * config.BATTERY_MIN_SOC_FRACTION
    )


def diesel_first_dispatch(
    demand_kw,
    renewable_kw,
    generator_1_available=True,
    generator_2_available=True,
):
    """
    Simple diesel-first baseline dispatch.

    Dispatch order:
      1. Renewable energy
      2. Generator 1
      3. Generator 2
      4. Unmet load
    """

    demand_kw = max(0.0, demand_kw)
    renewable_kw = max(0.0, renewable_kw)

    renewable_used_kw = min(demand_kw, renewable_kw)
    remaining_load_kw = demand_kw - renewable_used_kw

    generator_1_kw = 0.0
    generator_2_kw = 0.0

    if generator_1_available and remaining_load_kw > 0:
        generator_1_kw = min(
            remaining_load_kw,
            config.GENERATOR_1_RATED_KW,
        )
        remaining_load_kw -= generator_1_kw

    if generator_2_available and remaining_load_kw > 0:
        generator_2_kw = min(
            remaining_load_kw,
            config.GENERATOR_2_RATED_KW,
        )
        remaining_load_kw -= generator_2_kw

    unmet_load_kw = max(0.0, remaining_load_kw)

    return {
        "renewable_used_kw": renewable_used_kw,
        "generator_1_kw": generator_1_kw,
        "generator_2_kw": generator_2_kw,
        "unmet_load_kw": unmet_load_kw,
    }


def baseline_dispatch_step(
    demand_kw,
    renewable_kw,
    battery_soc_kwh,
    fuel_remaining_litres,
    generator_1_available=True,
    generator_2_available=True,
):
    """
    Full baseline dispatch step with battery and fuel tracking.

    Dispatch order:
      1. Renewable energy
      2. Battery discharge
      3. Generator 1
      4. Generator 2
      5. Unmet load

    Battery SOC is always handled in kWh.
    """

    demand_kw = max(0.0, demand_kw)
    renewable_kw = max(0.0, renewable_kw)
    battery_soc_kwh = max(0.0, battery_soc_kwh)
    fuel_remaining_litres = max(0.0, fuel_remaining_litres)

    minimum_soc_kwh = _minimum_battery_soc_kwh()

    # ---------------------------------------------------------
    # 1. Renewable energy
    # ---------------------------------------------------------
    renewable_used_kw = min(demand_kw, renewable_kw)
    remaining_load_kw = demand_kw - renewable_used_kw

    # ---------------------------------------------------------
    # 2. Battery discharge
    # ---------------------------------------------------------
    battery_discharge_kw = 0.0

    available_battery_energy_kwh = max(
        0.0,
        battery_soc_kwh - minimum_soc_kwh,
    )

    max_battery_discharge_kw = min(
        config.BATTERY_MAX_DISCHARGE_KW,
        available_battery_energy_kwh / config.TIMESTEP_HOURS,
    )

    battery_discharge_kw = min(
        remaining_load_kw,
        max_battery_discharge_kw,
    )

    # Account for battery discharge efficiency.
    battery_energy_removed_kwh = (
        battery_discharge_kw
        * config.TIMESTEP_HOURS
        / config.BATTERY_DISCHARGE_EFFICIENCY
    )

    battery_soc_kwh -= battery_energy_removed_kwh
    battery_soc_kwh = max(
        minimum_soc_kwh,
        battery_soc_kwh,
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
    # 5. Fuel consumption
    # ---------------------------------------------------------
    generator_1_fuel_litres = 0.0
    generator_2_fuel_litres = 0.0

    if generator_1_kw > 0:
        generator_1_fuel_litres = (
            config.GENERATOR_1_IDLE_FUEL_LPH
            + config.GENERATOR_1_FUEL_PER_KWH * generator_1_kw
        ) * config.TIMESTEP_HOURS

    if generator_2_kw > 0:
        generator_2_fuel_litres = (
            config.GENERATOR_2_IDLE_FUEL_LPH
            + config.GENERATOR_2_FUEL_PER_KWH * generator_2_kw
        ) * config.TIMESTEP_HOURS

    fuel_required_litres = (
        generator_1_fuel_litres
        + generator_2_fuel_litres
    )

    fuel_used_litres = min(
        fuel_required_litres,
        fuel_remaining_litres,
    )

    fuel_remaining_litres = max(
        0.0,
        fuel_remaining_litres - fuel_used_litres,
    )

    # ---------------------------------------------------------
    # 6. Final unmet load
    # ---------------------------------------------------------
    unmet_load_kw = max(
        0.0,
        remaining_load_kw,
    )

    critical_load_served = (
        demand_kw <= 0.0
        or unmet_load_kw <= 0.0
        or demand_kw - unmet_load_kw >= config.CRITICAL_LOAD_KW
    )

    return {
        "renewable_used_kw": renewable_used_kw,
        "battery_discharge_kw": battery_discharge_kw,
        "battery_soc_kwh": battery_soc_kwh,
        "generator_1_kw": generator_1_kw,
        "generator_2_kw": generator_2_kw,
        "generator_total_kw": (
            generator_1_kw + generator_2_kw
        ),
        "fuel_used_litres": fuel_used_litres,
        "fuel_remaining_litres": fuel_remaining_litres,
        "unmet_load_kw": unmet_load_kw,
        "critical_load_served": critical_load_served,
    }