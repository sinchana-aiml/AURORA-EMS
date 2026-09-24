# AURORA-EMS Dashboard

This Streamlit dashboard supports two display modes:

- **Demo scenario** uses deterministic local Summer, Winter, or Storm data.
- **Digital Twin + validated weather sample** loads `data/sample/digital_twin_weather_24h.csv`, validates it with the existing weather loader, and runs the existing Digital Twin simulation.

Station energy values are simulated for prototype demonstration.

## Run locally

From the repository root:

```powershell
python -m pip install streamlit
python -m streamlit run dashboard/app.py
```

In Digital Twin mode, the dashboard displays a mapped view of the Twin's existing output: load, solar, wind, generator output, battery SOC, remaining fuel, and unmet load. Weather input is the validated NASA POWER sample; the station energy response is simulated by the Digital Twin.

## Empty-fuel critical demonstration

Choose **Digital Twin + validated weather sample** as the data source, then select **Empty fuel — critical demonstration** under **Digital Twin scenario**. The dashboard runs the same validated weather sample through the existing Digital Twin with `initial_fuel_litres=0.0`. Fuel, generator output, and unmet load are the Twin's actual outputs; no values are fabricated by the dashboard.

The resilience panel is a static demo placeholder only. This dashboard does not implement synchronization, satellite operation, network recovery, load shedding, generator failover, forecasting, optimization, or any other backend resilience behavior.
