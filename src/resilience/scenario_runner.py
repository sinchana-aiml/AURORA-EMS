# src/resilience/scenario_runner.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Combined Resilience Scenario Runner
# Member: Resilience & Offline Integration
#
# Runs the station across a weather series while layering the Digital Twin's
# existing scenario helpers — storm, generator failure, low fuel, communication
# outage — simultaneously rather than one at a time.
#
# Reuses src/digital_twin/scenarios.py; no scenario logic is duplicated here.
# ─────────────────────────────────────────────────────────────────────────────

import config
from src.digital_twin.scenarios import (
    apply_storm_scenario,
    apply_generator_failure_scenario,
    apply_low_fuel_scenario,
    apply_communication_outage_scenario,
)
from .connectivity import get_connectivity_status, is_record_offline
from .fallback import safe_dispatch
from . import cache


def build_scenario_records(weather_records, storm=False, comms_outage_hours=None):
    """
    Layers record-level scenarios onto a weather series.

    storm              : tag storm hours using the Twin's wind-speed threshold
    comms_outage_hours : iterable of hour indices where the uplink is down

    Returns a new list; input records are never mutated.
    """
    records = list(weather_records)
    if storm:
        records = apply_storm_scenario(records)

    if comms_outage_hours:
        outage = set(comms_outage_hours)
        offline_tagged = apply_communication_outage_scenario(records)
        records = [
            offline_tagged[i] if i in outage else records[i]
            for i in range(len(records))
        ]
    return records


def run_resilience_scenario(weather_records, storm=False, failed_generator=None,
                            comms_outage_hours=None, initial_fuel_litres=None,
                            initial_soc_kwh=None, optimizer=None,
                            use_cache_when_offline=True):
    """
    Runs the full combined-failure scenario hour by hour.

    failed_generator   : "G1" or "G2" (uses the Twin's failure helper), or None
    comms_outage_hours : hour indices where the uplink is down
    initial_fuel_litres: low-fuel scenarios pass a reduced value here
    optimizer          : optional optimizer; falls back automatically on failure

    Returns a list of per-hour dispatch dicts, each carrying connectivity_status,
    dispatch_mode, reasoning and the Twin's full power-flow fields.
    """
    if failed_generator is not None:
        gen_cfg = apply_generator_failure_scenario(weather_records, failed_generator)
        gen1_available = gen_cfg["generator_1_available"]
        gen2_available = gen_cfg["generator_2_available"]
    else:
        gen1_available = gen2_available = True

    fuel = config.FUEL_TANK_LITRES if initial_fuel_litres is None else initial_fuel_litres
    fuel_state = apply_low_fuel_scenario(fuel)
    fuel_l = fuel_state["initial_fuel_litres"]

    soc_kwh = (config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION
               if initial_soc_kwh is None else initial_soc_kwh)

    records = build_scenario_records(weather_records, storm=storm,
                                     comms_outage_hours=comms_outage_hours)

    results = []
    consecutive_offline = 0

    for rec in records:
        offline = is_record_offline(rec)

        if offline:
            consecutive_offline += 1
            if use_cache_when_offline:
                snapshot = cache.load_snapshot()
                active_weather = snapshot["weather_record"]
            else:
                active_weather = rec
            # Never call a network/API-dependent optimizer while offline.
            active_optimizer = None
        else:
            consecutive_offline = 0
            active_weather = rec
            active_optimizer = optimizer
            cache.save_snapshot(rec, soc_kwh, fuel_l)

        result = safe_dispatch(
            weather_record        = active_weather,
            battery_soc_kwh       = soc_kwh,
            fuel_remaining_litres = fuel_l,
            generator_1_available = gen1_available,
            generator_2_available = gen2_available,
            optimizer             = active_optimizer,
        )

        soc_kwh = result["battery_soc_kwh"]
        fuel_l  = result["fuel_remaining_litres"]

        result["timestamp"]            = rec.get("timestamp")
        result["connectivity_status"]  = get_connectivity_status(offline, consecutive_offline)
        result["storm_active"]         = rec.get("scenario_name") == "storm"
        result["failed_generator"]     = failed_generator
        result["used_cached_weather"]  = offline and use_cache_when_offline
        results.append(result)

    return results
