# AURORA-EMS
# Member 4 — Fuel Metrics
#
# Fuel consumption and baseline-vs-optimized comparison metrics.
# All values are simulated for prototype/research purposes.

import config


def calculate_generator_fuel(generator_id, output_kw):
    """
    Calculate fuel consumed by one generator for one timestep.
    """

    output_kw = max(0.0, output_kw)

    if output_kw <= 0.0:
        return 0.0

    if generator_id == "G1":
        idle_fuel_lph = config.GENERATOR_1_IDLE_FUEL_LPH
        fuel_per_kwh = config.GENERATOR_1_FUEL_PER_KWH

    elif generator_id == "G2":
        idle_fuel_lph = config.GENERATOR_2_IDLE_FUEL_LPH
        fuel_per_kwh = config.GENERATOR_2_FUEL_PER_KWH

    else:
        raise ValueError(
            "generator_id must be 'G1' or 'G2'"
        )

    return (
        idle_fuel_lph
        + fuel_per_kwh * output_kw
    ) * config.TIMESTEP_HOURS


def calculate_total_fuel(
    generator_1_kw,
    generator_2_kw,
):
    """
    Calculate total fuel consumption for both generators.

    The original *_fuel_l keys are preserved because they are
    part of the existing Member 4 test/API contract.
    """

    generator_1_fuel_l = calculate_generator_fuel(
        "G1",
        generator_1_kw,
    )

    generator_2_fuel_l = calculate_generator_fuel(
        "G2",
        generator_2_kw,
    )

    total_fuel_l = (
        generator_1_fuel_l
        + generator_2_fuel_l
    )

    return {
        "generator_1_fuel_l": generator_1_fuel_l,
        "generator_2_fuel_l": generator_2_fuel_l,
        "total_fuel_l": total_fuel_l,

        # Descriptive aliases for newer code.
        "generator_1_fuel_litres": generator_1_fuel_l,
        "generator_2_fuel_litres": generator_2_fuel_l,
        "total_fuel_litres": total_fuel_l,
    }


def calculate_fuel_saved(
    baseline_fuel_litres,
    optimized_fuel_litres,
):
    """
    Compare optimized fuel consumption against baseline.
    """

    baseline_fuel_litres = max(
        0.0,
        baseline_fuel_litres,
    )

    optimized_fuel_litres = max(
        0.0,
        optimized_fuel_litres,
    )

    fuel_saved_liters = (
        baseline_fuel_litres
        - optimized_fuel_litres
    )

    if baseline_fuel_litres > 0.0:
        fuel_saved_pct = (
            fuel_saved_liters
            / baseline_fuel_litres
            * 100.0
        )
    else:
        fuel_saved_pct = 0.0

    return {
        "fuel_saved_liters": fuel_saved_liters,
        "fuel_saved_pct": fuel_saved_pct,
    }


def calculate_average_daily_fuel(
    total_fuel_litres,
    hours_simulated,
):
    """
    Convert simulated fuel consumption into average
    daily fuel consumption.
    """

    total_fuel_litres = max(
        0.0,
        total_fuel_litres,
    )

    hours_simulated = max(
        0.0,
        hours_simulated,
    )

    if hours_simulated <= 0.0:
        return 0.0

    return (
        total_fuel_litres
        / hours_simulated
        * 24.0
    )


def calculate_fuel_crisis_days(
    fuel_remaining_litres,
    average_daily_fuel_consumption_litres,
):
    """
    Estimate remaining fuel duration in days.

    Formula:
        fuel remaining / average daily consumption
    """

    fuel_remaining_litres = max(
        0.0,
        fuel_remaining_litres,
    )

    average_daily_fuel_consumption_litres = max(
        0.0,
        average_daily_fuel_consumption_litres,
    )

    if average_daily_fuel_consumption_litres <= 0.0:
        return float("inf")

    return (
        fuel_remaining_litres
        / average_daily_fuel_consumption_litres
    )