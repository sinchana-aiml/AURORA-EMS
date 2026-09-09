# Digital Twin Modelling Assumptions

**Project:** AURORA-EMS — AI-Assisted Energy Management System  
**Module:** Member 1 — Digital Twin & Energy Simulation  
**Status:** Prototype. Not a real NCPOR controller.

---

## 1. Purpose and Scope

The AURORA-EMS Digital Twin is a physics-informed simulation of the energy
system of a *virtual* Indian polar research station. Its purpose is to:

- model hourly energy generation, storage, and consumption under varying
  Antarctic weather conditions;
- exercise failure and storm scenarios without risk to real equipment;
- provide a stable, testable foundation for future forecasting, optimisation,
  and dashboard modules.

**The Digital Twin does not control any real hardware.** All energy values are
simulated. No real NCPOR electrical telemetry has been used to calibrate or
validate the model.

---

## 2. Station Electrical Load

| Parameter | Value | Source |
|---|---|---|
| Base (critical) load | 20.0 kW | `config.BASE_LOAD_KW` |
| Flexible (deferrable) load | 10.0 kW | `config.FLEXIBLE_LOAD_KW` |
| Critical load threshold | 20.0 kW | `config.CRITICAL_LOAD_KW` |

- The **critical load** (20 kW) represents always-on systems — life support,
  communications, and essential instrumentation. It is never shed.
- The **flexible load** (10 kW) represents laboratories and non-critical
  equipment. It is included in normal operation but can be shed during
  shortfalls.
- Total electrical demand with flexible load: **30 kW** (constant).

---

## 3. Heating Load

| Parameter | Value | Source |
|---|---|---|
| Base heating at 0 °C | 15.0 kW | `config.HEATING_BASE_KW` |
| Extra heating per °C below 0 °C | 0.8 kW/°C | `config.HEATING_TEMP_COEFF` |

**Formula:**

```
heating_load(T) = HEATING_BASE_KW + max(0, -T) × HEATING_TEMP_COEFF
```

- At or above 0 °C the heating load is constant at 15 kW.
- Below 0 °C the load increases linearly. At −20 °C: 15 + 20 × 0.8 = **31 kW**.
- The coefficient is a prototype engineering estimate; no real station
  heat-loss data has been used.

---

## 4. Solar PV Array

| Parameter | Value | Source |
|---|---|---|
| Rated peak capacity | 40.0 kW | `config.SOLAR_CAPACITY_KW` |
| Reference irradiance | 1000.0 W/m² | `config.SOLAR_REF_IRRADIANCE` |
| System performance ratio | 0.82 | `config.SOLAR_PERFORMANCE_RATIO` |
| Temperature coefficient | −0.004 /°C | `config.SOLAR_TEMP_COEFF` |
| Reference cell temperature | 25.0 °C | `config.SOLAR_REF_TEMP_C` |

**Formula:**

```
irradiance_factor  = max(0, irradiance_w_m2 / 1000)
temperature_factor = 1 + (−0.004) × (temperature_c − 25)
output_kw          = 40 × irradiance_factor × temperature_factor × 0.82
output_kw          = clamp(output_kw, 0, 40)
```

- The performance ratio (0.82) accounts for wiring losses, inverter
  efficiency, soiling, and shading in aggregate.
- The temperature coefficient models the well-known reduction in PV cell
  efficiency at elevated temperatures; cold Antarctic temperatures therefore
  slightly increase output relative to the 25 °C reference.
- Output is clamped to [0, 40 kW] — it cannot be negative or exceed rated
  capacity.

---

## 5. Wind Turbine

| Parameter | Value | Source |
|---|---|---|
| Rated capacity | 50.0 kW | `config.WIND_CAPACITY_KW` |
| Cut-in speed | 3.0 m/s | `config.WIND_CUT_IN_MS` |
| Rated speed | 12.0 m/s | `config.WIND_RATED_MS` |
| Cut-out speed | 25.0 m/s | `config.WIND_CUT_OUT_MS` |

**Power curve (4 regions):**

| Wind speed | Output |
|---|---|
| < 3.0 m/s | 0 kW (below cut-in) |
| 3.0 – 11.99 m/s | Linear ramp: `50 × (v − 3) / (12 − 3)` kW |
| 12.0 – 24.99 m/s | 50 kW (rated zone) |
| ≥ 25.0 m/s | 0 kW (cut-out for safety) |

- The linear ramp is a simplified approximation of a real cubic power curve.
  It is adequate for prototype dispatch simulation.
- The cut-out at 25 m/s models the automatic storm-protection shutdown.

---

## 6. Battery Energy Storage

| Parameter | Value | Source |
|---|---|---|
| Total capacity | 300.0 kWh | `config.BATTERY_CAPACITY_KWH` |
| Minimum SOC (floor) | 25 % = 75 kWh | `config.BATTERY_MIN_SOC_FRACTION` |
| Initial SOC | 70 % = 210 kWh | `config.BATTERY_INITIAL_SOC_FRACTION` |
| Maximum charge power | 60.0 kW | `config.BATTERY_MAX_CHARGE_KW` |
| Maximum discharge power | 60.0 kW | `config.BATTERY_MAX_DISCHARGE_KW` |
| Charge efficiency | 95 % | `config.BATTERY_CHARGE_EFFICIENCY` |
| Discharge efficiency | 95 % | `config.BATTERY_DISCHARGE_EFFICIENCY` |

**Charging (bus power → SOC):**

```
energy_in_kwh = min(requested_kw, 60) × timestep_h × 0.95
energy_in_kwh = min(energy_in_kwh, 300 − current_soc)
actual_charge_kw = energy_in_kwh / (timestep_h × 0.95)
new_soc = current_soc + energy_in_kwh
```

**Discharging (SOC → bus power):**

```
energy_out_kwh = min(requested_kw, 60) × timestep_h / 0.95
energy_out_kwh = min(energy_out_kwh, current_soc − 75)
actual_discharge_kw = energy_out_kwh × 0.95 / timestep_h
new_soc = current_soc − energy_out_kwh
```

- The SOC floor (75 kWh) protects battery longevity; the model never
  discharges below it.
- Both efficiencies are applied symmetrically. Round-trip efficiency is
  0.95 × 0.95 = 90.25 %.

---

## 7. Diesel Generators

### Generator 1

| Parameter | Value | Source |
|---|---|---|
| Rated capacity | 80.0 kW | `config.GENERATOR_1_RATED_KW` |
| Minimum operating load | 20.0 kW | `config.GENERATOR_1_MINIMUM_KW` |
| Idle fuel consumption | 3.0 L/h | `config.GENERATOR_1_IDLE_FUEL_LPH` |
| Load-dependent fuel rate | 0.25 L/kWh | `config.GENERATOR_1_FUEL_PER_KWH` |

### Generator 2

| Parameter | Value | Source |
|---|---|---|
| Rated capacity | 120.0 kW | `config.GENERATOR_2_RATED_KW` |
| Minimum operating load | 30.0 kW | `config.GENERATOR_2_MINIMUM_KW` |
| Idle fuel consumption | 4.0 L/h | `config.GENERATOR_2_IDLE_FUEL_LPH` |
| Load-dependent fuel rate | 0.23 L/kWh | `config.GENERATOR_2_FUEL_PER_KWH` |

### Shared fuel tank

| Parameter | Value | Source |
|---|---|---|
| Total capacity | 5000.0 L | `config.FUEL_TANK_LITRES` |
| Low-fuel alert threshold | 500.0 L | `config.LOW_FUEL_THRESHOLD_L` |

**Fuel consumption formula (per timestep):**

```
fuel_used = idle_fuel_lph × timestep_h + fuel_per_kwh × actual_output_kw × timestep_h
```

**Minimum-load rule:** diesel engines cannot run efficiently below a minimum
load. If the requested output is less than the minimum, the generator runs at
its minimum anyway, producing excess generation that must be absorbed or
curtailed (see Section 8).

**Availability:** each generator can be marked unavailable (failed or offline).
An unavailable generator produces zero output and consumes no fuel.

---

## 8. Energy Dispatch Order

Each simulation timestep dispatches load in the following priority order:

1. **Renewables (solar + wind)** — zero marginal cost; used first up to
   available output.
2. **Battery discharge** — stored energy; no fuel cost; limited by SOC floor
   and discharge power cap.
3. **Generator 1** — lower fuel rate (0.25 L/kWh); dispatched for remaining
   deficit.
4. **Generator 2** — higher capacity backup (0.23 L/kWh); dispatched only if
   deficit remains after G1.

### Surplus renewable energy

When renewables exceed demand, the surplus charges the battery up to the
charge power cap and SOC ceiling. Any surplus that cannot be stored is
**curtailed** (wasted).

### Generator minimum-load excess

When a generator is dispatched for a small deficit but its minimum-load rule
forces it to produce more than needed, the excess is:

1. Absorbed by the battery (charged at up to 60 kW), then
2. Curtailed if the battery cannot accept it.

This ensures the power-balance identity holds at every timestep:

```
solar + wind + generator_total + battery_discharge
    = supplied_load + battery_charge + curtailed_power
```

---

## 9. Scenario Thresholds

| Scenario | Threshold | Source |
|---|---|---|
| Storm wind label | ≥ 20.0 m/s | `config.STORM_WIND_THRESHOLD_MS` |
| Low-fuel warning | ≤ 500.0 L | `config.LOW_FUEL_THRESHOLD_L` |
| Comms outage probability | 2 % per hour | `config.COMMS_OUTAGE_PROBABILITY` |

---

## 10. Weather Input

The simulation loop accepts any list of hourly records with the four required
fields: `timestamp`, `temperature_c`, `irradiance_w_m2`, `wind_speed_ms`.

Current self-tests use **synthetic weather** generated by `make_test_weather()`
and `make_sample_weather_csv()`. These values are hand-crafted to exercise all
dispatch paths and are **not real Antarctic measurements**.

The weather loader (`src/digital_twin/weather_loader.py`) is designed to accept
real CSV data from any source that produces the same four-column format. No
external weather API has been integrated at this stage.

---

## 11. Prototype Disclaimer

> This Digital Twin is a **prototype for research and demonstration purposes**.
> All energy values, equipment ratings, and fuel consumption figures are
> engineering estimates used to make the simulation physically plausible.
> They have **not** been calibrated against real NCPOR station data.
> The system must not be used to make operational decisions for any real
> polar research station.
