"""Streamlit UI for AURORA-EMS demo scenarios and Digital Twin output."""

from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from dashboard.data_adapter import load_digital_twin_sample
except ModuleNotFoundError:  # Supports `streamlit run dashboard/app.py`.
    from data_adapter import load_digital_twin_sample


STATION_NAME = "Bharati Research Station"
DEMO_BATTERY_CAPACITY_KWH = 600.0
DEMO_FUEL_BURN_L_PER_KWH = 0.27


def apply_console_styles() -> None:
    """Apply a small local visual system for the operations-console UI."""
    st.markdown(
        """
        <style>
        .stApp { background: #0a1322; color: #dae2f8; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
        .block-container { max-width: 1500px; padding-top: 1.25rem; padding-bottom: 2.5rem; }
        h1, h2, h3 { color: #dae2f8; letter-spacing: -0.02em; }
        h2, h3 { font-size: 1.02rem; margin-top: 0.15rem; }
        [data-testid="stSidebar"] { background: #050e1d; border-right: 1px solid #29384a; }
        [data-testid="stSidebar"] .block-container { padding-top: 1rem; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"], [data-testid="stSidebar"] label { color: #bdc8d1; }
        [data-testid="stSidebar"] [data-baseweb="select"] > div, [data-testid="stSidebar"] input { background: #131c2b !important; border-color: #3e484f !important; color: #dae2f8 !important; }
        .ops-header { align-items: center; background: #131c2b; border: 1px solid #303d50; border-radius: 8px; box-shadow: 0 8px 20px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255,255,255,0.05); display: flex; gap: 0.8rem; justify-content: space-between; margin-bottom: 1rem; padding: 0.82rem 1rem; }
        .ops-header-main { align-items: center; display: flex; gap: 0.75rem; min-width: 0; }
        .ops-mark { align-items: center; background: #38bdf8; border-radius: 5px; color: #00354a; display: flex; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.74rem; font-weight: 800; height: 2rem; justify-content: center; width: 2rem; }
        .ops-header h1 { font-size: 1.15rem; line-height: 1.2; margin: 0; }
        .ops-header p { color: #bdc8d1; font-size: 0.76rem; margin: 0.16rem 0 0; overflow-wrap: anywhere; }
        .prototype-tag { background: #2c3545; border: 1px solid #3e484f; border-radius: 4px; color: #4cd7f6; display: inline-block; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.63rem; font-weight: 700; letter-spacing: 0.06em; padding: 0.28rem 0.45rem; text-transform: uppercase; white-space: nowrap; }
        .status-banner { align-items: center; background: #17202f; border: 1px solid #3e484f; border-radius: 9px; border-left: 5px solid; box-shadow: 0 12px 28px -10px rgba(0, 0, 0, 0.75), inset 0 1px 0 rgba(255,255,255,0.05); display: flex; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.86rem; font-weight: 700; gap: 0.65rem; margin: 0.85rem 0 0.6rem; padding: 0.9rem 1rem; }
        .status-normal { border-left-color: #56e5a9; color: #56e5a9; }
        .status-warning { border-left-color: #4cd7f6; color: #4cd7f6; }
        .status-critical { border-left-color: #ffb4ab; color: #ffb4ab; }
        .section-kicker { color: #7bd0ff; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em; margin: 1.2rem 0 0.25rem; text-transform: uppercase; }
        div[data-testid="stMetric"] { background: #131c2b; border: 1px solid #344256; border-radius: 7px; box-shadow: 0 8px 18px -11px rgba(0, 0, 0, 0.9), inset 0 1px 0 rgba(255,255,255,0.045); min-height: 108px; padding: 0.72rem 0.8rem; }
        div[data-testid="stMetricLabel"] { color: #bdc8d1; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.71rem; letter-spacing: 0.03em; text-transform: uppercase; }
        div[data-testid="stMetricValue"] { color: #dae2f8; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 1.42rem; font-weight: 700; }
        div[data-testid="stMetricDelta"] { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.72rem; }
        [data-testid="stVerticalBlockBorderWrapper"] { background: #17202f; border-color: #344256; border-radius: 9px; box-shadow: 0 12px 26px -13px rgba(0, 0, 0, 0.9), inset 0 1px 0 rgba(255,255,255,0.04); }
        .sidebar-brand { background: #131c2b; border: 1px solid #303d50; border-radius: 6px; margin-bottom: 1rem; padding: 0.72rem; }
        .sidebar-brand strong { color: #dae2f8; font-size: 1rem; letter-spacing: 0.05em; }
        .sidebar-brand span { color: #4cd7f6; display: block; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.7rem; margin-top: 0.22rem; }
        .station-node, .telemetry-feed { background: #131c2b; border: 1px solid #303d50; border-radius: 6px; margin-bottom: 0.7rem; padding: 0.7rem; }
        .station-node-label, .telemetry-label, .sidebar-group { color: #bdc8d1; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.64rem; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; }
        .station-node-name { color: #dae2f8; font-size: 0.98rem; font-weight: 700; margin-top: 0.25rem; }
        .station-node-coords, .telemetry-detail { color: #4cd7f6; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.7rem; margin-top: 0.22rem; }
        .telemetry-value { color: #dae2f8; font-size: 0.78rem; font-weight: 600; margin-top: 0.24rem; }
        .sidebar-group { color: #7bd0ff; margin: 0.95rem 0 0.35rem; }
        .placeholder-note { background: #131c2b; border: 1px solid #344256; border-left: 4px solid #38bdf8; border-radius: 6px; color: #bdc8d1; font-size: 0.84rem; padding: 0.65rem 0.78rem; }
        [data-testid="stAlert"] { background: #17202f; border-color: #3e484f; color: #dae2f8; }
        [data-testid="stCaptionContainer"] { color: #bdc8d1; }
        @media (max-width: 900px) { .block-container { padding-left: 0.85rem; padding-right: 0.85rem; } .ops-header { align-items: flex-start; flex-direction: column; } .ops-header h1 { font-size: 1rem; } .prototype-tag { white-space: normal; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_status_banner(status: str, status_text: str) -> None:
    """Render the dashboard's single horizontal operational-status banner."""
    status_class = {"NORMAL": "normal", "WARNING": "warning", "CRITICAL": "critical"}[status]
    st.markdown(
        f'<div class="status-banner status-{status_class}">STATUS // {status} &nbsp;—&nbsp; {status_text}</div>',
        unsafe_allow_html=True,
    )


def get_demo_data(mode: str = "Summer") -> pd.DataFrame:
    """Return one deterministic 24-hour set of prototype station readings."""
    mode_settings = {
        "Summer": {"solar": 185.0, "wind": 62.0, "load": 155.0, "soc": 72.0, "fuel": 5400.0},
        "Winter": {"solar": 42.0, "wind": 76.0, "load": 178.0, "soc": 48.0, "fuel": 4550.0},
        "Storm": {"solar": 18.0, "wind": 108.0, "load": 205.0, "soc": 34.0, "fuel": 3600.0},
    }[mode]
    solar_profile = [0, 0, 0, 0, 0, 0.02, 0.10, 0.28, 0.50, 0.72, 0.88, 0.98,
                     1.0, 0.94, 0.78, 0.56, 0.32, 0.12, 0.03, 0, 0, 0, 0, 0]
    wind_profile = [0.62, 0.57, 0.52, 0.48, 0.50, 0.58, 0.66, 0.73, 0.80, 0.84, 0.78, 0.70,
                    0.65, 0.69, 0.76, 0.86, 0.95, 1.0, 0.91, 0.83, 0.76, 0.70, 0.67, 0.64]
    load_profile = [0.90, 0.87, 0.84, 0.83, 0.84, 0.88, 0.96, 1.02, 1.00, 0.96, 0.94, 0.93,
                    0.95, 0.97, 1.00, 1.04, 1.10, 1.17, 1.22, 1.24, 1.17, 1.08, 1.00, 0.94]

    rows: list[dict[str, float | pd.Timestamp]] = []
    fuel = mode_settings["fuel"]
    for hour in range(24):
        solar = round(mode_settings["solar"] * solar_profile[hour], 1)
        wind = round(mode_settings["wind"] * wind_profile[hour], 1)
        load = round(mode_settings["load"] * load_profile[hour], 1)
        generator = round(max(0.0, load - solar - wind - 24.0), 1)
        fuel -= generator * DEMO_FUEL_BURN_L_PER_KWH
        soc_percent = max(21.0, min(96.0, mode_settings["soc"] + solar * 0.13 + wind * 0.04 - generator * 0.10))
        rows.append({
            "timestamp": pd.Timestamp("2026-01-15") + pd.Timedelta(hours=hour),
            "load_kw": load,
            "solar_kw": solar,
            "wind_kw": wind,
            "generator_kw": generator,
            "battery_soc_kwh": round(DEMO_BATTERY_CAPACITY_KWH * soc_percent / 100, 1),
            "fuel_litres": round(fuel, 1),
            "unmet_load_kw": 0.0,
        })

    data = pd.DataFrame(rows)
    data.attrs["battery_capacity_kwh"] = DEMO_BATTERY_CAPACITY_KWH
    data.attrs["initial_fuel_litres"] = mode_settings["fuel"]
    return data


def calculate_status(current: pd.Series, battery_capacity_kwh: float) -> tuple[str, str]:
    """Classify the displayed simulation or demo reading for dashboard status."""
    battery_soc_percent = current["battery_soc_kwh"] / battery_capacity_kwh * 100
    if current["unmet_load_kw"] > 0:
        return "CRITICAL", "CRITICAL — Unmet load detected"
    if current["fuel_litres"] < 1500 or battery_soc_percent < 25:
        return "WARNING", "WARNING — Low fuel or low battery"
    return "NORMAL", "NORMAL — Station operating normally"


def render_dashboard(
    data: pd.DataFrame,
    mode: str,
    data_source: str,
    empty_fuel_demonstration: bool = False,
) -> None:
    """Render shared dashboard panels for demo data or Digital Twin output."""
    current = data.iloc[-1]
    battery_capacity_kwh = data.attrs.get("battery_capacity_kwh", DEMO_BATTERY_CAPACITY_KWH)
    battery_soc_percent = current["battery_soc_kwh"] / battery_capacity_kwh * 100
    status, status_text = calculate_status(current, battery_capacity_kwh)
    initial_fuel_litres = data.attrs.get("initial_fuel_litres", data["fuel_litres"].iloc[0])
    fuel_burn = max(0.0, initial_fuel_litres - current["fuel_litres"])
    elapsed_hours = len(data) - 1
    fuel_days = None if fuel_burn <= 0 or elapsed_hours <= 0 else current["fuel_litres"] / (fuel_burn / elapsed_hours * 24)
    total_generator_energy_kwh = data["generator_kw"].sum()
    maximum_unmet_load_kw = data["unmet_load_kw"].max()

    display_context = f"{mode} mode" if data_source == "Demo scenario" else "Digital Twin simulation"
    st.markdown(
        f"""
        <div class="ops-header">
          <div class="ops-header-main">
            <div class="ops-mark">AE</div>
            <div>
              <h1>AURORA-EMS</h1>
              <p>Polar Station Energy Command Center — {STATION_NAME}</p>
            </div>
          </div>
          <span class="prototype-tag">Prototype · Local simulation · {display_context}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.warning("Station energy values are simulated for prototype demonstration.")
    if empty_fuel_demonstration:
        st.error("CRITICAL DEMONSTRATION — Fuel unavailable; generator output is limited by the Digital Twin.")
    if data_source == "Digital Twin + validated weather sample":
        st.caption("Weather input: validated NASA POWER Antarctic sample · Station energy response: simulated by the Digital Twin.")
        st.caption(f"First timestamp: {data['timestamp'].iloc[0]} · Last timestamp: {data['timestamp'].iloc[-1]}")

    render_status_banner(status, status_text)
    st.caption("Status rules: NORMAL — Station operating normally · WARNING — Low fuel or low battery · CRITICAL — Unmet load detected")

    st.markdown('<p class="section-kicker">Latest simulation hour</p>', unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("Power balance")
        top_row = st.columns(4)
        top_row[0].metric("Current load", f"{current['load_kw']:.1f} kW")
        top_row[1].metric("Solar generation", f"{current['solar_kw']:.1f} kW")
        top_row[2].metric("Wind generation", f"{current['wind_kw']:.1f} kW")
        top_row[3].metric("Generator output", f"{current['generator_kw']:.1f} kW")

    with st.container(border=True):
        st.subheader("Storage and fuel")
        bottom_row = st.columns(2)
        bottom_row[0].metric("Battery SOC", f"{current['battery_soc_kwh']:.1f} kWh", f"{battery_soc_percent:.1f}%")
        bottom_row[1].metric(
            "Unmet load",
            f"{current['unmet_load_kw']:.1f} kW",
            "CRITICAL" if status == "CRITICAL" else None,
            delta_color="inverse",
        )

    with st.container(border=True):
        st.subheader("Fuel outlook")
        fuel_row = st.columns(2)
        fuel_row[0].metric("Fuel remaining", f"{current['fuel_litres']:,.0f} litres")
        fuel_row[1].metric("Estimated fuel days remaining", "N/A" if fuel_days is None else f"{fuel_days:.1f} days")

    with st.container(border=True):
        st.subheader("Simulation summary")
        summary_top = st.columns(3)
        summary_top[0].metric("Number of simulation hours", f"{len(data)}")
        summary_top[1].metric("First timestamp", str(data["timestamp"].iloc[0]))
        summary_top[2].metric("Last timestamp", str(data["timestamp"].iloc[-1]))
        summary_bottom = st.columns(3)
        summary_bottom[0].metric("Total generator energy", f"{total_generator_energy_kwh:.1f} kWh")
        summary_bottom[1].metric("Total fuel used", f"{fuel_burn:.1f} litres")
        summary_bottom[2].metric("Maximum unmet load", f"{maximum_unmet_load_kw:.1f} kW")

    with st.container(border=True):
        st.subheader("Energy profile (power in kW; Battery SOC in kWh)")
        chart_data = data.set_index("timestamp")[["load_kw", "solar_kw", "wind_kw", "generator_kw", "battery_soc_kwh"]].rename(
            columns={
                "load_kw": "Load",
                "solar_kw": "Solar",
                "wind_kw": "Wind",
                "generator_kw": "Generator",
                "battery_soc_kwh": "Battery SOC",
            }
        )
        st.line_chart(chart_data, width="stretch", height=360)
        if data_source == "Digital Twin + validated weather sample":
            st.caption("Power values are kW; battery state of charge is kWh. Readings are simulated Digital Twin output.")
        else:
            st.caption("Power values are kW; battery state of charge is kWh. All readings are local deterministic demo data.")

    with st.container(border=True):
        st.subheader("Resilience status — display placeholder")
        st.markdown(
            '<div class="placeholder-note">Display-only placeholder. No offline, synchronization, load-shedding, failover, or resilience backend logic is implemented.</div>',
            unsafe_allow_html=True,
        )
        resilience = st.columns(5)
        resilience[0].metric("Tier 0 loads", "Protected")
        resilience[1].metric("Tier 1 loads", "Protected")
        resilience[2].metric("Flexible loads", "Normal")
        resilience[3].metric("Generator 1", "Available")
        resilience[4].metric("Generator 2", "Available")


def main() -> None:
    """Configure the page and choose an explicit dashboard data source."""
    st.set_page_config(page_title="AURORA-EMS Dashboard", page_icon="❄️", layout="wide")
    apply_console_styles()
    st.sidebar.markdown(
        '<div class="sidebar-brand"><strong>AURORA-EMS</strong><span>Polar station operations console</span></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        '<div class="station-node"><div class="station-node-label">Station node</div><div class="station-node-name">Bharati Station</div><div class="station-node-coords">69°24′S, 76°11′E</div></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        '<div class="telemetry-feed"><div class="telemetry-label">Operational telemetry feed</div><div class="telemetry-value">Digital Twin + NASA sample</div><div class="telemetry-detail">LOCAL SIMULATION ACTIVE</div></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown('<p class="sidebar-group">Scenario controls</p>', unsafe_allow_html=True)
    st.sidebar.text_input("Station", value=STATION_NAME, disabled=True)
    data_source = st.sidebar.selectbox("Data source", ["Demo scenario", "Digital Twin + validated weather sample"])
    mode = st.sidebar.selectbox("Mode", ["Summer", "Winter", "Storm"])
    digital_twin_scenario = "Normal fuel"
    if data_source == "Digital Twin + validated weather sample":
        digital_twin_scenario = st.sidebar.selectbox(
            "Digital Twin scenario",
            ["Normal fuel", "Empty fuel — critical demonstration"],
        )
    st.sidebar.markdown('<p class="sidebar-group">Data provenance</p>', unsafe_allow_html=True)
    st.sidebar.caption("Data label: Simulated station energy data")
    st.sidebar.caption("Weather input: validated NASA POWER Antarctic sample")
    st.sidebar.caption("Station energy response: simulated by the Digital Twin")
    st.sidebar.divider()
    st.sidebar.warning("Station energy values are simulated for prototype demonstration.")
    st.sidebar.info("Demo scenarios are local and deterministic. Digital Twin mode uses the validated repository sample.")

    if data_source == "Demo scenario":
        render_dashboard(get_demo_data(mode), mode, data_source)
        return
    try:
        empty_fuel_demonstration = digital_twin_scenario == "Empty fuel — critical demonstration"
        simulation_data = load_digital_twin_sample(
            initial_fuel_litres=0.0 if empty_fuel_demonstration else None
        )
    except Exception as error:
        st.error(f"Unable to load the validated weather sample or run the Digital Twin: {error}")
        st.info("Select 'Demo scenario' in the sidebar to use the local demonstration data explicitly.")
        return
    render_dashboard(
        simulation_data,
        mode,
        data_source,
        empty_fuel_demonstration=empty_fuel_demonstration,
    )


if __name__ == "__main__":
    main()
