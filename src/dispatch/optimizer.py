# AURORA-EMS
# Member 4 — Optimized Energy Dispatch
#
# Two dispatch strategies are provided:
#
#   optimized_dispatch(...)
#       Single-hour rule-based dispatch (kept for backward compatibility
#       with existing tests and the per-hour scenario runner).
#
#   optimized_dispatch_lookahead(records, initial_soc_kwh,
#                                initial_fuel_litres, ...)
#       24-hour dynamic-programming optimizer.
#       Minimises TOTAL diesel fuel over the complete horizon by choosing,
#       for every hour, the cheapest feasible combination of:
#           - battery discharge / charge
#           - G1 on/off and output level
#           - G2 on/off and output level
#           - flexible-load shedding
#       subject to all physical and operational constraints from config.py.
#
# All values are simulated for prototype/research purposes.

import config

from src.dispatch.constraints import (
    calculate_unmet_load,
    critical_load_is_served,
    fuel_is_available,
    limit_battery_discharge,
    limit_generator_output,
    minimum_battery_soc_kwh,
)


# ---------------------------------------------------------------------------
# Internal helpers shared by both strategies
# ---------------------------------------------------------------------------

def _gen_fuel(gen_id, output_kw):
    """Fuel consumed by one generator for one timestep (litres)."""
    output_kw = max(0.0, output_kw)
    if output_kw <= 0.0:
        return 0.0
    if gen_id == "G1":
        return (config.GENERATOR_1_IDLE_FUEL_LPH
                + config.GENERATOR_1_FUEL_PER_KWH * output_kw
                ) * config.TIMESTEP_HOURS
    if gen_id == "G2":
        return (config.GENERATOR_2_IDLE_FUEL_LPH
                + config.GENERATOR_2_FUEL_PER_KWH * output_kw
                ) * config.TIMESTEP_HOURS
    raise ValueError("gen_id must be 'G1' or 'G2'")


def _low_fuel_mode(fuel_remaining_litres):
    return fuel_remaining_litres <= config.LOW_FUEL_THRESHOLD_L


def _battery_discharge_kwh_removed(discharge_kw):
    """Energy removed from battery (kWh) for a given bus-side discharge."""
    return (discharge_kw * config.TIMESTEP_HOURS
            / config.BATTERY_DISCHARGE_EFFICIENCY)


def _battery_charge_kwh_added(charge_kw):
    """Energy added to battery (kWh) for a given bus-side charge."""
    return (charge_kw * config.TIMESTEP_HOURS
            * config.BATTERY_CHARGE_EFFICIENCY)


# ---------------------------------------------------------------------------
# Dynamic-programming optimizer — 24-hour look-ahead
# ---------------------------------------------------------------------------

# SOC discretisation step (kWh).  Smaller = more accurate but slower.
_SOC_STEP = 5.0


def _soc_to_idx(soc_kwh):
    return int(round(soc_kwh / _SOC_STEP))


def _idx_to_soc(idx):
    return idx * _SOC_STEP


def _feasible_actions(
    demand_kw,
    renewable_kw,
    soc_kwh,
    fuel_remaining_litres,
    g1_available,
    g2_available,
    low_fuel,
):
    """
    Enumerate every feasible dispatch action for one hour.

    An action is a dict:
        shed_flexible  : bool
        g1_kw          : float  (0 = off)
        g2_kw          : float  (0 = off)
        battery_kw     : float  (positive = discharge, negative = charge)
        fuel_cost      : float  (litres)
        new_soc        : float  (kWh, snapped to grid)
        unmet_kw       : float
        critical_ok    : bool
    """
    min_soc = minimum_battery_soc_kwh()
    max_soc = config.BATTERY_CAPACITY_KWH
    max_dis = config.BATTERY_MAX_DISCHARGE_KW
    max_chg = config.BATTERY_MAX_CHARGE_KW
    eff_d   = config.BATTERY_DISCHARGE_EFFICIENCY
    eff_c   = config.BATTERY_CHARGE_EFFICIENCY
    ts      = config.TIMESTEP_HOURS

    actions = []

    # Flexible-load shedding options
    shed_options = [True] if low_fuel else [False, True]

    # Generator output candidates (kW): 0 = off, else min..rated
    def gen_candidates(available, min_kw, rated_kw):
        if not available:
            return [0.0]
        # off, minimum, midpoint, rated — enough resolution without explosion
        return [0.0, min_kw, (min_kw + rated_kw) / 2.0, rated_kw]

    g1_candidates = gen_candidates(
        g1_available,
        config.GENERATOR_1_MINIMUM_KW,
        config.GENERATOR_1_RATED_KW,
    )
    g2_candidates = gen_candidates(
        g2_available,
        config.GENERATOR_2_MINIMUM_KW,
        config.GENERATOR_2_RATED_KW,
    )

    for shed in shed_options:
        effective_demand = demand_kw
        if shed:
            effective_demand = max(
                config.CRITICAL_LOAD_KW,
                demand_kw - config.FLEXIBLE_LOAD_KW,
            )

        # Renewable covers as much as possible
        renew_used = min(effective_demand, renewable_kw)
        after_renew = effective_demand - renew_used
        renew_surplus = renewable_kw - renew_used

        for g1_kw in g1_candidates:
            for g2_kw in g2_candidates:
                gen_total = g1_kw + g2_kw

                # Total supply from generators + renewables
                total_supply = renew_used + gen_total

                # Battery role: positive = discharge to cover gap,
                #               negative = charge from surplus
                gap = effective_demand - total_supply  # positive = need more

                if gap > 0.0:
                    # Need battery to discharge
                    avail_batt_energy = max(0.0, soc_kwh - min_soc)
                    max_dis_power = min(
                        max_dis,
                        avail_batt_energy * eff_d / ts,
                    )
                    batt_kw = min(gap, max_dis_power)
                    charge_kw = 0.0
                else:
                    # Surplus — charge battery
                    batt_kw = 0.0
                    surplus = -gap  # positive surplus
                    # Also add any renewable surplus not used for load
                    surplus += renew_surplus
                    avail_cap = max(0.0, max_soc - soc_kwh)
                    max_chg_power = min(
                        max_chg,
                        avail_cap / (eff_c * ts),
                    )
                    charge_kw = min(surplus, max_chg_power)

                # New SOC
                new_soc = soc_kwh
                if batt_kw > 0.0:
                    new_soc -= _battery_discharge_kwh_removed(batt_kw)
                if charge_kw > 0.0:
                    new_soc += _battery_charge_kwh_added(charge_kw)
                new_soc = max(min_soc, min(max_soc, new_soc))

                # Snap to discretisation grid
                new_soc_snapped = _idx_to_soc(_soc_to_idx(new_soc))
                new_soc_snapped = max(min_soc, min(max_soc, new_soc_snapped))

                # Unmet load
                supplied = renew_used + gen_total + batt_kw
                unmet = max(0.0, effective_demand - supplied)

                # Fuel cost
                fuel_g1 = _gen_fuel("G1", g1_kw)
                fuel_g2 = _gen_fuel("G2", g2_kw)
                fuel_cost = fuel_g1 + fuel_g2

                # Skip if not enough fuel
                if fuel_cost > fuel_remaining_litres + 1e-6:
                    continue

                # Critical load check
                critical_ok = critical_load_is_served(
                    supplied - unmet,
                    config.CRITICAL_LOAD_KW,
                )

                # Reject any action that leaves unmet load when
                # generators are available and have fuel.
                # This makes the DP always prefer serving load over
                # saving fuel at the cost of unmet demand.
                if unmet > 1e-3 and (g1_kw > 0.0 or g2_kw > 0.0):
                    # Generator is running but still unmet — only
                    # accept if both generators are at rated capacity
                    max_possible = (renew_used + gen_total
                                    + min(config.BATTERY_MAX_DISCHARGE_KW,
                                          max(0.0, soc_kwh - min_soc)
                                          * config.BATTERY_DISCHARGE_EFFICIENCY
                                          / config.TIMESTEP_HOURS))
                    if max_possible > effective_demand + 1e-3:
                        continue  # could have served more — skip

                # Assign a large penalty cost for unmet load so the DP
                # always prefers serving demand over saving fuel.
                # 1000 L per kW of unmet load >> any real fuel cost.
                effective_cost = fuel_cost + unmet * 1000.0

                actions.append({
                    "shed_flexible": shed,
                    "g1_kw":         g1_kw,
                    "g2_kw":         g2_kw,
                    "battery_kw":    batt_kw,
                    "charge_kw":     charge_kw,
                    "renew_used":    renew_used,
                    "fuel_cost":     fuel_cost,
                    "dp_cost":       effective_cost,
                    "new_soc":       new_soc_snapped,
                    "unmet_kw":      unmet,
                    "critical_ok":   critical_ok,
                    "fuel_g1":       fuel_g1,
                    "fuel_g2":       fuel_g2,
                })

    return actions


def optimized_dispatch_lookahead(
    records,
    initial_soc_kwh,
    initial_fuel_litres,
    generator_1_available=True,
    generator_2_available=True,
    storm_mode=False,
    communication_loss=False,
    forecast_confidence=None,
):
    """
    24-hour dynamic-programming optimizer.

    Minimises total diesel fuel over the complete horizon.

    Parameters
    ----------
    records : list of dicts
        Output of adapt_digital_twin_results() — one dict per hour.
    initial_soc_kwh : float
        Battery SOC at the start of Hour 0.
    initial_fuel_litres : float
        Fuel available at the start of Hour 0.
    generator_1_available, generator_2_available : bool
        Generator availability flags (failure scenarios).
    storm_mode : bool
        If True, renewable generation is reduced to 60 %.
    communication_loss : bool
        If True, G2 is treated as unavailable (safe-mode assumption).
    forecast_confidence : str or None
        "high" / "medium" / "low" / None — adjusts battery reserve.

    Returns
    -------
    list of per-hour result dicts (same schema as optimized_dispatch).
    """

    # ------------------------------------------------------------------
    # Forecast confidence → battery reserve multiplier
    # ------------------------------------------------------------------
    _reserve_mult = {"high": 1.00, "medium": 1.10, "low": 1.25}
    reserve_mult = _reserve_mult.get(forecast_confidence, 1.00)
    min_soc_base = minimum_battery_soc_kwh() * reserve_mult
    min_soc_base = min(min_soc_base, config.BATTERY_CAPACITY_KWH)

    # ------------------------------------------------------------------
    # Prepare per-hour demand and renewable arrays
    # ------------------------------------------------------------------
    n = len(records)
    demands = []
    renewables = []
    for rec in records:
        ren = rec["renewable_available_kw"]
        if storm_mode:
            ren *= 0.60
        demands.append(rec["load_total_kw"])
        renewables.append(ren)

    g2_avail = generator_2_available and not communication_loss

    # ------------------------------------------------------------------
    # SOC state space
    # ------------------------------------------------------------------
    soc_min_idx = _soc_to_idx(min_soc_base)
    soc_max_idx = _soc_to_idx(config.BATTERY_CAPACITY_KWH)
    n_states = soc_max_idx + 1

    INF = float("inf")

    # dp[t][soc_idx] = minimum total fuel from hour t onward,
    #                  starting with this SOC.
    # We also store the best action at each state for reconstruction.
    dp   = [[INF] * n_states for _ in range(n + 1)]
    best = [[None] * n_states for _ in range(n)]

    # Terminal condition: any SOC at end of horizon costs 0 future fuel
    for s in range(n_states):
        dp[n][s] = 0.0

    # ------------------------------------------------------------------
    # Backward pass
    # ------------------------------------------------------------------
    # Fuel is a continuous variable — we track it implicitly by summing
    # costs along the chosen path.  The DP state is SOC only; fuel is
    # assumed sufficient (checked per action).  We do a separate
    # feasibility pass for fuel in the forward reconstruction.

    for t in range(n - 1, -1, -1):
        demand  = demands[t]
        renew   = renewables[t]
        # Approximate fuel remaining for feasibility: use full tank
        # (exact fuel is enforced in the forward pass)
        fuel_approx = config.FUEL_TANK_LITRES

        for s_idx in range(soc_min_idx, n_states):
            soc = _idx_to_soc(s_idx)
            low_fuel = False  # conservative: don't shed in planning pass

            actions = _feasible_actions(
                demand, renew, soc, fuel_approx,
                generator_1_available, g2_avail, low_fuel,
            )

            best_cost = INF
            best_act  = None

            for act in actions:
                ns_idx = _soc_to_idx(act["new_soc"])
                ns_idx = max(soc_min_idx, min(soc_max_idx, ns_idx))
                future  = dp[t + 1][ns_idx]
                if future == INF:
                    continue
                total = act["dp_cost"] + future
                if total < best_cost:
                    best_cost = total
                    best_act  = act

            dp[t][s_idx]   = best_cost if best_act is not None else INF
            best[t][s_idx] = best_act

    # ------------------------------------------------------------------
    # Forward pass — reconstruct the optimal schedule with exact fuel
    # ------------------------------------------------------------------
    results = []
    soc_kwh  = initial_soc_kwh
    fuel_rem = initial_fuel_litres

    for t in range(n):
        demand = demands[t]
        renew  = renewables[t]
        low_fuel = _low_fuel_mode(fuel_rem)

        s_idx = _soc_to_idx(soc_kwh)
        s_idx = max(soc_min_idx, min(soc_max_idx, s_idx))

        act = best[t][s_idx]

        # If the DP action is infeasible due to actual fuel, fall back
        # to a safe greedy action for this hour only.
        if act is None or act["fuel_cost"] > fuel_rem + 1e-6:
            fallback_actions = _feasible_actions(
                demand, renew, soc_kwh, fuel_rem,
                generator_1_available, g2_avail, low_fuel,
            )
            # Pick lowest fuel cost among feasible fallbacks
            fallback_actions.sort(key=lambda a: (a["unmet_kw"], a["fuel_cost"]))
            act = fallback_actions[0] if fallback_actions else None

        if act is None:
            # Absolute fallback: renewables only
            renew_used = min(demand, renew)
            unmet = max(0.0, demand - renew_used)
            act = {
                "shed_flexible": False,
                "g1_kw": 0.0, "g2_kw": 0.0,
                "battery_kw": 0.0, "charge_kw": 0.0,
                "renew_used": renew_used,
                "fuel_cost": 0.0, "fuel_g1": 0.0, "fuel_g2": 0.0,
                "new_soc": soc_kwh,
                "unmet_kw": unmet,
                "critical_ok": critical_load_is_served(renew_used),
            }

        # Apply action with exact fuel tracking
        fuel_used = min(act["fuel_cost"], fuel_rem)
        fuel_rem  = max(0.0, fuel_rem - fuel_used)

        # Recompute exact new SOC (not snapped)
        new_soc = soc_kwh
        if act["battery_kw"] > 0.0:
            new_soc -= _battery_discharge_kwh_removed(act["battery_kw"])
        if act["charge_kw"] > 0.0:
            new_soc += _battery_charge_kwh_added(act["charge_kw"])
        new_soc = max(minimum_battery_soc_kwh(),
                      min(config.BATTERY_CAPACITY_KWH, new_soc))

        supplied = act["renew_used"] + act["g1_kw"] + act["g2_kw"] + act["battery_kw"]
        unmet    = max(0.0, (max(config.CRITICAL_LOAD_KW,
                                 demand - (config.FLEXIBLE_LOAD_KW
                                           if act["shed_flexible"] else 0.0))
                             if act["shed_flexible"] else demand) - supplied)
        unmet    = max(0.0, unmet)

        effective_demand = demand
        if act["shed_flexible"]:
            effective_demand = max(config.CRITICAL_LOAD_KW,
                                   demand - config.FLEXIBLE_LOAD_KW)

        critical_ok = critical_load_is_served(
            supplied - unmet, config.CRITICAL_LOAD_KW
        )

        results.append({
            "renewable_used_kw":    round(act["renew_used"], 4),
            "renewable_curtailed_kw": round(
                max(0.0, renew - act["renew_used"] - act["charge_kw"]), 4),
            "battery_discharge_kw": round(act["battery_kw"], 4),
            "battery_charge_kw":    round(act["charge_kw"], 4),
            "battery_soc_kwh":      round(new_soc, 4),
            "generator_1_kw":       round(act["g1_kw"], 4),
            "generator_2_kw":       round(act["g2_kw"], 4),
            "generator_total_kw":   round(act["g1_kw"] + act["g2_kw"], 4),
            "fuel_used_litres":     round(fuel_used, 4),
            "fuel_remaining_litres": round(fuel_rem, 4),
            "unmet_load_kw":        round(unmet, 4),
            "critical_load_served": critical_ok,
            "battery_reserve_kwh":  round(minimum_battery_soc_kwh(), 4),
            "low_fuel_mode":        low_fuel,
            "flexible_load_shed_kw": (config.FLEXIBLE_LOAD_KW
                                      if act["shed_flexible"] else 0.0),
        })

        soc_kwh = new_soc

    return results


# ---------------------------------------------------------------------------
# Single-hour rule-based dispatch (kept for backward compatibility)
# ---------------------------------------------------------------------------

def _fuel_limited_generator_output(generator_id, requested_kw,
                                    fuel_remaining_litres):
    requested_kw = max(0.0, requested_kw)
    fuel_remaining_litres = max(0.0, fuel_remaining_litres)
    if requested_kw <= 0.0 or fuel_remaining_litres <= 0.0:
        return 0.0, 0.0

    requested_kw = limit_generator_output(requested_kw, generator_id)

    if generator_id == "G1":
        idle = config.GENERATOR_1_IDLE_FUEL_LPH
        rate = config.GENERATOR_1_FUEL_PER_KWH
        min_kw = config.GENERATOR_1_MINIMUM_KW
    else:
        idle = config.GENERATOR_2_IDLE_FUEL_LPH
        rate = config.GENERATOR_2_FUEL_PER_KWH
        min_kw = config.GENERATOR_2_MINIMUM_KW

    required = _gen_fuel(generator_id, requested_kw)
    if fuel_is_available(required, fuel_remaining_litres):
        return requested_kw, required

    ts = config.TIMESTEP_HOURS
    max_out = max(0.0, (fuel_remaining_litres / ts - idle) / rate)
    output = min(requested_kw, max_out)
    if 0.0 < output < min_kw:
        return 0.0, 0.0
    fuel = min(_gen_fuel(generator_id, output), fuel_remaining_litres)
    return output, fuel


def optimized_dispatch(
    demand_kw,
    renewable_kw,
    battery_soc_kwh,
    generator_1_available=True,
    generator_2_available=True,
    fuel_remaining_litres=None,
    forecast_confidence=None,
):
    """
    Single-hour rule-based dispatch (backward-compatible).

    For genuine fuel minimisation use optimized_dispatch_lookahead().
    """
    demand_kw = max(0.0, demand_kw)
    renewable_kw = max(0.0, renewable_kw)
    battery_soc_kwh = max(0.0, battery_soc_kwh)

    if fuel_remaining_litres is None:
        fuel_remaining_litres = config.FUEL_TANK_LITRES
    fuel_remaining_litres = max(0.0, fuel_remaining_litres)

    _reserve_mult = {"high": 1.00, "medium": 1.10, "low": 1.25}
    reserve_mult = _reserve_mult.get(forecast_confidence, 1.00)
    minimum_soc_kwh = minimum_battery_soc_kwh() * reserve_mult
    minimum_soc_kwh = min(minimum_soc_kwh, config.BATTERY_CAPACITY_KWH)

    low_fuel = _low_fuel_mode(fuel_remaining_litres)
    if low_fuel:
        demand_kw = max(config.CRITICAL_LOAD_KW,
                        demand_kw - config.FLEXIBLE_LOAD_KW)
    flexible_load_shed_kw = config.FLEXIBLE_LOAD_KW if low_fuel else 0.0

    renewable_used_kw = min(demand_kw, renewable_kw)
    remaining_load_kw = calculate_unmet_load(demand_kw, renewable_used_kw)
    renewable_curtailed_kw = max(0.0, renewable_kw - renewable_used_kw)

    battery_discharge_kw = 0.0
    if remaining_load_kw > 0.0:
        battery_discharge_kw = limit_battery_discharge(
            remaining_load_kw, battery_soc_kwh)
        battery_soc_kwh -= _battery_discharge_kwh_removed(battery_discharge_kw)
        battery_soc_kwh = max(minimum_soc_kwh, battery_soc_kwh)
        remaining_load_kw -= battery_discharge_kw

    generator_1_kw = 0.0
    if generator_1_available and remaining_load_kw > 0.0:
        req = limit_generator_output(remaining_load_kw, "G1")
        generator_1_kw, fuel_used = _fuel_limited_generator_output(
            "G1", req, fuel_remaining_litres)
        fuel_remaining_litres -= fuel_used
        remaining_load_kw -= generator_1_kw

    generator_2_kw = 0.0
    if generator_2_available and remaining_load_kw > 0.0:
        req = limit_generator_output(remaining_load_kw, "G2")
        generator_2_kw, fuel_used = _fuel_limited_generator_output(
            "G2", req, fuel_remaining_litres)
        fuel_remaining_litres -= fuel_used
        remaining_load_kw -= generator_2_kw

    unmet_load_kw = max(0.0, remaining_load_kw)
    generator_total_kw = generator_1_kw + generator_2_kw
    total_fuel = (_gen_fuel("G1", generator_1_kw)
                  + _gen_fuel("G2", generator_2_kw))
    fuel_remaining_litres = max(0.0, fuel_remaining_litres)
    supplied_load_kw = demand_kw - unmet_load_kw
    critical_load_served = critical_load_is_served(
        supplied_load_kw, config.CRITICAL_LOAD_KW)

    return {
        "renewable_used_kw":      renewable_used_kw,
        "renewable_curtailed_kw": renewable_curtailed_kw,
        "battery_discharge_kw":   battery_discharge_kw,
        "battery_soc_kwh":        battery_soc_kwh,
        "generator_1_kw":         generator_1_kw,
        "generator_2_kw":         generator_2_kw,
        "generator_total_kw":     generator_total_kw,
        "fuel_used_litres":       total_fuel,
        "fuel_remaining_litres":  fuel_remaining_litres,
        "unmet_load_kw":          unmet_load_kw,
        "critical_load_served":   critical_load_served,
        "battery_reserve_kwh":    minimum_soc_kwh,
        "low_fuel_mode":          low_fuel,
        "flexible_load_shed_kw":  flexible_load_shed_kw,
    }
