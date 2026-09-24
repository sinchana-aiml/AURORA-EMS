#!/usr/bin/env python3
# scripts/run_resilience_demo.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Resilience & Offline Demo
# Member: Resilience & Offline Integration
#
# Repeatable four-phase demonstration:
#   1. Normal operation      — uplink up, deterministic Twin dispatch
#   2. Communication outage  — cached weather, status escalates to autonomous
#   3. Storm + Generator 1 failure + low fuel, while still offline
#   4. Recovery              — uplink restored mid-run
#
# Run from the repository root:
#   python3 scripts/run_resilience_demo.py
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from src.digital_twin import make_test_weather
from src.resilience import run_resilience_scenario, clear_cache

HOURS = 12


def show(title, results, note=""):
    print()
    print("=" * 100)
    print(f"  {title}")
    if note:
        print(f"  {note}")
    print("=" * 100)
    print(f"{'hr':>3} | {'connectivity':<36} | {'load':>7} | {'ren':>7} | "
          f"{'gen':>7} | {'SOC kWh':>8} | {'fuel L':>8} | crit")
    print("-" * 100)
    for i, r in enumerate(results):
        print(f"{i:>3} | {r['connectivity_status']:<36} | "
              f"{r['total_load_kw']:>7.1f} | {r['renewable_used_kw']:>7.1f} | "
              f"{r['generator_total_kw']:>7.1f} | {r['battery_soc_kwh']:>8.1f} | "
              f"{r['fuel_remaining_litres']:>8.1f} | {str(r['critical_load_served']):<5}")
    print()
    print(f"  Example reasoning (hour {len(results)-1}):")
    print(f"    {results[-1]['reasoning']}")
    if results[-1].get("fallback_reason"):
        print(f"    Fallback: {results[-1]['fallback_reason']}")


def main():
    clear_cache()
    weather = make_test_weather(HOURS)

    print()
    print("AURORA-EMS — Resilience & Offline Integration demonstration")
    print("All station energy values are SIMULATED for prototype purposes.")
    print(f"Critical load block: {config.CRITICAL_LOAD_KW:.0f} kW | "
          f"Battery reserve floor: {config.BATTERY_MIN_SOC_FRACTION:.0%} of "
          f"{config.BATTERY_CAPACITY_KWH:.0f} kWh | "
          f"Fuel tank: {config.FUEL_TANK_LITRES:.0f} L")

    show("PHASE 1 — Normal operation",
         run_resilience_scenario(weather),
         "Uplink online. Deterministic Digital Twin dispatch, no optimizer yet integrated.")

    show("PHASE 2 — Communication outage",
         run_resilience_scenario(weather, comms_outage_hours=range(HOURS)),
         "Uplink down for the whole window. Cached weather in use; status escalates "
         f"to autonomous after {3} consecutive offline hours.")

    show("PHASE 3 — Storm + Generator 1 failure + low fuel, while offline",
         run_resilience_scenario(weather, storm=True, failed_generator="G1",
                                 comms_outage_hours=range(HOURS),
                                 initial_fuel_litres=config.LOW_FUEL_THRESHOLD_L),
         "Worst case: four simultaneous failures. Generator 1 is unavailable; "
         "Generator 2 carries the load until fuel is exhausted.")

    show("PHASE 4 — Recovery after reconnection",
         run_resilience_scenario(weather, comms_outage_hours=range(0, 5)),
         "Uplink restored at hour 5; status returns to ONLINE and live weather resumes.")

    print()
    print("Demonstration complete.")
    clear_cache()


if __name__ == "__main__":
    main()
