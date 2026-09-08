# AURORA-EMS — AI-Assisted Energy Management System

A prototype energy management system for a virtual Indian polar research station.
Uses Antarctic weather data and a physics-informed digital twin to simulate station
energy flows, storage, generation, and failure scenarios.

> **Note:** All energy values are simulated for prototype/research purposes.
> This is NOT a real NCPOR controller.

## Modules

| Member | Module |
|--------|--------|
| Member 1 | Digital Twin & Energy Simulation |

## Project Structure

```
AURORA-EMS/
├── config.py          # Station constants and physical parameters
├── simulator.py       # Core digital twin simulation engine
├── scenarios.py       # Failure and storm scenario handlers
├── data/              # Weather and load CSV/JSON input files
├── outputs/           # Simulation result CSVs
├── dashboard/         # Streamlit UI (later phase)
└── tests/             # Unit tests
```

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python simulator.py
```
