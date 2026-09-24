# Resilience and Offline Integration

**Branch:** `member6/resilience-offline-integration`
**Package:** `src/resilience/`
**Pull request:** [#6 - Add resilience offline integration](https://github.com/sinchana-aiml/AURORA-EMS/pull/6)

This contribution is the Member 6 safety layer for AURORA-EMS. It keeps the
station producing safe, explainable dispatch decisions when the uplink is down
or a forecasting or optimization component fails.

All energy values remain simulated for prototype and research purposes. This is
not a real NCPOR controller.

## Design Decisions

The fallback does not reimplement dispatch. It delegates to the validated
Digital Twin function `src.digital_twin.energy_balance_step()`, which applies
renewables, battery, Generator 1, and Generator 2 in the existing dispatch
order.

The scenario runner also reuses the Digital Twin helpers in
`src.digital_twin.scenarios`. This keeps Member 6 aligned with the team's
existing weather schema, constants, and failure behavior.

## Components

| File | Responsibility |
| --- | --- |
| `src/resilience/connectivity.py` | Uplink probe and dashboard-ready status values |
| `src/resilience/cache.py` | Last-known-good weather and station-state cache |
| `src/resilience/fallback.py` | Optimizer wrapper and deterministic Digital Twin fallback |
| `src/resilience/scenario_runner.py` | Combined outage, storm, generator, and fuel scenarios |
| `tests/test_resilience.py` | 14 focused resilience tests |
| `scripts/run_resilience_demo.py` | Four-phase end-to-end demonstration |

## Connectivity States

| Status | Meaning |
| --- | --- |
| `ONLINE` | Live weather and normal operation are available |
| `OFFLINE` | Cached data is being used and operator attention is required |
| `OFFLINE - AUTONOMOUS CONTROL ACTIVE` | The outage has lasted at least three consecutive hours |

The socket probe is isolated from status mapping so tests remain deterministic.
Offline records are identified through the existing
`communication_status: "offline"` scenario tag.

## Offline Cache

Successful live records save a JSON snapshot containing:

- Weather data
- Battery state of charge in kWh
- Remaining fuel in litres

The default path is `outputs/resilience_cache.json`. The `outputs/` directory
is ignored by Git. Missing or corrupt cache data uses conservative cold-start
weather instead of raising an exception.

## Fallback Policy

`safe_dispatch()` is the single entry point for dispatch calls that may depend
on forecasting or optimization. It uses the deterministic fallback when:

- No optimizer is supplied
- The optimizer raises an exception
- The optimizer returns an incomplete result

Every fallback result includes dispatch mode, fallback reason, fuel warning,
load-shed guidance, and plain-English reasoning. The critical load is protected
using the existing configured constants.

## Scenario Runner

`run_resilience_scenario()` can combine:

- Storm conditions
- Generator 1 or Generator 2 failure
- Low fuel
- Communication outage
- Optional optimizer failure

While offline, the optimizer is not called. Input weather records are copied
rather than mutated, and battery and fuel state are carried between hours.

## Validation Evidence

Commands run on the integration branch:

```bash
python -m pytest tests/test_resilience.py -q
python -m pytest -q
python scripts/run_resilience_demo.py
```

Results:

- Focused resilience tests: **14 passed**
- Full repository suite: **265 passed**
- Demo: all four phases completed successfully
- One existing pandas date-format warning remains in
  `tests/test_forecasting_validation.py`; it did not fail the suite

## Completed Member 6 Work

The implementation, tests, demo, documentation, local commit, branch push,
and pull request are complete.

The work is recorded in commit `74725d6` and is currently awaiting maintainer
review in PR #6. No merge into `main` has been performed.

## Remaining Team Integration Work

1. Review and merge PR #6 into the team's `main` branch.
2. Wire `get_connectivity_status()` into the dashboard status component when
   the dashboard surface is ready.
3. Pass the selected production optimizer through `safe_dispatch(optimizer=...)`.
4. Replace the public DNS probe with the station's satellite-gateway probe for
   deployment.
5. Validate the behavior against deployment network and hardware interfaces.
