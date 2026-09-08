# Telemetry Schema

**Project:** AURORA-EMS — AI-Assisted Energy Management System  
**Module:** Member 1 — Digital Twin & Energy Simulation  
**Source function:** `energy_balance_step` in `src/digital_twin/energy_balance.py`  
**Simulation loop:** `run_simulation` in `src/digital_twin/simulation.py`

> All values are **SIMULATED / PROTOTYPE**. Units and field names are stable
> and must not be renamed by downstream modules.

---

## 1. Weather Input Interface

`run_simulation` and `energy_balance_step` consume weather records as plain
Python dicts. The four required fields are:

| Field | Type | Unit | Description |
|---|---|---|---|
| `timestamp` | `str` | ISO-8601 (`YYYY-MM-DDTHH:MM`) | Hour label; preserved unchanged in output |
| `temperature_c` | `float` | °C | Outside air temperature |
| `irradiance_w_m2` | `float` | W/m² | Solar irradiance on panel surface; must be ≥ 0 |
| `wind_speed_ms` | `float` | m/s | Wind speed at hub height; must be ≥ 0 |

These four fields are the **stable contract** between the weather data layer
and the simulation engine. Any weather source — synthetic CSV, future API
loader, or real-time feed — must produce records in this format.
`validate_weather_records` enforces physical bounds before records reach the
simulation.

---

## 2. Simulation Output Schema

`energy_balance_step` returns a dict with 23 fields. `run_simulation` adds
`timestamp` as a 24th field, giving one complete record per simulated hour.

Fields are grouped below by role.

### 2.1 Weather inputs (echoed into output)

| Field | Type | Unit | Role | Description |
|---|---|---|---|---|
| `timestamp` | `str` | ISO-8601 | Input (echoed) | Hour label from the weather record |
| `temperature_c` | `float` | °C | Input (echoed) | Outside air temperature passed in |
| `irradiance_w_m2` | `float` | W/m² | Input (echoed) | Solar irradiance passed in |
| `wind_speed_ms` | `float` | m/s | Input (echoed) | Wind speed passed in |

### 2.2 Station load

| Field | Type | Unit | Role | Description |
|---|---|---|---|---|
| `electrical_load_kw` | `float` | kW | Calculated output | Electrical demand (base + flexible) |
| `heating_load_kw` | `float` | kW | Calculated output | Heating demand at this temperature |
| `total_load_kw` | `float` | kW | Calculated output | `electrical_load_kw + heating_load_kw` |

### 2.3 Renewable generation

| Field | Type | Unit | Role | Description |
|---|---|---|---|---|
| `solar_power_kw` | `float` | kW | Calculated output | Solar PV output this hour |
| `wind_power_kw` | `float` | kW | Calculated output | Wind turbine output this hour |
| `renewable_used_kw` | `float` | kW | Calculated output | Renewable power actually delivered to load |

### 2.4 Battery

| Field | Type | Unit | Role | Description |
|---|---|---|---|---|
| `battery_charge_kw` | `float` | kW | Calculated output | Power drawn from bus into battery (bus-side) |
| `battery_discharge_kw` | `float` | kW | Calculated output | Power delivered from battery to bus (bus-side) |
| `battery_soc_kwh` | `float` | kWh | State | Battery state of charge at end of this hour |

`battery_charge_kw` and `battery_discharge_kw` are mutually exclusive in any
single timestep. Both are zero when the battery is idle.

`battery_soc_kwh` is the **carried-forward state variable**. `run_simulation`
feeds the value from hour *n* as the input to hour *n+1*.

### 2.5 Generators

| Field | Type | Unit | Role | Description |
|---|---|---|---|---|
| `generator_1_power_kw` | `float` | kW | Calculated output | Generator 1 actual output |
| `generator_2_power_kw` | `float` | kW | Calculated output | Generator 2 actual output |
| `generator_total_kw` | `float` | kW | Calculated output | `generator_1_power_kw + generator_2_power_kw` |
| `generator_to_battery_charge_kw` | `float` | kW | Calculated output | Generator excess absorbed by battery |
| `excess_generation_kw` | `float` | kW | Calculated output | Generator over-production before battery absorption |
| `fuel_used_litres` | `float` | L | Calculated output | Diesel consumed by both generators this hour |
| `fuel_remaining_litres` | `float` | L | State | Cumulative fuel remaining after this hour |

`fuel_remaining_litres` is the second **carried-forward state variable**.

### 2.6 Load balance and quality

| Field | Type | Unit | Role | Description |
|---|---|---|---|---|
| `curtailed_power_kw` | `float` | kW | Calculated output | Generation that could not be stored or used |
| `unmet_load_kw` | `float` | kW | Calculated output | Demand not served; 0 in normal operation |
| `supplied_load_kw` | `float` | kW | Calculated output | `total_load_kw − unmet_load_kw` |
| `critical_load_served` | `bool` | — | Status | `True` when `supplied_load_kw ≥ 20 kW` |

---

## 3. Power-Balance Identity

The following identity holds at every timestep (verified by automated tests):

```
solar_power_kw + wind_power_kw + generator_total_kw + battery_discharge_kw
    = supplied_load_kw + battery_charge_kw + curtailed_power_kw
```

Downstream modules may use this identity to detect data corruption or
integration errors.

---

## 4. Scenario Overlay Fields

When scenario helpers in `src/digital_twin/scenarios.py` are applied to
weather records before simulation, additional fields may appear in the
weather dicts. These are **not** produced by `energy_balance_step` and are
not part of the core telemetry schema.

| Field | Added by | Values | Description |
|---|---|---|---|
| `scenario_name` | `apply_storm_scenario` | `"storm"` | Present only on storm-threshold records |
| `communication_status` | `apply_communication_outage_scenario` | `"offline"` | Marks all records in a comms-outage run |
| `sensor_quality_flag` | `apply_sensor_fault_scenario` | `"fault"` | Marks all records in a sensor-fault run |

---

## 5. Guidance for Downstream Modules

**Forecasting module**  
Consume the list of result dicts returned by `run_simulation`. Use
`battery_soc_kwh` and `fuel_remaining_litres` as the initial state for the
next simulation window. Do not rename fields or change units.

**Optimisation module**  
Read `unmet_load_kw`, `curtailed_power_kw`, and `fuel_used_litres` as
objective-function inputs. Pass modified `generator_1_available` /
`generator_2_available` flags to `run_simulation` to evaluate dispatch
alternatives. Do not modify `energy_balance_step` internals.

**Dashboard module**  
Display fields directly from the result dicts. The field names and units in
this document are the stable API. If a display label must differ from the
field name, map it in the dashboard layer, not in the simulation layer.

---

## 6. Example Telemetry Record

The following is one real output record from the verified 24-hour normal
simulation (hour 23, 2024-07-01T23:00, evening conditions):

```json
{
  "timestamp":                    "2024-07-01T23:00",
  "temperature_c":                -18.0,
  "irradiance_w_m2":              50.0,
  "wind_speed_ms":                5.0,
  "electrical_load_kw":           30.0,
  "heating_load_kw":              29.4,
  "total_load_kw":                59.4,
  "solar_power_kw":               1.9168,
  "wind_power_kw":                11.1111,
  "renewable_used_kw":            13.0279,
  "battery_charge_kw":            19.0,
  "battery_discharge_kw":         0.0,
  "battery_soc_kwh":              103.5,
  "generator_1_power_kw":         20.0,
  "generator_2_power_kw":         0.0,
  "generator_total_kw":           20.0,
  "generator_to_battery_charge_kw": 19.0,
  "excess_generation_kw":         19.0,
  "curtailed_power_kw":           0.0,
  "fuel_used_litres":             8.0,
  "fuel_remaining_litres":        4806.2881,
  "unmet_load_kw":                0.0,
  "supplied_load_kw":             59.4,
  "critical_load_served":         true
}
```

> Note: `solar_power_kw` and `wind_power_kw` values above are rounded for
> display. The simulation stores values rounded to 4 decimal places.
