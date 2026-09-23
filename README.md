# AURORA-EMS

## AI-Assisted Energy Management System

AURORA-EMS is a prototype energy management system for a virtual Indian polar
research station. It combines Antarctic weather data, a physics-informed
Digital Twin, renewable-energy forecasting, and energy dispatch optimization.

> **Prototype notice:** All energy values are simulated for research and
> demonstration purposes. This project is not a real NCPOR controller.

## Current Contribution: Member 6

This branch adds the Resilience and Offline Integration layer. Its purpose is
to keep producing safe, explainable dispatch decisions when communication is
unavailable or a forecasting or optimization component fails.

The implementation is built on the team's existing Digital Twin and scenario
helpers. It does not create a second dispatch engine or replace the existing
Member 3 and Member 4 modules.

### Completed Work

| Area | Implementation | Status |
| --- | --- | --- |
| Connectivity status | `ONLINE`, `OFFLINE`, and autonomous-control escalation after three offline hours | Complete |
| Offline operation | Last-known-good weather and station-state cache with conservative cold-start defaults | Complete |
| Fallback dispatch | `safe_dispatch()` delegates to the validated Digital Twin when the optimizer is missing, incomplete, or fails | Complete |
| Failure scenarios | Storm, generator failure, low fuel, communication outage, and combined scenarios | Complete |
| Explainability | Dispatch mode, fallback reason, fuel warning, load-shed advice, and operator reasoning | Complete |
| Tests | 14 focused resilience tests plus the existing repository suite | Complete |
| Demonstration | Four-phase normal, outage, combined failure, and recovery demo | Complete |
| Documentation | Technical design and operating notes | Complete |

## Integration Status

- Local branch: `member6/resilience-offline-integration`
- Base commit: `origin/main` at `59edc4d`
- Member 6 commit: `74725d6`
- Pull request: [#6 - Add resilience offline integration](https://github.com/sinchana-aiml/AURORA-EMS/pull/6)
- PR state: Open and awaiting maintainer review
- No merge into `main` has been performed

The branch was published through the contributor fork because the contributor
account does not have direct write permission to the team repository.

## How the Resilience Layer Works

### Connectivity

`src/resilience/connectivity.py` provides a testable uplink probe and maps the
current outage duration to a dashboard-ready status:

| Status | Meaning |
| --- | --- |
| `ONLINE` | Live weather and normal operation are available |
| `OFFLINE` | Cached data is being used and operator attention is required |
| `OFFLINE - AUTONOMOUS CONTROL ACTIVE` | The outage has lasted at least three hours |

### Offline cache

`src/resilience/cache.py` stores the latest weather record, battery state of
charge, and remaining fuel in `outputs/resilience_cache.json`. The `outputs/`
directory is ignored by Git. Missing or corrupt cache data falls back to
conservative polar defaults instead of stopping the station simulation.

### Fallback dispatch

`src/resilience/fallback.py` calls the existing
`src.digital_twin.energy_balance_step()` function. The Digital Twin retains
the dispatch order:

1. Renewable generation
2. Battery discharge or charging
3. Generator 1
4. Generator 2
5. Flexible-load shedding when a shortfall remains

The fallback path protects the configured critical load and returns a complete,
explainable result rather than raising an exception or returning `None`.

### Scenario runner

`src/resilience/scenario_runner.py` composes the existing helpers in
`src.digital_twin.scenarios` and runs a weather series hour by hour. It keeps
input records unchanged, avoids calling an optimizer while offline, and tracks
battery state and fuel across the scenario.

## Repository Structure

```text
AURORA-EMS/
├── config.py                         # Shared station constants
├── data/                             # Weather and simulation inputs
├── docs/                             # Contracts, handoffs, and technical notes
├── scripts/                          # Demonstration and utility scripts
├── src/
│   ├── digital_twin/                 # Member 1/2 physics and scenarios
│   ├── dispatch/                     # Member 4 dispatch and optimization
│   ├── forecasting/                  # Member 3 forecasting services
│   └── resilience/                   # Member 6 offline safety layer
├── tests/                            # Repository and integration tests
├── requirements.txt                  # Runtime dependencies
└── requirements-dev.txt              # Test dependencies
```

## Setup

Use a virtual environment for local development:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

On macOS or Linux, use `.venv/bin/activate` instead of the PowerShell command.

## Validation

Run the focused Member 6 tests:

```bash
python -m pytest tests/test_resilience.py -v
```

Run the complete repository suite:

```bash
python -m pytest -q
```

Verified on the integration branch:

- Focused resilience tests: **14 passed**
- Full repository suite: **265 passed**
- Known output: one existing pandas date-format warning in
  `tests/test_forecasting_validation.py`

## Demo

Run the complete four-phase demonstration:

```bash
python scripts/run_resilience_demo.py
```

The demo shows:

1. Normal operation
2. Communication outage with cached weather
3. Storm, Generator 1 failure, low fuel, and offline operation together
4. Recovery after reconnection

## Remaining Work

The Member 6 implementation and validation are complete. The following work
belongs to the final team integration and deployment stage:

1. Review and merge PR #6 into the team's `main` branch.
2. Wire `get_connectivity_status()` into the dashboard status component when
   the dashboard surface is ready.
3. Pass the production optimizer through `safe_dispatch(optimizer=...)` once
   the team selects the final optimizer entry point.
4. Replace the public DNS probe with the station's satellite-gateway probe in
   deployment.
5. Validate the behavior against the deployment network and hardware
   interfaces.

## Related Documentation

- [Resilience and Offline Integration](docs/resilience_offline_integration.md)
- [Digital Twin Handoff](docs/digital_twin_handoff.md)
- [Forecasting Contract](docs/forecasting_contract.md)
- [Dispatch Handoff](docs/dispatch_handoff.md)
