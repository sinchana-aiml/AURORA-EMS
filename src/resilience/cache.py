# src/resilience/cache.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Offline Data Cache
# Member: Resilience & Offline Integration
#
# Stores the last known-good weather record and station state so the Twin
# can keep running when the uplink drops. Uses the same weather schema as
# weather_loader.REQUIRED_COLUMNS.
#
# JSON file store is deliberate for the prototype — swap for SQLite when the
# system runs on real station hardware.
# ─────────────────────────────────────────────────────────────────────────────

import json
import os

DEFAULT_CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "outputs",
    "resilience_cache.json",
)

# Used only on a cold start (no cache written yet). Conservative polar values:
# no sun, light wind, deep cold — so the Twin errs toward more heating demand
# and less renewable generation rather than optimistically underestimating it.
COLD_START_WEATHER = {
    "timestamp":       "cold-start",
    "temperature_c":   -25.0,
    "irradiance_w_m2":   0.0,
    "wind_speed_ms":     2.0,
}


def save_snapshot(weather_record, battery_soc_kwh, fuel_remaining_litres,
                  path=DEFAULT_CACHE_PATH):
    """
    Persists the latest known-good weather record and station state.
    Called whenever a live weather read succeeds.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    snapshot = {
        "weather_record":        dict(weather_record),
        "battery_soc_kwh":       battery_soc_kwh,
        "fuel_remaining_litres": fuel_remaining_litres,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
    return snapshot


def load_snapshot(path=DEFAULT_CACHE_PATH):
    """
    Returns the last saved snapshot, or a safe cold-start snapshot when no
    cache exists yet. Never raises for a missing or corrupt cache — the
    station must keep running regardless.
    """
    if not os.path.exists(path):
        return _cold_start()
    try:
        with open(path, encoding="utf-8") as f:
            snapshot = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _cold_start()

    if "weather_record" not in snapshot:
        return _cold_start()
    return snapshot


def _cold_start():
    import config
    return {
        "weather_record":        dict(COLD_START_WEATHER),
        "battery_soc_kwh":       config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION,
        "fuel_remaining_litres": config.FUEL_TANK_LITRES,
        "cold_start":            True,
    }


def clear_cache(path=DEFAULT_CACHE_PATH):
    """Removes the cache file. Used by tests and demo resets."""
    if os.path.exists(path):
        os.remove(path)
