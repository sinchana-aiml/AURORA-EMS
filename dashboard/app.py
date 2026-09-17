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
    fuel_burn = data["fuel_litres"].iloc[0] - data["fuel_litres"].iloc[-1]
    elapsed_hours = len(data) - 1
    fuel_days = None if fuel_burn <= 0 or elapsed_hours <= 0 else current["fuel_litres"] / (fuel_burn / elapsed_hours * 24)

    st.title("AURORA-EMS — Polar Station Energy Dashboard")
    display_context = f"{mode} mode" if data_source == "Demo scenario" else "Digital Twin simulation"
    st.caption(f"{STATION_NAME} · {display_context} · {data_source}")
    st.warning("Station energy values are simulated for prototype demonstration.")
    if empty_fuel_demonstration:
        st.error("CRITICAL DEMONSTRATION — Fuel unavailable; generator output is limited by the Digital Twin.")
    if data_source == "Digital Twin + validated weather sample":
        st.caption("Weather input: validated NASA POWER sample; station energy response: simulated by the Digital Twin.")
        st.caption(f"First timestamp: {data['timestamp'].iloc[0]} · Last timestamp: {data['timestamp'].iloc[-1]}")

    if status == "NORMAL":
        st.success(status_text)
    elif status == "WARNING":
        st.warning(status_text)
    else:
        st.error(status_text)
    st.caption("Status rules: NORMAL — Station operating normally · WARNING — Low fuel or low battery · CRITICAL — Unmet load detected")

    top_row = st.columns(4)
    top_row[0].metric("Current load", f"{current['load_kw']:.1f} kW")
    top_row[1].metric("Solar generation", f"{current['solar_kw']:.1f} kW")
    top_row[2].metric("Wind generation", f"{current['wind_kw']:.1f} kW")
    top_row[3].metric("Generator output", f"{current['generator_kw']:.1f} kW")

    bottom_row = st.columns(4)
    bottom_row[0].metric("Battery SOC", f"{current['battery_soc_kwh']:.1f} kWh", f"{battery_soc_percent:.1f}%")
    bottom_row[1].metric("Fuel remaining", f"{current['fuel_litres']:,.0f} litres")
    bottom_row[2].metric("Unmet load", f"{current['unmet_load_kw']:.1f} kW")
    bottom_row[3].metric("Estimated fuel days remaining", "N/A" if fuel_days is None else f"{fuel_days:.1f} days")

    st.subheader("24-hour energy profile")
    chart_data = data.set_index("timestamp")[["load_kw", "solar_kw", "wind_kw", "generator_kw", "battery_soc_kwh"]]
    st.line_chart(chart_data, use_container_width=True)
    if data_source == "Digital Twin + validated weather sample":
        st.caption("Power values are kW; battery state of charge is kWh. Readings are simulated Digital Twin output.")
    else:
        st.caption("Power values are kW; battery state of charge is kWh. All readings are local deterministic demo data.")

    st.subheader("Resilience status (demo placeholder)")
    st.caption("Display-only placeholder. No offline, synchronization, load-shedding, failover, or resilience backend logic is implemented.")
    resilience = st.columns(5)
    resilience[0].metric("Tier 0 loads", "Protected")
    resilience[1].metric("Tier 1 loads", "Protected")
    resilience[2].metric("Flexible loads", "Normal")
    resilience[3].metric("Generator 1", "Available")
    resilience[4].metric("Generator 2", "Available")


def main() -> None:
    """Configure the page and choose an explicit dashboard data source."""
    st.set_page_config(page_title="AURORA-EMS Dashboard", page_icon="❄️", layout="wide")
    st.sidebar.header("Station settings")
    st.sidebar.text_input("Station", value=STATION_NAME, disabled=True)
    data_source = st.sidebar.selectbox("Data source", ["Demo scenario", "Digital Twin + validated weather sample"])
    mode = st.sidebar.selectbox("Mode", ["Summer", "Winter", "Storm"])
    digital_twin_scenario = "Normal fuel"
    if data_source == "Digital Twin + validated weather sample":
        digital_twin_scenario = st.sidebar.selectbox(
            "Digital Twin scenario",
            ["Normal fuel", "Empty fuel — critical demonstration"],
        )
    st.sidebar.caption("Data label: Simulated station energy data")
    st.sidebar.caption("Weather source: NASA POWER Antarctic weather data (Digital Twin mode)")
    st.sidebar.divider()
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
