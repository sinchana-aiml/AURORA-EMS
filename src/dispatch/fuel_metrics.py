# AURORA-EMS
# Member 4 — Fuel Metrics
#
# Calculates simulated diesel fuel consumption
# for the dispatch outputs.

import config


def calculate_generator_fuel(generator_id, output_kw):
    """
    Calculate fuel used by a generator for one timestep.

    Fuel model:
        fuel = idle fuel + load-dependent fuel

    Returns fuel consumption in litres.
    """

    output_kw = max(0.0, output_kw)

    if generator_id == "G1":
        idle_fuel_lph = config.GENERATOR_1_IDLE_FUEL_LPH
        fuel_per_kwh = config.GENERATOR_1_FUEL_PER_KWH

    elif generator_id == "G2":
        idle_fuel_lph = config.GENERATOR_2_IDLE_FUEL_LPH
        fuel_per_kwh = config.GENERATOR_2_FUEL_PER_KWH

    else:
        raise ValueError(f"Unknown generator: {generator_id}")

    if output_kw <= 0:
        return 0.0

    fuel_used_l = (
        idle_fuel_lph * config.TIMESTEP_HOURS
        + fuel_per_kwh * output_kw * config.TIMESTEP_HOURS
    )

    return fuel_used_l


def calculate_total_fuel(generator_1_kw, generator_2_kw):
    """
    Calculate total diesel fuel consumed by both generators.
    """

    generator_1_fuel_l = calculate_generator_fuel(
        "G1",
        generator_1_kw,
    )

    generator_2_fuel_l = calculate_generator_fuel(
        "G2",
        generator_2_kw,
    )

    return {
        "generator_1_fuel_l": generator_1_fuel_l,
        "generator_2_fuel_l": generator_2_fuel_l,
        "total_fuel_l": generator_1_fuel_l + generator_2_fuel_l,
    }