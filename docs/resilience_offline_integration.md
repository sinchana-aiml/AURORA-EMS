# Resilience & Offline Integration

**Branch:** `feature/resilience-offline-integration`
**Package:** `src/resilience/`

This module is the safety layer beneath AURORA-EMS's forecasting and
optimization work. It keeps the station producing safe, explainable dispatch
decisions when the uplink drops or the AI modules fail.

All station energy values remain **PROTOTYPE / SIMULATED**. This is not a real
NCPOR controller.

---

## Design principle

A fallback must not depend on the component that just failed.

This module therefore **does not reimplement dispatch**. It delegates to the
already-validated Digital Twin (`energy_balance_step`), which performs
deterministic priority dispatch — renewables, then battery, then Generator 1,
then Generator 2 — with no ML dependency. The Twin is covered by 169 existing
tests, so the fallback path inherits that validation instead of introducing a
second, unvalidated dispatch implementation.

---

## Module map

| File | Purpose |
|------|---------|
| `src/resilience/connectivity.py` | Uplink probe and the three dashboard status strings |
| `src/resilience/cache.py` | Last known-good weather/state snapshot for offline operation |
| `src/resilience/fallback.py` | `safe_dispatch()` — optimizer wrapper with deterministic fallback |
| `src/resilience/scenario_runner.py` | Runs combined storm / generator-failure / low-fuel / outage scenarios |
| `tests/test_resilience.py` | 14 integration tests |
| `scripts/run_resilience_demo.py` | Four-phase demonstration script |

---

## 1. Connectivity indicator

Three states are exposed for the dashboard:

| Status | Meaning |
|--------|---------|
| `ONLINE` | Uplink reachable; live weather and optimizer in use |
| `OFFLINE` | Uplink down; running on cached data, operator attention expected |
| `OFFLINE - AUTONOMOUS CONTROL ACTIVE` | Outage has lasted `AUTONOMOUS_AFTER_HOURS` (3) or longer; the station is dispatching itself without operator confirmation |

The escalation from `OFFLINE` to `OFFLINE - AUTONOMOUS CONTROL ACTIVE` is
deliberate: a brief dropout is routine, but a sustained outage means nobody is
confirming recommendations, and the operator should see that stated plainly.

`probe_uplink()` is kept separate from `get_connectivity_status()` so tests and
the scenario runner never depend on a real socket.

Offline records are detected through the Digital Twin's existing
`apply_communication_outage_scenario()`, which tags records with
`communication_status: "offline"` — no parallel mechanism was introduced.

## 2. Offline mode

Every successful live weather read writes a snapshot (weather record, battery
SOC in kWh, fuel litres) to `outputs/resilience_cache.json`. When the uplink
drops, the runner loads that snapshot instead of stalling.

With no cache present (cold start), `COLD_START_WEATHER` supplies conservative
polar defaults — no sun, light wind, −25 °C — so the Twin errs toward more
heating demand and less renewable generation rather than optimistically
underestimating them. A missing or corrupt cache never raises.

## 3. Fallback policy

`safe_dispatch()` is the single entry point the rest of the system should call
instead of invoking the optimizer directly:

```python
from src.resilience import safe_dispatch

result = safe_dispatch(
    weather_record,
    battery_soc_kwh,
    fuel_remaining_litres,
    generator_1_available=True,
    generator_2_available=True,
    optimizer=forecast_optimizer,   # None until feature/forecasting lands
)
```

It falls back to deterministic Twin dispatch when the optimizer is absent,
raises any exception, or returns an incomplete result. It **always** returns a
dispatch decision — it never raises and never returns `None`.

Every result carries `dispatch_mode`, `fallback_triggered`, `fallback_reason`,
`flexible_load_shed`, `low_fuel_warning`, and a plain-English `reasoning`
string, so the fallback path is explainable too — not just the AI path.

Flexible-load guidance is derived from the Twin's own `unmet_load_kw` against
`config.FLEXIBLE_LOAD_KW`, so the critical block (`config.CRITICAL_LOAD_KW`,
20 kW) is protected first.

## 4. Scenario runner

`run_resilience_scenario()` layers the Twin's existing scenario helpers rather
than duplicating them:

```python
results = run_resilience_scenario(
    weather_records,
    storm=True,
    failed_generator="G1",
    comms_outage_hours=range(0, 8),
    initial_fuel_litres=config.LOW_FUEL_THRESHOLD_L,
)
```

While offline the optimizer is never called, since it may depend on network or
API access. Input records are never mutated.

## 5. Tests

```bash
python3 -m pytest tests/test_resilience.py -v
```

14 tests covering: connectivity state transitions; fallback on a missing
optimizer and on a raising optimizer; a working optimizer not being overridden;
worst-case survival (no sun, no wind, no fuel, both generators down, battery at
reserve); battery never discharging below `BATTERY_MIN_SOC_FRACTION`; offline
status and cache use; escalation to autonomous; the optimizer never being
called while offline; reconnection restoring `ONLINE`; the combined four-failure
scenario; the low-fuel warning; and input records not being mutated.

Full suite: **183 passed** (169 existing + 14 new), no regressions.

## 6. Demo

```bash
python3 scripts/run_resilience_demo.py
```

Four phases: normal operation → communication outage → storm + Generator 1
failure + low fuel while offline → recovery after reconnection.

---

## Remaining integration work

1. **Dashboard wiring.** The connectivity status is not yet displayed. The
   dashboard lives on `member1/digital-twin`, which is not merged into `main`
   yet. Once it is, `get_connectivity_status()` should feed a status badge in
   `dashboard/app.py` alongside the existing `calculate_status()` output.
2. **Optimizer wiring.** `feature/forecasting` is currently an empty branch
   pointing at `main`. When the optimizer exists, pass it as the `optimizer`
   argument to `safe_dispatch()`; no other change is required.
3. **Real uplink probe.** `probe_uplink()` targets a public DNS server. In
   deployment this becomes the station's satellite gateway. Note that in a
   sandboxed or firewalled environment the probe reports offline even when the
   host has connectivity — expected, not a defect.
