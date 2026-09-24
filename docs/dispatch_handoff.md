# Dispatch Handoff — Member 4

**Module:** Member 4 — Optimization & Energy Dispatch  
**Status:** Prototype. Not a real NCPOR controller.

---

## 1. What This Module Does

The dispatch layer sits between the Digital Twin (Member 1/2) and the
Dashboard (Member 5). It takes hourly energy state from the Digital Twin,
decides how to allocate generation sources, and returns a per-hour result
dict that downstream modules can consume directly.

---

## 2. How to Get Dispatch Results

```python
from src.dispatch.run_comparison import run_dispatch_comparison

comparison = run_dispatch_comparison()

# Per-hour results for each strategy:
baseline_hours  = comparison["baseline_results"]   # list of dicts
optimized_hours = comparison["optimized_results"]  # list of dicts
```

For scenario results:

```python
from src.dispatch.run_scenarios import run_scenario

results = run_scenario(
    scenario_name="Storm",
    storm_mode=True,
)
# results is a list of per-hour dicts
```

---

## 3. Per-Hour Output Schema

Every item in the results list contains these fields.

### From the adapter (Digital Twin passthrough)

| Field | Type | Unit | Description |
|---|---|---|---|
| `timestamp_utc` | str | ISO-8601 UTC | Hour label |
| `load_total_kw` | float | kW | Total station demand this hour |
| `renewable_available_kw` | float | kW | Solar + wind available |

### From the dispatch layer

| Field | Type | Unit | Description |
|---|---|---|---|
| `renewable_used_kw` | float | kW | Renewable actually dispatched |
| `renewable_curtailed_kw` | float | kW | Renewable available but unused |
| `battery_discharge_kw` | float | kW | Battery power delivered to load |
| `battery_soc_kwh` | float | kWh | Battery state of charge after this hour |
| `generator_1_kw` | float | kW | Generator 1 output |
| `generator_2_kw` | float | kW | Generator 2 output |
| `generator_total_kw` | float | kW | G1 + G2 combined output |
| `fuel_used_litres` | float | L | Diesel consumed this hour |
| `fuel_remaining_litres` | float | L | Cumulative fuel remaining |
| `unmet_load_kw` | float | kW | Demand not served (0 in normal operation) |
| `critical_load_served` | bool | — | True when critical load is fully supplied |
| `battery_reserve_kwh` | float | kWh | Minimum SOC enforced this hour |
| `low_fuel_mode` | bool | — | True when fuel ≤ 500 L threshold |
| `flexible_load_shed_kw` | float | kW | Flexible load shed due to low fuel (0 normally) |

### Summary fields (run_dispatch_comparison only)

| Field | Type | Description |
|---|---|---|
| `baseline_fuel_used_litres` | float | Total baseline fuel over 24 h |
| `optimized_fuel_used_litres` | float | Total optimized fuel over 24 h |
| `fuel_saved_liters` | float | Baseline minus optimized fuel |
| `fuel_saved_pct` | float | Percentage fuel saved |
| `baseline_final_soc_kwh` | float | Baseline battery SOC at end |
| `optimized_final_soc_kwh` | float | Optimized battery SOC at end |
| `baseline_fuel_crisis_days` | float | Estimated days of fuel remaining (baseline) |
| `optimized_fuel_crisis_days` | float | Estimated days of fuel remaining (optimized) |

---

## 4. Forecast Confidence Hook (Member 3)

`optimized_dispatch` accepts an optional `forecast_confidence` parameter.
Member 3 should pass this when their forecasting module is ready.

```python
from src.dispatch.optimizer import optimized_dispatch

result = optimized_dispatch(
    demand_kw=65.0,
    renewable_kw=30.0,
    battery_soc_kwh=210.0,
    forecast_confidence="low",   # "high", "medium", "low", or None
)
```

Effect on battery reserve:

| Value | Reserve multiplier | Minimum SOC |
|---|---|---|
| `"high"` | 1.00× | 75 kWh |
| `"medium"` | 1.10× | 82.5 kWh |
| `"low"` | 1.25× | 93.75 kWh |
| `None` | 1.00× | 75 kWh |

---

## 5. Scenario Names

`run_scenarios.py` runs these scenarios:

| Scenario | Description |
|---|---|
| Normal | Full fuel, both generators, no storm |
| Storm | Renewable generation reduced to 60% |
| G1 Failure | Generator 1 unavailable |
| G2 Failure | Generator 2 unavailable |
| Low Fuel | Starting fuel = 500 L (threshold), flexible load shed |
| Communication Loss | G2 disabled (conservative safe-mode) |
| Both Generators Unavailable | Battery + renewables only, unmet load expected |

---

## 6. Running the Dispatch Layer

From the project root:

```bash
# Baseline only
python -m src.dispatch.run_baseline

# Baseline vs optimized comparison
python -m src.dispatch.run_comparison

# All scenarios
python -m src.dispatch.run_scenarios
```

---

## 7. Configuration Values Used

All constants come from `config.py`. Key values:

| Constant | Value | Role |
|---|---|---|
| `BATTERY_CAPACITY_KWH` | 300 kWh | Battery size |
| `BATTERY_MIN_SOC_FRACTION` | 0.25 | 75 kWh floor |
| `BATTERY_INITIAL_SOC_FRACTION` | 0.70 | 210 kWh start |
| `FUEL_TANK_LITRES` | 5000 L | Starting fuel |
| `LOW_FUEL_THRESHOLD_L` | 500 L | Triggers low-fuel mode |
| `CRITICAL_LOAD_KW` | 20 kW | Never shed |
| `FLEXIBLE_LOAD_KW` | 10 kW | Shed in low-fuel mode |
| `GENERATOR_1_RATED_KW` | 80 kW | G1 capacity |
| `GENERATOR_2_RATED_KW` | 120 kW | G2 capacity |
