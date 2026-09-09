# Verification Report

**Project:** AURORA-EMS — AI-Assisted Energy Management System  
**Module:** Member 1 — Digital Twin & Energy Simulation  
**Verification date:** Date of final verification: to be recorded at release  
**Status:** All automated tests pass. Prototype only — not validated against real NCPOR data.

---

## 1. Test Command and Result

```
python -m pytest -q
```

```
146 passed in 0.74s
```

No failures. No warnings. Exit code 0.

---

## 2. Test Environment

| Item | Value |
|---|---|
| Python | 3.11.9 |
| pytest | 9.1.1 |
| Platform | Windows (win32) |
| Test discovery root | `tests/` |
| pytest config | `pytest.ini` (`pythonpath = .`) |

---

## 3. Test File Summary

| File | Tests | Coverage area |
|---|---|---|
| `tests/test_load_model.py` | 11 | Electrical, heating, and total load calculations |
| `tests/test_renewable_model.py` | 16 | Solar PV boundaries and temperature effect; wind 4-region power curve |
| `tests/test_battery_model.py` | 10 | SOC limits, charge/discharge efficiency, power caps |
| `tests/test_generator_model.py` | 13 | Minimum load, rated cap, availability, fuel formula |
| `tests/test_energy_balance.py` | 22 | All five dispatch scenarios, power-balance identity, output field names |
| `tests/test_simulation.py` | 17 | 24-hour loop, timestamp order, SOC continuity, fuel monotonicity, G1 failure |
| `tests/test_scenarios.py` | 40 | All five scenario helpers, immutability, boundary values, invalid-input rejection |
| `tests/test_weather_loader.py` | 17 | CSV loading, float conversion, validation rules, error cases |
| **Total** | **146** | |

---

## 4. Power-Balance Verification

The identity below was verified for all five energy-balance test cases:

```
solar_power_kw + wind_power_kw + generator_total_kw + battery_discharge_kw
    = supplied_load_kw + battery_charge_kw + curtailed_power_kw
```

| Test case | LHS (kW) | RHS (kW) | Result |
|---|---|---|---|
| T1: Sunny + windy, renewables surplus | 79.9136 | 79.9136 | PASS |
| T2: Dark + calm, battery + G1 minimum | 80.0000 | 80.0000 | PASS |
| T3: G1 unavailable, G2 takes over | 90.0000 | 90.0000 | PASS |
| T4: Battery at minimum SOC | 61.0000 | 61.0000 | PASS |
| T5: Both generators unavailable | 0.0000 | 0.0000 | PASS |

Tolerance applied: 1 × 10⁻⁴ kW.

---

## 5. 24-Hour Simulation Checks (Normal Scenario)

Initial conditions: SOC = 210.0 kWh (70 %), fuel = 5000.0 L.  
Weather: synthetic 24-hour pattern from `make_test_weather()`.

| Check | Result |
|---|---|
| Exactly 24 output rows | PASS |
| Timestamps in chronological order | PASS |
| SOC continuity between hours (tolerance 0.05 kWh) | PASS |
| Fuel never increases between hours | PASS |
| No unmet load in any hour | PASS |

### Pinned final-hour values

| Metric | Value |
|---|---|
| Final battery SOC | **103.5 kWh** |
| Final fuel remaining | **4806.2881 L** |
| Total fuel consumed | **193.7119 L** |
| Maximum unmet load | **0.0 kW** |

These values are pinned in `tests/test_simulation.py` with tolerances of
±0.1 kWh and ±0.01 L respectively. Any change to physics formulas or
constants that shifts these values will cause the tests to fail.

---

## 6. Generator 1 Failure Scenario

`run_simulation` was called with `generator_1_available=False` over the same
24-hour synthetic weather sequence.

| Check | Result |
|---|---|
| Generator 1 output is 0.0 kW in all 24 hours | PASS |
| Generator 2 runs during night hours (hours 0–5) | PASS |
| No unmet load in any hour | PASS |
| Exactly 24 output rows | PASS |

---

## 7. Scenario Helper Verification

All five scenario functions in `src/digital_twin/scenarios.py` were verified:

| Scenario | Checks | Result |
|---|---|---|
| `apply_storm_scenario` | Labelling at/above threshold, no label below, immutability, timestamp/value preservation | PASS |
| `apply_generator_failure_scenario` | G1 config, G2 config, default=G1, invalid name rejection | PASS |
| `apply_low_fuel_scenario` | Below threshold, at threshold, above threshold, zero fuel, negative rejection | PASS |
| `apply_communication_outage_scenario` | All records offline, immutability, value preservation | PASS |
| `apply_sensor_fault_scenario` | All three sensors × 6 checks each, unsupported sensor rejection | PASS |

---

## 8. Weather Loader Verification

`src/digital_twin/weather_loader.py` was verified in two ways:
- Standalone `weather_loader.py` self-test (`python weather_loader.py`): **12/12 checks passed**
- pytest `tests/test_weather_loader.py`: **17 tests passed**
- Complete pytest suite: **146/146 tests passed**

The 17 pytest checks are:

| Check | Result |
|---|---|
| Loads exactly 24 rows from synthetic CSV | PASS |
| All numeric fields converted to `float` | PASS |
| Timestamps preserved as strings | PASS |
| First/last timestamp spot-check | PASS |
| Missing file raises `FileNotFoundError` | PASS |
| Missing column raises `ValueError` | PASS |
| Non-numeric cell raises `ValueError` | PASS |
| Empty records list raises `ValueError` | PASS |
| Negative irradiance raises `ValueError` | PASS |
| Negative wind speed raises `ValueError` | PASS |
| Temperature below −90 °C raises `ValueError` | PASS |
| Temperature above 60 °C raises `ValueError` | PASS |
| Out-of-order timestamps raise `ValueError` | PASS |

---

## 9. Limitations

The following limitations apply to this prototype verification:

1. **Synthetic weather only.** All self-tests and the 24-hour simulation use
   hand-crafted weather values from `make_test_weather()` and
   `make_sample_weather_csv()`. No real Antarctic weather data has been used
   to drive the simulation.

2. **Engineering estimates, not calibrated parameters.** Equipment ratings
   (PV capacity, wind curve, battery efficiency, generator fuel rates) are
   plausible prototype values. They have not been calibrated against real
   NCPOR station measurements or manufacturer data sheets.

3. **No real NCPOR electrical telemetry.** The model has not been compared
   against any real station power logs. Accuracy relative to a real polar
   station is unknown.

4. **No field validation.** The simulation has not been run in shadow mode
   alongside a real system to compare predicted versus actual energy flows.

5. **Hourly resolution only.** The timestep is fixed at one hour. Sub-hourly
   dynamics (ramp rates, transient faults) are not modelled.

6. **No degradation modelling.** Battery capacity fade, panel soiling over
   time, and generator wear are not included.

---

## 10. Next Validation Steps

The following steps are recommended before the Digital Twin is used for
operational planning or real-station integration:

1. **Public weather data.** Drive the simulation with publicly available
   Antarctic weather records (e.g., from a meteorological agency) to test
   behaviour under realistic seasonal and storm conditions.

2. **Real telemetry comparison (if available).** If NCPOR station power logs
   can be obtained, compare simulated generation and consumption against
   recorded values and quantify the error.

3. **Parameter calibration.** Adjust equipment constants in `config.py` to
   match actual installed hardware specifications once those are known.

4. **Backtest over a full season.** Run the simulation over a complete
   Antarctic winter (April–September) to verify fuel consumption and SOC
   trajectories are physically plausible.

5. **Shadow mode.** Run the Digital Twin in parallel with a real or
   higher-fidelity model, comparing outputs hour by hour before any
   operational use.

6. **Operator review.** Have a domain expert (station engineer or energy
   systems specialist) review the modelling assumptions in
   `docs/digital_twin_assumptions.md` and confirm or correct them.
