# src/digital_twin/simulation.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Multi-Hour Simulation Loop
# Drives the digital twin over a sequence of weather records, carrying battery
# SOC and fuel state forward between timesteps.
# All values are PROTOTYPE / SIMULATED — not real NCPOR measurements.
# ─────────────────────────────────────────────────────────────────────────────

from .energy_balance import energy_balance_step


def make_test_weather(hours=24):
    """
    Returns a deterministic list of hourly weather dicts for prototype testing.
    NOT real weather data -- values are hand-crafted to exercise all dispatch paths.

    Pattern (repeating every 24 h):
      Hours  0-5  : night, calm       -- no solar, low wind
      Hours  6-11 : morning sun, wind picking up
      Hours 12-17 : peak sun, strong wind
      Hours 18-23 : evening, wind dropping, no solar
    """
    records = []
    for h in range(hours):
        hour_of_day = h % 24
        if hour_of_day < 6:
            irr, wind, temp = 0,   2.0,  -25.0
        elif hour_of_day < 12:
            irr, wind, temp = 400, 8.0,  -20.0
        elif hour_of_day < 18:
            irr, wind, temp = 900, 14.0, -15.0
        else:
            irr, wind, temp = 50,  5.0,  -18.0
        records.append({
            "timestamp":       f"2024-07-01T{hour_of_day:02d}:00",
            "temperature_c":   temp,
            "irradiance_w_m2": irr,
            "wind_speed_ms":   wind,
        })
    return records


def run_simulation(
    weather_records,
    initial_soc_kwh,
    initial_fuel_litres,
    generator_1_available=True,
    generator_2_available=True,
):
    """
    Runs the digital twin for every record in weather_records.

    State carried between hours:
      - battery_soc_kwh       : taken from previous hour's returned battery_soc_kwh
      - fuel_remaining_litres : taken from previous hour's returned fuel_remaining_litres

    Both start at the supplied initial values and are NEVER reset inside the loop.

    Returns a list of result dicts, one per hour, each containing the
    input timestamp plus all fields returned by energy_balance_step.
    """
    soc_kwh = initial_soc_kwh
    fuel_l  = initial_fuel_litres
    results = []

    for rec in weather_records:
        r = energy_balance_step(
            temperature_c         = rec["temperature_c"],
            irradiance_w_m2       = rec["irradiance_w_m2"],
            wind_speed_ms         = rec["wind_speed_ms"],
            battery_soc_kwh       = soc_kwh,
            fuel_remaining_litres = fuel_l,
            generator_1_available = generator_1_available,
            generator_2_available = generator_2_available,
        )
        soc_kwh = r["battery_soc_kwh"]
        fuel_l  = r["fuel_remaining_litres"]
        r["timestamp"] = rec["timestamp"]
        results.append(r)

    return results
