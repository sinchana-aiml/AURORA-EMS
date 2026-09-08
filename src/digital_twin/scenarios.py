# src/digital_twin/scenarios.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Failure and Storm Scenario Helpers
# Member 1: Digital Twin & Energy Simulation
#
# Each function returns a NEW object and never mutates its input.
# None of these functions alter weather physics or simulation constants.
# All values remain PROTOTYPE / SIMULATED.
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os

# Ensure the project root is importable whether this file is run directly
# (python src/digital_twin/scenarios.py) or imported as part of the package.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import config

_SUPPORTED_SENSORS = {"wind_speed_ms", "temperature_c", "irradiance_w_m2"}
_VALID_GENERATORS  = {"G1", "G2"}


# ── 1. STORM SCENARIO ─────────────────────────────────────────────────────────

def apply_storm_scenario(weather_records):
    """
    Return a new list of weather records with scenario_name = "storm" added
    to every record where wind_speed_ms >= config.STORM_WIND_THRESHOLD_MS.

    Records below the threshold are copied unchanged (no scenario_name added).
    Weather values and timestamps are never modified.
    """
    result = []
    for rec in weather_records:
        new_rec = dict(rec)                          # shallow copy — no mutation
        if new_rec["wind_speed_ms"] >= config.STORM_WIND_THRESHOLD_MS:
            new_rec["scenario_name"] = "storm"
        result.append(new_rec)
    return result


# ── 2. GENERATOR FAILURE SCENARIO ─────────────────────────────────────────────

def apply_generator_failure_scenario(weather_records, failed_generator="G1"):
    """
    Return a simulation-configuration dict describing which generators are
    available.  Does NOT modify weather records.

    failed_generator : "G1" or "G2"

    Returns:
      {
        "generator_1_available": bool,
        "generator_2_available": bool,
        "failed_generator":      str,
        "scenario_name":         "generator_failure",
      }

    Raises ValueError for any value other than "G1" or "G2".
    """
    if failed_generator not in _VALID_GENERATORS:
        raise ValueError(
            f"failed_generator must be 'G1' or 'G2', got '{failed_generator}'."
        )
    return {
        "generator_1_available": failed_generator != "G1",
        "generator_2_available": failed_generator != "G2",
        "failed_generator":      failed_generator,
        "scenario_name":         "generator_failure",
    }


# ── 3. LOW-FUEL SCENARIO ──────────────────────────────────────────────────────

def apply_low_fuel_scenario(initial_fuel_litres):
    """
    Return a fuel-state dict for the low-fuel scenario.

    initial_fuel_litres : current fuel level (litres) — must be >= 0

    Returns:
      {
        "initial_fuel_litres": float,
        "low_fuel_warning":    bool,   # True when fuel <= config.LOW_FUEL_THRESHOLD_L
        "scenario_name":       "low_fuel",
      }

    Raises ValueError for negative fuel values.
    """
    if initial_fuel_litres < 0:
        raise ValueError(
            f"initial_fuel_litres cannot be negative, got {initial_fuel_litres}."
        )
    return {
        "initial_fuel_litres": initial_fuel_litres,
        "low_fuel_warning":    initial_fuel_litres <= config.LOW_FUEL_THRESHOLD_L,
        "scenario_name":       "low_fuel",
    }


# ── 4. COMMUNICATION OUTAGE SCENARIO ──────────────────────────────────────────

def apply_communication_outage_scenario(weather_records):
    """
    Return a new list of records with communication_status = "offline" added
    to every record.  All weather values and timestamps are preserved unchanged.
    """
    return [{**rec, "communication_status": "offline"} for rec in weather_records]


# ── 5. SENSOR FAULT SCENARIO ──────────────────────────────────────────────────

def apply_sensor_fault_scenario(weather_records, sensor_name):
    """
    Return a new list of records where the named sensor value is set to None
    and sensor_quality_flag = "fault" is added to every record.

    sensor_name : one of "wind_speed_ms", "temperature_c", "irradiance_w_m2"

    All other weather values and timestamps are preserved unchanged.
    The input list and its dicts are never mutated.

    Raises ValueError for unsupported sensor names.
    """
    if sensor_name not in _SUPPORTED_SENSORS:
        raise ValueError(
            f"Unsupported sensor '{sensor_name}'. "
            f"Supported sensors: {sorted(_SUPPORTED_SENSORS)}."
        )
    result = []
    for rec in weather_records:
        new_rec = dict(rec)
        new_rec[sensor_name]          = None
        new_rec["sensor_quality_flag"] = "fault"
        result.append(new_rec)
    return result


# ── Self-tests ────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    def check(label, condition):
        print(f"  [{'PASS' if condition else 'FAIL'}] {label}")
        return condition

    def expect_error(label, fn):
        try:
            fn()
            print(f"  [FAIL] {label}  <-- expected ValueError but none raised>")
            return False
        except ValueError as e:
            print(f"  [PASS] {label}  (error: {e})")
            return True

    # ── Minimal synthetic weather records ─────────────────────────────────────
    # Three records: calm, borderline, storm-force
    RECORDS = [
        {"timestamp": "2024-07-01T00:00", "temperature_c": -25.0,
         "irradiance_w_m2": 0.0,   "wind_speed_ms": 5.0},   # calm
        {"timestamp": "2024-07-01T01:00", "temperature_c": -20.0,
         "irradiance_w_m2": 400.0, "wind_speed_ms": 20.0},  # exactly at threshold
        {"timestamp": "2024-07-01T02:00", "temperature_c": -15.0,
         "irradiance_w_m2": 900.0, "wind_speed_ms": 28.0},  # storm-force
    ]

    print("=" * 60)
    print("  scenarios.py  self-tests")
    print(f"  STORM_WIND_THRESHOLD_MS = {config.STORM_WIND_THRESHOLD_MS} m/s")
    print(f"  LOW_FUEL_THRESHOLD_L    = {config.LOW_FUEL_THRESHOLD_L} L")
    print("=" * 60)

    # ── 1. Storm scenario ─────────────────────────────────────────────────────
    print()
    print("-- apply_storm_scenario --")
    storm_recs = apply_storm_scenario(RECORDS)

    check("Returns a new list (not the same object)",
          storm_recs is not RECORDS)
    check("Input records are not mutated",
          "scenario_name" not in RECORDS[0] and
          "scenario_name" not in RECORDS[1] and
          "scenario_name" not in RECORDS[2])
    check("Calm record (5 m/s) has no scenario_name",
          "scenario_name" not in storm_recs[0])
    check("Threshold record (20 m/s) labeled 'storm'",
          storm_recs[1].get("scenario_name") == "storm")
    check("Storm record (28 m/s) labeled 'storm'",
          storm_recs[2].get("scenario_name") == "storm")
    check("Timestamps preserved in storm output",
          [r["timestamp"] for r in storm_recs] ==
          [r["timestamp"] for r in RECORDS])
    check("Weather values preserved in storm output",
          storm_recs[0]["wind_speed_ms"] == RECORDS[0]["wind_speed_ms"] and
          storm_recs[2]["irradiance_w_m2"] == RECORDS[2]["irradiance_w_m2"])

    # ── 2. Generator failure scenario ─────────────────────────────────────────
    print()
    print("-- apply_generator_failure_scenario --")
    g1_cfg = apply_generator_failure_scenario(RECORDS, failed_generator="G1")
    check("G1 failure: generator_1_available is False",
          g1_cfg["generator_1_available"] is False)
    check("G1 failure: generator_2_available is True",
          g1_cfg["generator_2_available"] is True)
    check("G1 failure: failed_generator field is 'G1'",
          g1_cfg["failed_generator"] == "G1")
    check("G1 failure: scenario_name is 'generator_failure'",
          g1_cfg["scenario_name"] == "generator_failure")

    g2_cfg = apply_generator_failure_scenario(RECORDS, failed_generator="G2")
    check("G2 failure: generator_1_available is True",
          g2_cfg["generator_1_available"] is True)
    check("G2 failure: generator_2_available is False",
          g2_cfg["generator_2_available"] is False)
    check("G2 failure: failed_generator field is 'G2'",
          g2_cfg["failed_generator"] == "G2")

    expect_error("Invalid generator name raises ValueError",
                 lambda: apply_generator_failure_scenario(RECORDS, "G3"))

    # ── 3. Low-fuel scenario ──────────────────────────────────────────────────
    print()
    print("-- apply_low_fuel_scenario --")
    below = apply_low_fuel_scenario(300.0)
    check("300 L (below threshold 500 L): low_fuel_warning is True",
          below["low_fuel_warning"] is True)
    check("300 L: initial_fuel_litres preserved",
          below["initial_fuel_litres"] == 300.0)
    check("300 L: scenario_name is 'low_fuel'",
          below["scenario_name"] == "low_fuel")

    at_threshold = apply_low_fuel_scenario(500.0)
    check("500 L (exactly at threshold): low_fuel_warning is True",
          at_threshold["low_fuel_warning"] is True)

    above = apply_low_fuel_scenario(2000.0)
    check("2000 L (above threshold): low_fuel_warning is False",
          above["low_fuel_warning"] is False)

    expect_error("Negative fuel raises ValueError",
                 lambda: apply_low_fuel_scenario(-1.0))

    # ── 4. Communication outage scenario ──────────────────────────────────────
    print()
    print("-- apply_communication_outage_scenario --")
    comms_recs = apply_communication_outage_scenario(RECORDS)

    check("Returns a new list",
          comms_recs is not RECORDS)
    check("Input records not mutated",
          "communication_status" not in RECORDS[0])
    check("All records have communication_status = 'offline'",
          all(r["communication_status"] == "offline" for r in comms_recs))
    check("Timestamps preserved",
          [r["timestamp"] for r in comms_recs] ==
          [r["timestamp"] for r in RECORDS])
    check("Weather values preserved",
          comms_recs[1]["wind_speed_ms"] == RECORDS[1]["wind_speed_ms"])

    # ── 5. Sensor fault scenario ──────────────────────────────────────────────
    print()
    print("-- apply_sensor_fault_scenario --")
    for sensor in ("wind_speed_ms", "temperature_c", "irradiance_w_m2"):
        fault_recs = apply_sensor_fault_scenario(RECORDS, sensor)
        check(f"'{sensor}' fault: returns new list",
              fault_recs is not RECORDS)
        check(f"'{sensor}' fault: input not mutated (original value intact)",
              RECORDS[0][sensor] is not None)
        check(f"'{sensor}' fault: all records have {sensor} = None",
              all(r[sensor] is None for r in fault_recs))
        check(f"'{sensor}' fault: all records have sensor_quality_flag = 'fault'",
              all(r["sensor_quality_flag"] == "fault" for r in fault_recs))
        check(f"'{sensor}' fault: timestamps preserved",
              [r["timestamp"] for r in fault_recs] ==
              [r["timestamp"] for r in RECORDS])
        # Verify the other two sensor values are untouched
        other_sensors = _SUPPORTED_SENSORS - {sensor}
        check(f"'{sensor}' fault: other sensor values unchanged",
              all(fault_recs[i][s] == RECORDS[i][s]
                  for i in range(len(RECORDS))
                  for s in other_sensors))

    expect_error("Unsupported sensor name raises ValueError",
                 lambda: apply_sensor_fault_scenario(RECORDS, "pressure_hpa"))

    print()
    print("All scenario tests complete.")
