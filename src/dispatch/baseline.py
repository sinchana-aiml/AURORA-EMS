# AURORA-EMS
# Member 4 — Baseline Diesel Dispatch
#
# Simple reference strategy used to compare against the optimized dispatcher.
# All values are simulated for prototype/research purposes.

import config


def diesel_first_dispatch(
    demand_kw,
    renewable_kw,
    generator_1_available=True,
    generator_2_available=True,
):
    """
    Simple diesel-first baseline dispatch.

    Returns the power assigned to:
      - renewable sources
      - generator 1
      - generator 2
      - unmet load
    """

    remaining_load_kw = max(0.0, demand_kw - renewable_kw)

    generator_1_kw = 0.0
    generator_2_kw = 0.0

    # Generator 1 serves the remaining load first.
    if generator_1_available and remaining_load_kw > 0:
        generator_1_kw = min(
            remaining_load_kw,
            config.GENERATOR_1_RATED_KW,
        )
        remaining_load_kw -= generator_1_kw

    # Generator 2 serves anything G1 could not provide.
    if generator_2_available and remaining_load_kw > 0:
        generator_2_kw = min(
            remaining_load_kw,
            config.GENERATOR_2_RATED_KW,
        )
        remaining_load_kw -= generator_2_kw

    unmet_load_kw = max(0.0, remaining_load_kw)

    renewable_used_kw = min(demand_kw, renewable_kw)

    return {
        "renewable_used_kw": renewable_used_kw,
        "generator_1_kw": generator_1_kw,
        "generator_2_kw": generator_2_kw,
        "unmet_load_kw": unmet_load_kw,
    }