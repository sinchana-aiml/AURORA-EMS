# AURORA-EMS
# Member 4 — Baseline vs Optimized Dispatch Comparison
#
# Runs both dispatch strategies on the same 24-hour Digital Twin data.
# All values are simulated for prototype/research purposes.

import config

from src.digital_twin.simulation import run_simulation
from src.digital_twin.weather_loader import load_weather_csv

from src.dispatch.adapter import adapt_digital_twin_results
from src.dispatch.baseline import baseline_dispatch_step
from src.dispatch.optimizer import (
    optimized_dispatch,
    optimized_dispatch_lookahead,
)
from src.dispatch.fuel_metrics import (
    calculate_average_daily_fuel,
    calculate_fuel_crisis_days,
    calculate_fuel_saved,
)


def run_dispatch_comparison():
    weather_path = "data/sample/digital_twin_weather_24h.csv"

    weather = load_weather_csv(weather_path)

    initial_soc_kwh = (
        config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION
    )

    digital_twin_results = run_simulation(
        weather,
        initial_soc_kwh=initial_soc_kwh,
        initial_fuel_litres=config.FUEL_TANK_LITRES,
    )

    dispatch_inputs = adapt_digital_twin_results(
        digital_twin_results
    )

    if not dispatch_inputs:
        raise RuntimeError(
            "No Digital Twin records were produced."
        )

    baseline_soc_kwh = initial_soc_kwh
    baseline_fuel_litres = config.FUEL_TANK_LITRES

    baseline_results = []

    for record in dispatch_inputs:
        baseline = baseline_dispatch_step(
            demand_kw=record["load_total_kw"],
            renewable_kw=record["renewable_available_kw"],
            battery_soc_kwh=baseline_soc_kwh,
            fuel_remaining_litres=baseline_fuel_litres,
        )
        baseline_soc_kwh = baseline["battery_soc_kwh"]
        baseline_fuel_litres = baseline["fuel_remaining_litres"]
        baseline_results.append({
            "timestamp_utc": record["timestamp_utc"],
            "load_total_kw": record["load_total_kw"],
            "renewable_available_kw": record["renewable_available_kw"],
            **baseline,
        })

    # 24-hour look-ahead optimizer (minimises total fuel)
    opt_hourly = optimized_dispatch_lookahead(
        records=dispatch_inputs,
        initial_soc_kwh=initial_soc_kwh,
        initial_fuel_litres=config.FUEL_TANK_LITRES,
    )
    optimized_results = [
        {
            "timestamp_utc": dispatch_inputs[i]["timestamp_utc"],
            "load_total_kw": dispatch_inputs[i]["load_total_kw"],
            "renewable_available_kw": dispatch_inputs[i]["renewable_available_kw"],
            **opt_hourly[i],
        }
        for i in range(len(dispatch_inputs))
    ]
    optimized_soc_kwh = optimized_results[-1]["battery_soc_kwh"]
    optimized_fuel_litres = optimized_results[-1]["fuel_remaining_litres"]

    baseline_fuel_used = (
        config.FUEL_TANK_LITRES
        - baseline_fuel_litres
    )

    optimized_fuel_used = (
        config.FUEL_TANK_LITRES
        - optimized_fuel_litres
    )

    fuel_comparison = calculate_fuel_saved(
        baseline_fuel_used,
        optimized_fuel_used,
    )

    hours_simulated = len(dispatch_inputs)

    baseline_daily_fuel = calculate_average_daily_fuel(
        baseline_fuel_used,
        hours_simulated,
    )

    optimized_daily_fuel = calculate_average_daily_fuel(
        optimized_fuel_used,
        hours_simulated,
    )

    baseline_crisis_days = calculate_fuel_crisis_days(
        baseline_fuel_litres,
        baseline_daily_fuel,
    )

    optimized_crisis_days = calculate_fuel_crisis_days(
        optimized_fuel_litres,
        optimized_daily_fuel,
    )

    return {
        "baseline_results": baseline_results,
        "optimized_results": optimized_results,
        "baseline_fuel_used_litres": baseline_fuel_used,
        "optimized_fuel_used_litres": optimized_fuel_used,
        "baseline_fuel_remaining_litres": baseline_fuel_litres,
        "optimized_fuel_remaining_litres": optimized_fuel_litres,
        "baseline_final_soc_kwh": baseline_soc_kwh,
        "optimized_final_soc_kwh": optimized_soc_kwh,
        "fuel_saved_liters": fuel_comparison[
            "fuel_saved_liters"
        ],
        "fuel_saved_pct": fuel_comparison[
            "fuel_saved_pct"
        ],
        "baseline_fuel_crisis_days": baseline_crisis_days,
        "optimized_fuel_crisis_days": optimized_crisis_days,
    }


def main():
    comparison = run_dispatch_comparison()

    print()
    print("24-hour baseline vs optimized dispatch")
    print("=" * 80)

    print(
        f"Baseline fuel used       : "
        f"{comparison['baseline_fuel_used_litres']:.4f} L"
    )

    print(
        f"Optimized fuel used      : "
        f"{comparison['optimized_fuel_used_litres']:.4f} L"
    )

    print(
        f"Fuel saved               : "
        f"{comparison['fuel_saved_liters']:.4f} L"
    )

    print(
        f"Fuel saved percentage    : "
        f"{comparison['fuel_saved_pct']:.2f}%"
    )

    print()

    print(
        f"Baseline fuel remaining  : "
        f"{comparison['baseline_fuel_remaining_litres']:.4f} L"
    )

    print(
        f"Optimized fuel remaining : "
        f"{comparison['optimized_fuel_remaining_litres']:.4f} L"
    )

    print()

    print(
        f"Baseline final SOC       : "
        f"{comparison['baseline_final_soc_kwh']:.4f} kWh"
    )

    print(
        f"Optimized final SOC      : "
        f"{comparison['optimized_final_soc_kwh']:.4f} kWh"
    )

    print()

    print(
        f"Baseline fuel duration   : "
        f"{comparison['baseline_fuel_crisis_days']:.2f} days"
    )

    print(
        f"Optimized fuel duration  : "
        f"{comparison['optimized_fuel_crisis_days']:.2f} days"
    )


if __name__ == "__main__":
    main()