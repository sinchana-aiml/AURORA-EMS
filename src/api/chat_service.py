"""AURORA AI - Energy Operations Assistant chat service."""

from __future__ import annotations

import os
import re
from typing import Any

# ---------------------------------------------------------------------------
# Project knowledge base (lightweight keyword-based RAG)
# ---------------------------------------------------------------------------

KNOWLEDGE_CHUNKS: list[dict[str, Any]] = [
    {
        "id": "project_overview",
        "title": "AURORA-EMS Project Overview",
        "keywords": ["aurora", "project", "overview", "what is", "purpose", "polar", "research", "station", "sih", "hackathon"],
        "text": (
            "AURORA-EMS is an AI-driven Energy Management System for polar research stations, "
            "developed for Smart India Hackathon 2026 (Problem Statement 26061, Clean & Green Technology). "
            "It is designed for the Bharati Indian polar research station in Antarctica (69.4069°S, 76.1956°E). "
            "The system combines weather intelligence, a physics-informed Digital Twin, renewable-energy forecasting, "
            "battery and generator modelling, energy dispatch optimization, resilience mechanisms, and an interactive "
            "3D operator dashboard. Core objective: use available renewable energy intelligently, minimize diesel "
            "dependency, protect critical station loads, and continue safe operation during communication or component failures."
        ),
    },
    {
        "id": "digital_twin",
        "title": "Digital Twin",
        "keywords": ["digital twin", "simulation", "twin", "model", "physics", "simulate"],
        "text": (
            "The AURORA-EMS Digital Twin is a physics-informed simulation of the station energy system. "
            "It models hourly energy generation, storage, and consumption under Antarctic weather conditions. "
            "Components modelled: solar PV (40 kW rated), wind turbine (50 kW rated), battery storage (300 kWh), "
            "two diesel generators (G1: 80 kW, G2: 120 kW), station electrical load (30 kW base + heating), "
            "and fuel tank (5000 L). The twin runs scenario simulations including storm, generator failure, "
            "low fuel, and communication loss. It is a prototype and does not control real hardware."
        ),
    },
    {
        "id": "solar",
        "title": "Solar PV Generation",
        "keywords": ["solar", "pv", "irradiance", "photovoltaic", "sun", "panel"],
        "text": (
            "The station has a 40 kW rated solar PV array. Output formula: "
            "P = 40 × (irradiance/1000) × (1 - 0.004 × (temp - 25)) × 0.82, clamped to [0, 40] kW. "
            "Performance ratio 0.82 accounts for wiring losses and inverter efficiency. "
            "Cold Antarctic temperatures slightly increase output relative to the 25°C reference. "
            "Solar output is zero during polar night periods."
        ),
    },
    {
        "id": "wind",
        "title": "Wind Turbine Generation",
        "keywords": ["wind", "turbine", "wind speed", "cut-in", "cut-out", "wind power"],
        "text": (
            "The station has a 50 kW rated wind turbine. Power curve: below 3 m/s = 0 kW (cut-in); "
            "3-12 m/s = linear ramp 0-50 kW; 12-25 m/s = 50 kW rated; above 25 m/s = 0 kW (cut-out for safety). "
            "The cut-out at 25 m/s is a storm-protection shutdown. Wind is often the primary renewable source "
            "in Antarctica due to persistent katabatic winds."
        ),
    },
    {
        "id": "battery",
        "title": "Battery Storage System",
        "keywords": ["battery", "soc", "state of charge", "storage", "charge", "discharge", "kwh", "battery soc"],
        "text": (
            "Battery capacity: 300 kWh total. Minimum SOC floor: 25% (75 kWh) to protect longevity. "
            "Initial SOC: 70% (210 kWh). Max charge/discharge power: 60 kW each. "
            "Charge efficiency: 95%. Discharge efficiency: 95%. Round-trip efficiency: ~90.25%. "
            "The battery is discharged when renewable generation is insufficient to meet load. "
            "It is charged when renewables exceed demand or generators produce excess. "
            "The optimizer never discharges below the 75 kWh floor."
        ),
    },
    {
        "id": "generators",
        "title": "Diesel Generators",
        "keywords": ["generator", "diesel", "fuel", "g1", "g2", "gen", "generator 1", "generator 2"],
        "text": (
            "Two diesel generators provide backup power. "
            "Generator 1 (G1): 80 kW rated, 20 kW minimum load, 3 L/h idle fuel, 0.25 L/kWh. "
            "Generator 2 (G2): 120 kW rated, 30 kW minimum load, 4 L/h idle fuel, 0.23 L/kWh. "
            "Shared fuel tank: 5000 L total, low-fuel alert at 500 L. "
            "Dispatch priority: renewables first, then battery, then G1, then G2. "
            "Generators run at minimum load if requested output is below their minimum, producing excess that charges the battery."
        ),
    },
    {
        "id": "loads",
        "title": "Station Electrical Loads",
        "keywords": ["load", "demand", "critical load", "flexible load", "heating", "power demand", "consumption"],
        "text": (
            "Station loads: Critical load 20 kW (life support, communications, essential instruments - never shed). "
            "Flexible load 10 kW (labs, non-critical equipment - can be shed during shortfalls). "
            "Heating load: 15 kW base at 0°C, +0.8 kW per °C below 0°C (e.g. at -20°C: 31 kW heating). "
            "Total electrical demand with flexible load: ~30 kW constant. "
            "Critical load protection is the highest priority in all dispatch and resilience decisions."
        ),
    },
    {
        "id": "dispatch_optimization",
        "title": "Energy Dispatch Optimization",
        "keywords": ["dispatch", "optimization", "optimizer", "strategy", "decision", "energy strategy", "or-tools", "lookahead"],
        "text": (
            "The dispatch optimizer uses a 24-hour look-ahead horizon (OR-Tools based). "
            "Dispatch priority order: 1) Renewables (zero marginal cost), 2) Battery discharge, "
            "3) Generator 1, 4) Generator 2. "
            "The optimizer minimizes diesel consumption while protecting critical loads. "
            "In a validated 24h simulation: baseline diesel 158.19 L vs optimized 81.50 L (48.48% reduction). "
            "Unmet load: 0. Critical load failures: 0. "
            "Low-fuel mode triggers flexible load shedding when fuel drops to 500 L. "
            "Forecast confidence affects battery reserve: low confidence = higher reserve (93.75 kWh floor)."
        ),
    },
    {
        "id": "forecasting",
        "title": "AI Energy Forecasting",
        "keywords": ["forecast", "forecasting", "prediction", "ai", "machine learning", "predict", "future", "horizon"],
        "text": (
            "The forecasting layer estimates future load demand, solar generation, wind generation, and weather. "
            "Forecasts include uncertainty bands (p10/p50/p90 percentiles) and confidence scores. "
            "Forecast horizon: up to 48 hours. Storm risk flag and turbine cutout risk are included. "
            "The system supports offline/fallback operation when normal forecasting inputs are unavailable. "
            "Models use scikit-learn with historical weather and telemetry features. "
            "Forecast mode is shown in each row (e.g. 'ml_model' or 'fallback')."
        ),
    },
    {
        "id": "resilience",
        "title": "Resilience and Offline Operation",
        "keywords": ["resilience", "offline", "connectivity", "communication", "loss", "outage", "fallback", "autonomous", "reconnect"],
        "text": (
            "AURORA-EMS includes an offline-first resilience layer. Connectivity states: "
            "ONLINE (normal), OFFLINE (using cached data), OFFLINE - AUTONOMOUS CONTROL ACTIVE (3+ hours outage). "
            "During communication loss: cached weather/station data is used, local dispatch continues, "
            "critical loads are protected, conservative safe-mode dispatch is applied. "
            "The system handles: generator failures, low-fuel scenarios, storm scenarios, communication loss, "
            "and combined failure scenarios. Recovery after reconnection is supported. "
            "The fallback delegates to the Digital Twin energy balance function for deterministic safe dispatch."
        ),
    },
    {
        "id": "scenarios",
        "title": "Operational Scenarios",
        "keywords": ["scenario", "storm", "failure", "low fuel", "communication loss", "both generators", "normal"],
        "text": (
            "Supported scenarios: Normal (full fuel, both generators, no storm), "
            "Storm (renewable generation reduced, wind may cut out above 25 m/s), "
            "G1 Failure (Generator 1 unavailable), G2 Failure (Generator 2 unavailable), "
            "Low Fuel (starting fuel = 500 L threshold, flexible load shed enabled), "
            "Communication Loss (conservative safe-mode, G2 disabled), "
            "Both Generators Unavailable (battery + renewables only, unmet load expected). "
            "Storm threshold: wind >= 20 m/s. Low-fuel threshold: <= 500 L."
        ),
    },
    {
        "id": "weather",
        "title": "Weather Data and NASA POWER",
        "keywords": ["weather", "nasa", "nasa power", "temperature", "irradiance", "wind speed", "antarctic", "climate"],
        "text": (
            "Weather inputs come from NASA POWER (polar weather data pipeline). "
            "Required fields per hour: timestamp, temperature_c, irradiance_w_m2, wind_speed_ms. "
            "The weather validation pipeline checks for physically plausible Antarctic values. "
            "A polar climatology model (scikit-learn, joblib) provides fallback estimates. "
            "The current prototype uses a 24-hour sample dataset for demonstration. "
            "Future integration with real NCPOR station data is planned."
        ),
    },
    {
        "id": "architecture",
        "title": "System Architecture",
        "keywords": ["architecture", "stack", "technology", "flask", "react", "vercel", "render", "backend", "frontend"],
        "text": (
            "Architecture: Polar Weather Data → Weather Validation → Digital Twin → "
            "AI Forecasting + Scenario Engine → Energy Optimization (24h dispatch) → "
            "Resilience/Offline Layer → AURORA-EMS Dashboard. "
            "Backend: Python, Flask, Pandas, NumPy, scikit-learn, OR-Tools, Gunicorn. Deployed on Render. "
            "Frontend: React, TypeScript, Vite, Tailwind CSS, Three.js, React Three Fiber. Deployed on Vercel. "
            "API: GET /api/health, GET /api/dashboard, POST /api/chat."
        ),
    },
    {
        "id": "bharati_station",
        "title": "Bharati Research Station",
        "keywords": ["bharati", "india", "ncpor", "station", "antarctica", "location", "indian"],
        "text": (
            "Bharati is India's third Antarctic research station, operated by NCPOR "
            "(National Centre for Polar and Ocean Research). Located at 69.4069°S, 76.1956°E. "
            "Designed for year-round scientific research, supporting personnel, laboratories, "
            "regulated power, heating, water, and communications. "
            "AURORA-EMS models a virtual station inspired by Bharati's operational requirements. "
            "The team has contacted NCPOR to request real station datasets for future validation."
        ),
    },
]


def _retrieve_chunks(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Keyword-based retrieval: score each chunk by keyword overlap with query."""
    q = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for chunk in KNOWLEDGE_CHUNKS:
        score = sum(1 for kw in chunk["keywords"] if kw in q)
        # Also check title words
        for word in chunk["title"].lower().split():
            if len(word) > 3 and word in q:
                score += 1
        scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    # Always include at least the top result; filter zero-score if others exist
    results = [c for s, c in scored if s > 0][:top_k]
    if not results:
        results = [scored[0][1]]  # fallback: most general chunk
    return results


# ---------------------------------------------------------------------------
# Live context builder
# ---------------------------------------------------------------------------

def build_live_context(dashboard_data: dict[str, Any]) -> str:
    """Build a compact structured context string from live dashboard data."""
    lines: list[str] = []

    station = dashboard_data.get("station", {})
    lines.append(f"STATION: {station.get('name', 'Bharati')} | Lat {station.get('latitude', -69.41):.2f}°S, Lon {station.get('longitude', 76.20):.2f}°E")

    telemetry = dashboard_data.get("telemetry", {})
    latest = telemetry.get("latest", {})
    if latest:
        lines.append("\nCURRENT TELEMETRY:")
        lines.append(f"  Timestamp: {latest.get('timestamp', 'N/A')}")
        lines.append(f"  Total Load: {latest.get('total_load_kw', 0):.1f} kW")
        lines.append(f"  Solar Power: {latest.get('solar_power_kw', 0):.1f} kW")
        lines.append(f"  Wind Power: {latest.get('wind_power_kw', 0):.1f} kW")
        lines.append(f"  Renewable Used: {latest.get('renewable_used_kw', 0):.1f} kW")
        lines.append(f"  Generator Total: {latest.get('generator_total_kw', 0):.1f} kW (G1: {latest.get('generator_1_power_kw', 0):.1f} kW, G2: {latest.get('generator_2_power_kw', 0):.1f} kW)")
        lines.append(f"  Battery SOC: {latest.get('battery_soc_kwh', 0):.1f} kWh")
        lines.append(f"  Battery Discharge: {latest.get('battery_discharge_kw', 0):.1f} kW | Charge: {latest.get('battery_charge_kw', 0):.1f} kW")
        lines.append(f"  Fuel Remaining: {latest.get('fuel_remaining_litres', 0):.1f} L")
        lines.append(f"  Unmet Load: {latest.get('unmet_load_kw', 0):.1f} kW")
        lines.append(f"  Critical Load Served: {latest.get('critical_load_served', False)}")
        lines.append(f"  Temperature: {latest.get('temperature_c', 0):.1f}°C | Wind: {latest.get('wind_speed_ms', 0):.1f} m/s | Irradiance: {latest.get('irradiance_w_m2', 0):.1f} W/m²")

    forecast = dashboard_data.get("forecast", {})
    if forecast.get("available") and forecast.get("rows"):
        row0 = forecast["rows"][0]
        lines.append("\nFORECAST (next step):")
        lines.append(f"  Horizon: {forecast.get('horizon_hours', 24)}h | Mode: {row0.get('forecast_mode', 'N/A')}")
        lines.append(f"  Load p50: {row0.get('total_load_kw_p50', 0):.1f} kW | Net Load p50: {row0.get('net_load_kw_p50', 0):.1f} kW")
        lines.append(f"  Solar p50: {row0.get('solar_power_kw_p50', 0):.1f} kW | Wind p50: {row0.get('wind_power_kw_p50', 0):.1f} kW")
        lines.append(f"  Storm Risk: {row0.get('storm_risk_flag', False)} | Turbine Cutout Risk: {row0.get('turbine_cutout_risk', False)}")
        lines.append(f"  Confidence: {row0.get('confidence_score', 0):.0%}")
    else:
        lines.append(f"\nFORECAST: Unavailable ({forecast.get('error', 'no data')})")

    dispatch = dashboard_data.get("dispatch", {})
    if dispatch.get("available") and dispatch.get("history"):
        last = dispatch["history"][-1]
        summary = dispatch.get("summary", {})
        lines.append("\nDISPATCH (latest optimized step):")
        lines.append(f"  Strategy: {dispatch.get('strategy', 'N/A')}")
        lines.append(f"  Renewable Used: {last.get('renewable_used_kw', 0):.1f} kW | Curtailed: {last.get('renewable_curtailed_kw', 0):.1f} kW")
        lines.append(f"  Battery: charge {last.get('battery_charge_kw', 0):.1f} kW / discharge {last.get('battery_discharge_kw', 0):.1f} kW | SOC {last.get('battery_soc_kwh', 0):.1f} kWh")
        lines.append(f"  Generator Total: {last.get('generator_total_kw', 0):.1f} kW (G1: {last.get('generator_1_kw', 0):.1f} / G2: {last.get('generator_2_kw', 0):.1f})")
        lines.append(f"  Fuel Remaining: {last.get('fuel_remaining_litres', 0):.1f} L | Fuel Used (total): {summary.get('optimized_fuel_used_litres', 0):.1f} L")
        lines.append(f"  Unmet Load: {last.get('unmet_load_kw', 0):.1f} kW | Critical Load Served: {last.get('critical_load_served', False)}")
        lines.append(f"  Low Fuel Mode: {last.get('low_fuel_mode', False)} | Flexible Load Shed: {last.get('flexible_load_shed_kw', 0):.1f} kW")
    else:
        lines.append(f"\nDISPATCH: Unavailable ({dispatch.get('error', 'no data')})")

    resilience = dashboard_data.get("resilience", {})
    lines.append("\nRESILIENCE:")
    lines.append(f"  Connectivity: {resilience.get('connectivity_status', 'UNKNOWN')}")
    lines.append(f"  Scenario: {resilience.get('scenario', 'normal')}")
    r_latest = resilience.get("latest") or {}
    if r_latest:
        lines.append(f"  Dispatch Mode: {r_latest.get('dispatch_mode', 'N/A')}")
        lines.append(f"  Storm Active: {r_latest.get('storm_active', False)}")
        lines.append(f"  Fallback Triggered: {r_latest.get('fallback_triggered', False)}")
        lines.append(f"  Low Fuel Warning: {r_latest.get('low_fuel_warning', False)}")
        lines.append(f"  Reasoning: {r_latest.get('reasoning', 'N/A')}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are AURORA AI, the Energy Operations Assistant for the Bharati polar research station energy management system (AURORA-EMS).

Your job is to explain the station's energy state, forecasts, optimization decisions, and resilience status using the provided AURORA project knowledge and current live station data.

Rules:
1. Never invent current sensor or telemetry values. Use only the values provided in the LIVE STATION CONTEXT.
2. For current-state questions, always reference the live station context values explicitly.
3. Clearly distinguish observed data (from telemetry) from interpretation (your reasoning).
4. If information is unavailable in the context, say so explicitly.
5. Be concise and operationally useful. Use short bullet points when listing values.
6. Do not claim that an action was actually performed unless the system explicitly performed it.
7. Do not fabricate sources or invent equipment specifications not in the knowledge base.
8. When explaining optimization decisions, base the explanation on the supplied dispatch/telemetry context.
9. Critical-load continuity and system resilience are the highest priorities in all energy decisions.
10. You are a prototype demonstration system. Always be accurate about this when asked.

Response style: concise, technically accurate, bullet points for values, short paragraphs for explanations."""


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def _call_llm(messages: list[dict[str, str]]) -> str:
    """Call the configured LLM API. Returns answer string."""
    api_key = os.environ.get("LLM_API_KEY", "")
    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    if not api_key:
        return (
            "AURORA AI is not configured: no LLM API key is set on this deployment.\n\n"
            "To enable the AI assistant, add the `LLM_API_KEY` environment variable to the Render backend service.\n\n"
            "You can still explore all live telemetry, forecasts, dispatch, and resilience data in the dashboard panels above."
        )

    import urllib.request
    import json as _json

    payload = _json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": 600,
        "temperature": 0.2,
    }).encode()

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = _json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        return f"AURORA AI encountered an error communicating with the LLM provider: {exc}"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def answer_chat(
    message: str,
    history: list[dict[str, str]],
    dashboard_data: dict[str, Any],
) -> dict[str, Any]:
    """Build context, retrieve knowledge, call LLM, return answer + metadata."""
    message = message.strip()[:1000]

    # Retrieve relevant knowledge chunks
    chunks = _retrieve_chunks(message, top_k=3)
    knowledge_text = "\n\n".join(
        f"[{c['title']}]\n{c['text']}" for c in chunks
    )
    source_titles = [c["title"] for c in chunks]

    # Build live context
    live_ctx = build_live_context(dashboard_data)

    # Compose messages
    user_content = (
        f"LIVE STATION CONTEXT:\n{live_ctx}\n\n"
        f"AURORA PROJECT KNOWLEDGE:\n{knowledge_text}\n\n"
        f"OPERATOR QUESTION: {message}"
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Include last 4 history turns max
    for turn in history[-4:]:
        role = turn.get("role", "user")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": str(turn.get("content", ""))[:800]})

    messages.append({"role": "user", "content": user_content})

    answer = _call_llm(messages)

    return {
        "answer": answer,
        "sources": source_titles,
        "context_type": "live+rag",
    }
