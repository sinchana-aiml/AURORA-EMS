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
