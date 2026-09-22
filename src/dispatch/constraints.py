# AURORA-EMS
# Member 4 — Dispatch Constraints
#
# Centralized safety and physical constraints for energy dispatch.
# All values are simulated for prototype/research purposes.

import config


def minimum_battery_soc_kwh():
    """
    Return the minimum allowed battery SOC in kWh.

    config.BATTERY_MIN_SOC_FRACTION is a fraction
    (for example, 0.25 = 25%), not an energy value.
    """
    return (
        config.BATTERY_CAPACITY_KWH
        * config.BATTERY_MIN_SOC_FRACTION
    )


def limit_battery_discharge(
    requested_kw,
    battery_soc_kwh,
):
    """
    Limit battery discharge so that:
      - requested discharge is non-negative
      - battery never goes below minimum SOC
      - configured maximum discharge power is respected

    Returns the maximum permitted discharge power in kW.
    """

    requested_kw = max(0.0, requested_kw)
    battery_soc_kwh = max(0.0, battery_soc_kwh)

    minimum_soc_kwh = minimum_battery_soc_kwh()

    available_energy_kwh = max(
        0.0,
        battery_soc_kwh - minimum_soc_kwh,
    )

    # Convert available stored energy into deliverable power,
    # accounting for battery discharge efficiency.
    max_soc_limited_kw = (
        available_energy_kwh
        * config.BATTERY_DISCHARGE_EFFICIENCY
        / config.TIMESTEP_HOURS
    )

    return min(
        requested_kw,
        config.BATTERY_MAX_DISCHARGE_KW,
        max_soc_limited_kw,
    )


def limit_battery_charge(
    requested_kw,
    battery_soc_kwh,
):
    """
    Limit battery charging so that:
      - requested charge is non-negative
      - battery never exceeds maximum SOC
      - configured maximum charge power is respected

    Returns the permitted charging power in kW.
    """

    requested_kw = max(0.0, requested_kw)
    battery_soc_kwh = max(0.0, battery_soc_kwh)

    available_capacity_kwh = max(
        0.0,
        config.BATTERY_CAPACITY_KWH - battery_soc_kwh,
    )

    max_soc_limited_kw = (
        available_capacity_kwh
        / config.BATTERY_CHARGE_EFFICIENCY
        / config.TIMESTEP_HOURS
    )

    return min(
        requested_kw,
        config.BATTERY_MAX_CHARGE_KW,
        max_soc_limited_kw,
    )


def limit_generator_output(
    requested_kw,
    generator_id,
):
    """
    Limit generator output to its configured rated capacity.

    generator_id:
        "G1" or "G2"
    """

    requested_kw = max(0.0, requested_kw)

    if generator_id == "G1":
        rated_kw = config.GENERATOR_1_RATED_KW

    elif generator_id == "G2":
        rated_kw = config.GENERATOR_2_RATED_KW

    else:
        raise ValueError(
            "generator_id must be 'G1' or 'G2'"
        )

    return min(
        requested_kw,
        rated_kw,
    )


def generator_minimum_output(generator_id):
    """
    Return the configured minimum stable output of a generator.
    """

    if generator_id == "G1":
        return config.GENERATOR_1_MINIMUM_KW

    if generator_id == "G2":
        return config.GENERATOR_2_MINIMUM_KW

    raise ValueError(
        "generator_id must be 'G1' or 'G2'"
    )


def calculate_unmet_load(
    demand_kw,
    supplied_kw,
):
    """
    Calculate remaining unmet load.

    Both values are clamped to non-negative values.
    """

    demand_kw = max(0.0, demand_kw)
    supplied_kw = max(0.0, supplied_kw)

    return max(
        0.0,
        demand_kw - supplied_kw,
    )


def critical_load_is_served(
    supplied_kw,
    critical_load_kw=None,
):
    """
    Check whether the critical load is supplied.

    If critical_load_kw is omitted, the project configuration
    value is used.
    """

    supplied_kw = max(0.0, supplied_kw)

    if critical_load_kw is None:
        critical_load_kw = config.CRITICAL_LOAD_KW

    critical_load_kw = max(
        0.0,
        critical_load_kw,
    )

    return supplied_kw >= critical_load_kw


def fuel_is_available(
    required_fuel_litres,
    fuel_remaining_litres,
):
    """
    Check whether enough fuel is available for a dispatch step.
    """

    required_fuel_litres = max(
        0.0,
        required_fuel_litres,
    )

    fuel_remaining_litres = max(
        0.0,
        fuel_remaining_litres,
    )

    return required_fuel_litres <= fuel_remaining_litres


def renewable_used_is_valid(
    renewable_used_kw,
    renewable_available_kw,
):
    """
    Verify that renewable dispatch does not exceed availability.
    """

    renewable_used_kw = max(
        0.0,
        renewable_used_kw,
    )

    renewable_available_kw = max(
        0.0,
        renewable_available_kw,
    )

    return renewable_used_kw <= renewable_available_kw


def battery_soc_is_valid(
    battery_soc_kwh,
):
    """
    Verify that battery SOC remains within configured limits.
    """

    minimum_soc_kwh = minimum_battery_soc_kwh()

    return (
        minimum_soc_kwh
        <= battery_soc_kwh
        <= config.BATTERY_CAPACITY_KWH
    )