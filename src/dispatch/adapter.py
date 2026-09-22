# AURORA-EMS
# Member 4 — Digital Twin Adapter
#
# Converts Member 1 Digital Twin output into the common
# Member 4 dispatch input format.
#
# This adapter does not modify Member 1 or Member 2 code.

import config


def adapt_digital_twin_record(record):
    """
    Convert one Member 1 Digital Twin result into the
    Member 4 dispatch schema.
    """

    return {
        "timestamp_utc": record.get("timestamp"),
        "load_total_kw": max(0.0, record.get("total_load_kw", 0.0)),
        "load_critical_kw": config.CRITICAL_LOAD_KW,
        "load_flexible_kw": max(
            0.0,
            config.FLEXIBLE_LOAD_KW,
        ),
        "pv_available_kw": max(
            0.0,
            record.get("solar_power_kw", 0.0),
        ),
        "wind_available_kw": max(
            0.0,
            record.get("wind_power_kw", 0.0),
        ),
        "renewable_available_kw": max(
            0.0,
            record.get("solar_power_kw", 0.0)
            + record.get("wind_power_kw", 0.0),
        ),
        "generator_1_kw": max(
            0.0,
            record.get("generator_1_power_kw", 0.0),
        ),
        "generator_2_kw": max(
            0.0,
            record.get("generator_2_power_kw", 0.0),
        ),
        "battery_soc_kwh": max(
            0.0,
            record.get("battery_soc_kwh", 0.0),
        ),
        "battery_soc_pct": (
            max(0.0, record.get("battery_soc_kwh", 0.0))
            / config.BATTERY_CAPACITY_KWH
            * 100.0
        ),
        "fuel_remaining_litres": max(
            0.0,
            record.get("fuel_remaining_litres", 0.0),
        ),
        "scenario_name": record.get(
            "scenario_name",
            "baseline",
        ),
        "critical_load_served": bool(
            record.get("critical_load_served", True)
        ),
    }


def adapt_digital_twin_results(records):
    """
    Convert a list of Member 1 Digital Twin results.
    """

    return [
        adapt_digital_twin_record(record)
        for record in records
    ]
if __name__ == "__main__":
    sample_record = {
        "timestamp": "2015-01-01T00:00:00+00:00",
        "total_load_kw": 65.0,
        "solar_power_kw": 8.9,
        "wind_power_kw": 6.8,
        "battery_soc_kwh": 210.0,
        "fuel_remaining_litres": 4980.0,
        "critical_load_served": True,
    }

    adapted = adapt_digital_twin_record(sample_record)

    print("Adapted dispatch record:")
    for key, value in adapted.items():
        print(f"{key}: {value}")