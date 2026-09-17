# AURORA-EMS
# Member 4 — Generator Failover
#
# Handles generator availability during dispatch.
# If one generator is unavailable, the other generator
# can take over the remaining load when possible.

import config


def dispatch_with_failover(
    remaining_load_kw,
    generator_1_available=True,
    generator_2_available=True,
):
    """
    Dispatch remaining load using available generators.

    Generator 1 is attempted first.
    Generator 2 supplies any remaining load.

    Returns generator outputs and unmet load.
    """

    remaining_load_kw = max(0.0, remaining_load_kw)

    generator_1_kw = 0.0
    generator_2_kw = 0.0

    # Try Generator 1 first.
    if generator_1_available and remaining_load_kw > 0:
        generator_1_kw = min(
            remaining_load_kw,
            config.GENERATOR_1_RATED_KW,
        )
        remaining_load_kw -= generator_1_kw

    # Generator 2 takes over any remaining load.
    if generator_2_available and remaining_load_kw > 0:
        generator_2_kw = min(
            remaining_load_kw,
            config.GENERATOR_2_RATED_KW,
        )
        remaining_load_kw -= generator_2_kw

    unmet_load_kw = max(0.0, remaining_load_kw)

    return {
        "generator_1_kw": generator_1_kw,
        "generator_2_kw": generator_2_kw,
        "unmet_load_kw": unmet_load_kw,
    }