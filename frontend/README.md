# AURORA-EMS React Digital Twin UI

This is a standalone React/Vite presentation client. It intentionally leaves the
existing Python Digital Twin, Streamlit dashboard, simulation, and weather data
contracts unchanged.

## Run

```powershell
cd frontend
npm install
npm run dev
```

## Production check

```powershell
npm run build
```

The interactive Three.js globe is procedural: no static globe or dashboard image
is used. Drag to rotate, scroll to zoom, click a station marker to update the
telemetry rail, or use **Center Antarctica** to reset the view.
