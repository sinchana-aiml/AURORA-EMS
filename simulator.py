# simulator.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS Digital Twin — Core Simulation Engine
# Member 1: Digital Twin & Energy Simulation
# NOTE: All values are SIMULATED for prototype/research purposes.
# ─────────────────────────────────────────────────────────────────────────────

import config

# ── 1. LOAD CALCULATIONS ──────────────────────────────────────────────────────

def electrical_load(include_flexible=True):
    """
    Returns station electrical demand in kW.
    - Critical load is always on.
    - Flexible load can be shed during shortfalls.
    """
    load = config.BASE_LOAD_KW
    if include_flexible:
        load += config.FLEXIBLE_LOAD_KW
    return load  # kW


def heating_load(temperature_c):
    """
    Returns heating demand in kW based on outside temperature.
    - At 0°C and above: base heating load only.
    - Below 0°C: extra heating kicks in per degree.
    """
    extra = max(0, -temperature_c) * config.HEATING_TEMP_COEFF
    return config.HEATING_BASE_KW + extra  # kW


def total_load(temperature_c, include_flexible=True):
    """
    Returns total station load in kW.
    = electrical load + heating load
    """
    return electrical_load(include_flexible) + heating_load(temperature_c)  # kW


# ── 2. SOLAR PV GENERATION ───────────────────────────────────────────────────

def solar_pv_output(irradiance_w_m2, temperature_c):
    """
    Returns solar PV power output in kW.

    irradiance_w_m2 : sunlight intensity hitting the panels (W/m²)
    temperature_c   : outside air temperature (°C)

    Formula (transparent prototype):
      irradiance_factor  = how much sun vs the reference 1000 W/m²
      temperature_factor = how much the heat reduces panel output
      output = capacity × irradiance_factor × temperature_factor × performance_ratio
    """
    # Step 1: fraction of reference sunlight (0.0 at night, 1.0 at full sun)
    irradiance_factor = max(0, irradiance_w_m2 / config.SOLAR_REF_IRRADIANCE)

    # Step 2: panels lose efficiency when warmer than 25°C, gain slightly when colder
    temperature_factor = 1 + config.SOLAR_TEMP_COEFF * (temperature_c - config.SOLAR_REF_TEMP_C)

    # Step 3: multiply rated capacity by both factors and the system performance ratio
    output_kw = config.SOLAR_CAPACITY_KW * irradiance_factor * temperature_factor * config.SOLAR_PERFORMANCE_RATIO

    # Step 4: clamp — output cannot be negative or exceed rated capacity
    return max(0.0, min(output_kw, config.SOLAR_CAPACITY_KW))  # kW


# ── 3. WIND TURBINE GENERATION ───────────────────────────────────────────────

def wind_power_output(wind_speed_ms):
    """
    Returns wind turbine power output in kW using a linear power curve.

    wind_speed_ms : wind speed in metres per second (m/s)

    Power curve (4 regions):
      Below cut-in  (< 3.0 m/s)  : turbine is still, output = 0 kW
      Ramp-up zone  (3.0–12.0)   : output rises linearly from 0 → 50 kW
      Rated zone    (12.0–24.9)  : turbine runs at full 50 kW
      Cut-out       (≥ 25.0 m/s) : turbine shuts down for safety, output = 0 kW
    """
    # Region 1: too slow to spin the turbine
    if wind_speed_ms < config.WIND_CUT_IN_MS:
        return 0.0

    # Region 4: too fast — turbine shuts down to avoid damage
    if wind_speed_ms >= config.WIND_CUT_OUT_MS:
        return 0.0

    # Region 2: linearly scale output between cut-in and rated speed
    if wind_speed_ms < config.WIND_RATED_MS:
        fraction = (wind_speed_ms - config.WIND_CUT_IN_MS) / (config.WIND_RATED_MS - config.WIND_CUT_IN_MS)
        return config.WIND_CAPACITY_KW * fraction  # kW

    # Region 3: at or above rated speed — full output
    return config.WIND_CAPACITY_KW  # kW


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    # --- Load calculator test (unchanged) ---
    test_temps = [0, -10, -20, -30]

    print(f"{'Temp (°C)':<12} {'Electrical (kW)':<18} {'Heating (kW)':<15} {'Total (kW)'}")
    print("-" * 58)
    for t in test_temps:
        e = electrical_load()
        h = heating_load(t)
        total = total_load(t)
        print(f"{t:<12} {e:<18} {h:<15.1f} {total:.1f}")

    # --- Solar PV test ---
    print()
    print(f"{'Irradiance':<14} {'Temp (°C)':<12} {'Solar Output (kW)':<20} {'Expected (kW)'}")
    print("-" * 60)
    solar_cases = [
        (0,    25.0, 0.0),    # night — no sun, no output
        (1000, 25.0, 32.8),   # full sun at reference temp
        (500,  25.0, 16.4),   # half sun at reference temp
    ]
    for irr, temp, expected in solar_cases:
        result = solar_pv_output(irr, temp)
        print(f"{irr:<14} {temp:<12} {result:<20.1f} {expected}")

    # --- Wind turbine test ---
    print()
    print(f"{'Wind (m/s)':<14} {'Output (kW)':<15} {'Expected (kW)'}")
    print("-" * 42)
    wind_cases = [
        (0.0,  0.0),   # no wind
        (2.9,  0.0),   # just below cut-in
        (3.0,  0.0),   # exactly at cut-in — ramp starts but fraction = 0
        (7.5,  25.0),  # midpoint of ramp-up zone
        (12.0, 50.0),  # rated speed — full output
        (20.0, 50.0),  # inside rated zone
        (25.0, 0.0),   # exactly at cut-out — shuts down
        (30.0, 0.0),   # above cut-out
    ]
    for speed, expected in wind_cases:
        result = wind_power_output(speed)
        print(f"{speed:<14} {result:<15.1f} {expected}")
