# AURORA-EMS
# Member 4 — 24-Hour Baseline Dispatch Runner

import config

from src.digital_twin.simulation import run_simulation
from src.digital_twin.weather_loader import load_weather_csv

from src.dispatch.adapter import adapt_digital_twin_results
from src.dispatch.baseline import baseline_dispatch_step


def main():
    weather_path = "data/sample/digital_twin_weather_24h.csv"

    # Load the 24-hour weather data.
    weather = load_weather_csv(weather_path)

    # Run the Digital Twin using the project's initial conditions.
    initial_soc_kwh = (
        config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION
    )

    digital_twin_results = run_simulation(
        weather,
        initial_soc_kwh=initial_soc_kwh,
        initial_fuel_litres=config.FUEL_TANK_LITRES,
    )

    # Convert Digital Twin records into Member 4 dispatch format.
    dispatch_inputs = adapt_digital_twin_results(digital_twin_results)

    if not dispatch_inputs:
        print("No Digital Twin records were produced.")
        return

    battery_soc_kwh = initial_soc_kwh
    fuel_remaining_litres = config.FUEL_TANK_LITRES

    baseline_results = []

    for record in dispatch_inputs:
        result = baseline_dispatch_step(
            demand_kw=record["load_total_kw"],
            renewable_kw=record["renewable_available_kw"],
            battery_soc_kwh=battery_soc_kwh,
            fuel_remaining_litres=fuel_remaining_litres,
        )

        battery_soc_kwh = result["battery_soc_kwh"]
        fuel_remaining_litres = result["fuel_remaining_litres"]

        baseline_results.append({
            "timestamp_utc": record["timestamp_utc"],
            "load_total_kw": record["load_total_kw"],
            **result,
        })

    print("\n24-hour baseline dispatch")
    print("=" * 80)

    for result in baseline_results:
        print(
            f"{result['timestamp_utc']} | "
            f"Load={result['load_total_kw']:.1f} kW | "
            f"Renewable={result['renewable_used_kw']:.1f} kW | "
            f"Battery={result['battery_discharge_kw']:.1f} kW | "
            f"G1={result['generator_1_kw']:.1f} kW | "
            f"G2={result['generator_2_kw']:.1f} kW | "
            f"Fuel={result['fuel_used_litres']:.2f} L | "
            f"Unmet={result['unmet_load_kw']:.1f} kW"
        )

    total_fuel = sum(
        result["fuel_used_litres"]
        for result in baseline_results
    )

    max_unmet = max(
        result["unmet_load_kw"]
        for result in baseline_results
    )

    critical_failures = sum(
        1
        for result in baseline_results
        if not result["critical_load_served"]
    )

    print("\nBaseline summary")
    print("=" * 80)
    print(f"Hours simulated       : {len(baseline_results)}")
    print(f"Total fuel used       : {total_fuel:.4f} L")
    print(f"Final fuel remaining  : {fuel_remaining_litres:.4f} L")
    print(f"Final battery SOC     : {battery_soc_kwh:.4f} kWh")
    print(f"Final battery SOC %   : "
          f"{battery_soc_kwh / config.BATTERY_CAPACITY_KWH * 100:.2f}%")
    print(f"Minimum allowed SOC   : "
          f"{config.BATTERY_MIN_SOC_FRACTION * 100:.2f}%")
    print(f"Maximum unmet load    : {max_unmet:.4f} kW")
    print(f"Critical load failures: {critical_failures}")


if __name__ == "__main__":
    main()