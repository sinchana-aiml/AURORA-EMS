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


# ── 4. BATTERY ENERGY STORAGE ───────────────────────────────────────────────

def battery_step(current_soc_kwh, requested_power_kw, timestep_hours=1.0):
    """
    Simulates one timestep of battery charging or discharging.

    current_soc_kwh    : energy currently stored in the battery (kWh)
    requested_power_kw : positive = charge, negative = discharge, 0 = idle
    timestep_hours     : length of this simulation step in hours

    Returns a dict with:
      new_soc_kwh        : battery energy level after this step (kWh)
      actual_charge_kw   : power actually charged (kW), 0 if discharging
      actual_discharge_kw: power actually discharged (kW), 0 if charging
    """
    # Derived limits from config
    min_soc_kwh = config.BATTERY_CAPACITY_KWH * config.BATTERY_MIN_SOC_FRACTION  # 75 kWh
    max_soc_kwh = config.BATTERY_CAPACITY_KWH                                     # 300 kWh

    actual_charge_kw    = 0.0
    actual_discharge_kw = 0.0
    new_soc_kwh         = current_soc_kwh

    if requested_power_kw > 0:
        # ── CHARGING ───────────────────────────────────────────────────────────
        # Step 1: cap charging power at the hardware limit
        charge_kw = min(requested_power_kw, config.BATTERY_MAX_CHARGE_KW)

        # Step 2: energy that would enter the battery after efficiency loss
        energy_in_kwh = charge_kw * timestep_hours * config.BATTERY_CHARGE_EFFICIENCY

        # Step 3: don't overfill — only charge as much as the battery can hold
        energy_in_kwh = min(energy_in_kwh, max_soc_kwh - current_soc_kwh)

        # Step 4: back-calculate the actual grid power drawn for charging
        actual_charge_kw = energy_in_kwh / (timestep_hours * config.BATTERY_CHARGE_EFFICIENCY)
        new_soc_kwh      = current_soc_kwh + energy_in_kwh

    elif requested_power_kw < 0:
        # ── DISCHARGING ─────────────────────────────────────────────────────────
        # Step 1: cap discharge power at the hardware limit (work with positive numbers)
        discharge_kw = min(-requested_power_kw, config.BATTERY_MAX_DISCHARGE_KW)

        # Step 2: energy that would leave the battery (efficiency means more leaves than delivered)
        energy_out_kwh = discharge_kw * timestep_hours / config.BATTERY_DISCHARGE_EFFICIENCY

        # Step 3: don't over-drain — only discharge down to the minimum reserve
        energy_out_kwh = min(energy_out_kwh, current_soc_kwh - min_soc_kwh)

        # Step 4: back-calculate the actual power delivered to the grid
        actual_discharge_kw = energy_out_kwh * config.BATTERY_DISCHARGE_EFFICIENCY / timestep_hours
        new_soc_kwh         = current_soc_kwh - energy_out_kwh

    return {
        "new_soc_kwh":         round(new_soc_kwh, 4),
        "actual_charge_kw":    round(actual_charge_kw, 4),
        "actual_discharge_kw": round(actual_discharge_kw, 4),
    }


# ── 5. DIESEL GENERATOR MODEL ───────────────────────────────────────────────

# Map generator_id → its config constants (avoids long if/else chains later)
_GEN_PARAMS = {
    1: {
        "rated_kw":      config.GENERATOR_1_RATED_KW,
        "minimum_kw":    config.GENERATOR_1_MINIMUM_KW,
        "idle_fuel_lph": config.GENERATOR_1_IDLE_FUEL_LPH,
        "fuel_per_kwh":  config.GENERATOR_1_FUEL_PER_KWH,
    },
    2: {
        "rated_kw":      config.GENERATOR_2_RATED_KW,
        "minimum_kw":    config.GENERATOR_2_MINIMUM_KW,
        "idle_fuel_lph": config.GENERATOR_2_IDLE_FUEL_LPH,
        "fuel_per_kwh":  config.GENERATOR_2_FUEL_PER_KWH,
    },
}


def generator_output_and_fuel(generator_id, requested_power_kw,
                              available=True, timestep_hours=1.0):
    """
    Simulates one timestep of a diesel generator.

    generator_id       : 1 or 2
    requested_power_kw : how much power the station needs from this generator
    available          : False if the generator has failed or is offline
    timestep_hours     : length of this simulation step in hours

    Returns a dict with:
      actual_output_kw  : power actually produced (kW)
      fuel_used_litres  : diesel consumed this timestep (litres)
      status            : human-readable string describing generator state
    """
    p = _GEN_PARAMS[generator_id]

    # Rule 1: generator is broken or switched off — produces nothing
    if not available:
        return {"actual_output_kw": 0.0, "fuel_used_litres": 0.0, "status": "unavailable"}

    # Rule 2: no power requested — generator stays off
    if requested_power_kw <= 0:
        return {"actual_output_kw": 0.0, "fuel_used_litres": 0.0, "status": "off"}

    # Rule 3: cap output at rated capacity
    actual_output_kw = min(requested_power_kw, p["rated_kw"])

    # Rule 4: diesel engines cannot run efficiently below a minimum load
    #          if asked for less than minimum, run at minimum anyway
    if actual_output_kw < p["minimum_kw"]:
        actual_output_kw = p["minimum_kw"]

    # Rule 5: fuel = idle burn (just to keep engine running) + load-dependent burn
    fuel_used_litres = (p["idle_fuel_lph"] * timestep_hours
                        + p["fuel_per_kwh"] * actual_output_kw * timestep_hours)

    return {
        "actual_output_kw": round(actual_output_kw, 4),
        "fuel_used_litres": round(fuel_used_litres, 4),
        "status":           "running",
    }


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

    # --- Battery test ---
    INIT_SOC = config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION  # 210 kWh
    print()
    print(f"Battery capacity: {config.BATTERY_CAPACITY_KWH} kWh  |  "
          f"Min SOC: {config.BATTERY_CAPACITY_KWH * config.BATTERY_MIN_SOC_FRACTION} kWh  |  "
          f"Initial SOC: {INIT_SOC} kWh")
    print()
    print(f"{'Test':<35} {'SOC before':<12} {'Request(kW)':<14} {'New SOC':<12} {'Chg kW':<10} {'Dis kW':<10} {'Expected SOC'}")
    print("-" * 100)

    battery_cases = [
        ("No action",                   INIT_SOC,  0.0,    210.0),
        ("Charge 40 kW x 1 h",          INIT_SOC,  40.0,   248.0),   # 210 + 40*0.95 = 248
        ("Discharge 40 kW x 1 h",       INIT_SOC, -40.0,  167.895), # 210 - 40/0.95 = 167.895
        ("Charge capped at 60 kW",      INIT_SOC,  100.0,  267.0),   # 210 + 60*0.95 = 267
        ("Discharge capped at 60 kW",   INIT_SOC, -100.0, 146.842), # 210 - 60/0.95 = 146.842
        ("SOC ceiling: charge near full", 295.0,   40.0,   300.0),   # cannot exceed 300
        ("SOC floor: discharge near min",  80.0,  -40.0,    75.0),   # cannot go below 75
    ]

    for label, soc_before, req, expected_soc in battery_cases:
        result = battery_step(soc_before, req)
        print(f"{label:<35} {soc_before:<12} {req:<14} "
              f"{result['new_soc_kwh']:<12} {result['actual_charge_kw']:<10} "
              f"{result['actual_discharge_kw']:<10} {expected_soc}")

    # --- Generator test ---
    print()
    print("Generator 1  (rated=80 kW, min=20 kW, idle=3 L/h, 0.25 L/kWh)")
    print(f"{'Test':<35} {'Req(kW)':<10} {'Out(kW)':<10} {'Fuel(L)':<10} {'Status':<14} {'Expected Out'}")
    print("-" * 85)
    gen1_cases = [
        ("G1 off (0 kW)",          0,   0.0,   "off"),
        ("G1 below min (10 kW)",   10,  20.0,  "running"),  # bumped to minimum
        ("G1 normal (50 kW)",      50,  50.0,  "running"),
        ("G1 over rated (100 kW)", 100, 80.0,  "running"),  # capped at rated
        ("G1 unavailable (50 kW)", 50,  0.0,   "unavailable"),
    ]
    for label, req, exp_out, exp_status in gen1_cases:
        unavail = (exp_status == "unavailable")
        r = generator_output_and_fuel(1, req, available=not unavail)
        print(f"{label:<35} {req:<10} {r['actual_output_kw']:<10} {r['fuel_used_litres']:<10} {r['status']:<14} {exp_out}")

    # Fuel calculation walkthrough for G1 at 50 kW
    print()
    print("Fuel check — G1 at 50 kW for 1 hour:")
    print("  idle_fuel  = 3.0 L/h x 1 h          =  3.00 L")
    print("  load_fuel  = 0.25 L/kWh x 50 kW x 1h = 12.50 L")
    print("  total_fuel = 3.00 + 12.50             = 15.50 L")
    r_check = generator_output_and_fuel(1, 50)
    print(f"  Actual result from function           = {r_check['fuel_used_litres']} L")

    print()
    print("Generator 2  (rated=120 kW, min=30 kW, idle=4 L/h, 0.23 L/kWh)")
    print(f"{'Test':<35} {'Req(kW)':<10} {'Out(kW)':<10} {'Fuel(L)':<10} {'Status':<14} {'Expected Out'}")
    print("-" * 85)
    gen2_cases = [
        ("G2 below min (20 kW)",   20,  30.0,  "running"),  # bumped to minimum
        ("G2 normal (60 kW)",      60,  60.0,  "running"),
        ("G2 over rated (200 kW)", 200, 120.0, "running"),  # capped at rated
    ]
    for label, req, exp_out, exp_status in gen2_cases:
        r = generator_output_and_fuel(2, req)
        print(f"{label:<35} {req:<10} {r['actual_output_kw']:<10} {r['fuel_used_litres']:<10} {r['status']:<14} {exp_out}")
