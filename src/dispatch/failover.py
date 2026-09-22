# AURORA-EMS
# Member 4 — Generator Failover
#
# Handles generator availability and physical operating limits.
# Generator minimum/rated limits come from config.py.
#
# This module does not calculate fuel consumption.
# Fuel accounting is handled by the dispatch layer.

import config


def _dispatch_single_generator(
    remaining_load_kw,
    minimum_kw,
    rated_kw,
):
    """
    Dispatch one available generator.

    If load is positive but below the generator's minimum operating
    level, the generator runs at its minimum output. Any resulting
    excess power is reported separately.
    """

    remaining_load_kw = max(0.0, remaining_load_kw)

    if remaining_load_kw <= 0:
        return 0.0, 0.0

    output_kw = min(remaining_load_kw, rated_kw)

    # A running generator must respect its minimum operating level.
    if output_kw > 0 and output_kw < minimum_kw:
        output_kw = minimum_kw

    excess_kw = max(0.0, output_kw - remaining_load_kw)

    return output_kw, excess_kw


def dispatch_with_failover(
    remaining_load_kw,
    generator_1_available=True,
    generator_2_available=True,
):
    """
    Dispatch remaining load using available generators.

    Priority:
      1. Generator 1
      2. Generator 2

    The function respects each generator's minimum and rated output.

    Returns
    -------
    dict
        generator_1_kw
        generator_2_kw
        generator_total_kw
        excess_generation_kw
        unmet_load_kw
    """

    remaining_load_kw = max(0.0, remaining_load_kw)

    generator_1_kw = 0.0
    generator_2_kw = 0.0
    excess_generation_kw = 0.0

    # Generator 1
    if generator_1_available and remaining_load_kw > 0:
        generator_1_kw, excess_g1_kw = _dispatch_single_generator(
            remaining_load_kw,
            config.GENERATOR_1_MINIMUM_KW,
            config.GENERATOR_1_RATED_KW,
        )

        remaining_load_kw = max(
            0.0,
            remaining_load_kw - generator_1_kw,
        )
        excess_generation_kw += excess_g1_kw

    # Generator 2 takes over if load remains.
    if generator_2_available and remaining_load_kw > 0:
        generator_2_kw, excess_g2_kw = _dispatch_single_generator(
            remaining_load_kw,
            config.GENERATOR_2_MINIMUM_KW,
            config.GENERATOR_2_RATED_KW,
        )

        remaining_load_kw = max(
            0.0,
            remaining_load_kw - generator_2_kw,
        )
        excess_generation_kw += excess_g2_kw

    unmet_load_kw = max(0.0, remaining_load_kw)

    return {
        "generator_1_kw": generator_1_kw,
        "generator_2_kw": generator_2_kw,
        "generator_total_kw": generator_1_kw + generator_2_kw,
        "excess_generation_kw": excess_generation_kw,
        "unmet_load_kw": unmet_load_kw,
    }