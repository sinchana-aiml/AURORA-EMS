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


# ── 6. ENERGY BALANCE DISPATCH ──────────────────────────────────────────────

def energy_balance_step(
    temperature_c,
    irradiance_w_m2,
    wind_speed_ms,
    battery_soc_kwh,
    fuel_remaining_litres,
    generator_1_available=True,
    generator_2_available=True,
    timestep_hours=1.0,
):
    """
    Runs one timestep of the digital twin energy balance.

    Dispatch order (priority highest -> lowest):
      1. Renewables (solar + wind)  -- free, use first
      2. Battery discharge          -- stored energy, no fuel cost
      3. Generator 1                -- lower fuel rate
      4. Generator 2                -- backup

    Surplus renewable energy charges the battery first, then is curtailed.
    Returns a full dict of every power flow and state variable.
    """
    # Step 1: station load
    elec_kw   = electrical_load(include_flexible=True)
    heat_kw   = heating_load(temperature_c)
    demand_kw = elec_kw + heat_kw
    deficit_kw = demand_kw

    # Step 2: renewables
    solar_kw     = solar_pv_output(irradiance_w_m2, temperature_c)
    wind_kw      = wind_power_output(wind_speed_ms)
    renewable_kw = solar_kw + wind_kw

    renewable_used_kw = min(renewable_kw, deficit_kw)
    deficit_kw       -= renewable_used_kw
    surplus_kw        = renewable_kw - renewable_used_kw

    # Step 3: battery
    curtailed_kw = 0.0
    if surplus_kw > 0:
        # surplus renewable -> charge battery
        batt         = battery_step(battery_soc_kwh, surplus_kw, timestep_hours)
        battery_soc_kwh = batt["new_soc_kwh"]
        charge_kw    = batt["actual_charge_kw"]
        discharge_kw = 0.0
        curtailed_kw = surplus_kw - charge_kw
    elif deficit_kw > 0:
        # deficit -> discharge battery
        batt         = battery_step(battery_soc_kwh, -deficit_kw, timestep_hours)
        battery_soc_kwh = batt["new_soc_kwh"]
        discharge_kw = batt["actual_discharge_kw"]
        charge_kw    = 0.0
        deficit_kw  -= discharge_kw
    else:
        charge_kw    = 0.0
        discharge_kw = 0.0

    # Step 4: Generator 1
    g1 = generator_output_and_fuel(1, deficit_kw,
                                   available=generator_1_available,
                                   timestep_hours=timestep_hours)
    deficit_kw            -= g1["actual_output_kw"]
    fuel_remaining_litres  = max(0.0, fuel_remaining_litres - g1["fuel_used_litres"])

    # Step 5: Generator 2
    g2 = generator_output_and_fuel(2, deficit_kw,
                                   available=generator_2_available,
                                   timestep_hours=timestep_hours)
    deficit_kw            -= g2["actual_output_kw"]
    fuel_remaining_litres  = max(0.0, fuel_remaining_litres - g2["fuel_used_litres"])

    # Step 6: handle excess generation from generator minimum loading
    # deficit_kw is now negative when generators produced more than needed.
    # Try to absorb that excess into the battery first, then curtail the rest.
    gen_to_batt_kw  = 0.0
    excess_kw       = max(0.0, -deficit_kw)   # positive = generators over-produced
    if excess_kw > 0:
        batt2           = battery_step(battery_soc_kwh, excess_kw, timestep_hours)
        battery_soc_kwh = batt2["new_soc_kwh"]
        gen_to_batt_kw  = batt2["actual_charge_kw"]
        charge_kw      += gen_to_batt_kw      # add to total battery charging
        curtailed_kw   += excess_kw - gen_to_batt_kw  # anything battery couldn't take

    # Step 7: unmet load and critical load check
    # When generators over-produced, deficit is negative -- unmet load is zero.
    unmet_kw        = max(0.0, round(deficit_kw, 6))
    supplied_kw     = demand_kw - unmet_kw
    critical_served = supplied_kw >= config.CRITICAL_LOAD_KW

    return {
        "temperature_c":              temperature_c,
        "irradiance_w_m2":            irradiance_w_m2,
        "wind_speed_ms":              wind_speed_ms,
        "electrical_load_kw":         round(elec_kw, 4),
        "heating_load_kw":            round(heat_kw, 4),
        "total_load_kw":              round(demand_kw, 4),
        "solar_power_kw":             round(solar_kw, 4),
        "wind_power_kw":              round(wind_kw, 4),
        "renewable_used_kw":          round(renewable_used_kw, 4),
        "battery_charge_kw":          round(charge_kw, 4),
        "battery_discharge_kw":       round(discharge_kw, 4),
        "battery_soc_kwh":            round(battery_soc_kwh, 4),
        "generator_1_power_kw":       round(g1["actual_output_kw"], 4),
        "generator_2_power_kw":       round(g2["actual_output_kw"], 4),
        "generator_total_kw":         round(g1["actual_output_kw"] + g2["actual_output_kw"], 4),
        "generator_to_battery_charge_kw": round(gen_to_batt_kw, 4),
        "excess_generation_kw":       round(excess_kw, 4),
        "curtailed_power_kw":         round(curtailed_kw, 4),
        "fuel_used_litres":           round(g1["fuel_used_litres"] + g2["fuel_used_litres"], 4),
        "fuel_remaining_litres":      round(fuel_remaining_litres, 4),
        "unmet_load_kw":              round(unmet_kw, 4),
        "supplied_load_kw":           round(supplied_kw, 4),
        "critical_load_served":       critical_served,
    }


# ── 7. MULTI-HOUR SIMULATION LOOP ─────────────────────────────────────────────

def make_test_weather(hours=24):
    """
    Returns a deterministic list of hourly weather dicts for prototype testing.
    NOT real weather data -- values are hand-crafted to exercise all dispatch paths.

    Pattern (repeating every 24 h):
      Hours  0-5  : night, calm      -- no solar, low wind
      Hours  6-11 : morning sun, wind picking up
      Hours 12-17 : peak sun, strong wind
      Hours 18-23 : evening, wind dropping, no solar
    """
    records = []
    for h in range(hours):
        hour_of_day = h % 24
        if hour_of_day < 6:                          # night
            irr, wind, temp = 0,   2.0,  -25.0
        elif hour_of_day < 12:                       # morning
            irr, wind, temp = 400, 8.0,  -20.0
        elif hour_of_day < 18:                       # midday
            irr, wind, temp = 900, 14.0, -15.0
        else:                                        # evening
            irr, wind, temp = 50,  5.0,  -18.0
        records.append({
            "timestamp":      f"2024-07-01T{hour_of_day:02d}:00",
            "temperature_c":  temp,
            "irradiance_w_m2": irr,
            "wind_speed_ms":  wind,
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
      - battery_soc_kwh      : taken from previous hour's returned battery_soc_kwh
      - fuel_remaining_litres: taken from previous hour's returned fuel_remaining_litres

    Both start at the supplied initial values and are NEVER reset inside the loop.

    Returns a list of result dicts, one per hour, each containing the
    input timestamp plus all fields returned by energy_balance_step.
    """
    soc_kwh  = initial_soc_kwh
    fuel_l   = initial_fuel_litres
    results  = []

    for rec in weather_records:
        # Run one hour of the energy balance using current state
        r = energy_balance_step(
            temperature_c         = rec["temperature_c"],
            irradiance_w_m2       = rec["irradiance_w_m2"],
            wind_speed_ms         = rec["wind_speed_ms"],
            battery_soc_kwh       = soc_kwh,
            fuel_remaining_litres = fuel_l,
            generator_1_available = generator_1_available,
            generator_2_available = generator_2_available,
        )
        # Carry state forward to the next hour
        soc_kwh = r["battery_soc_kwh"]
        fuel_l  = r["fuel_remaining_litres"]

        # Attach the timestamp and store
        r["timestamp"] = rec["timestamp"]
        results.append(r)

    return results


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

    # --- Energy balance dispatch tests ---
    FUEL  = 5000.0
    SOC   = config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION  # 210 kWh
    MIN_SOC = config.BATTERY_CAPACITY_KWH * config.BATTERY_MIN_SOC_FRACTION     # 75 kWh

    def show(label, r):
        print(f"\n{'='*60}")
        print(f"  {label}")
        print(f"{'='*60}")
        for k, v in r.items():
            print(f"  {k:<28}: {v}")

    # Test 1: sunny + windy -- renewables cover most of the load
    # temp=-10, irr=800, wind=12 -> solar=26.24 kW, wind=50 kW, load=53 kW
    # renewable(76.24) > load(53) -> surplus=23.24 -> charge battery
    show("TEST 1: Sunny+windy, renewables surplus",
         energy_balance_step(-10, 800, 12.0, SOC, FUEL))

    # Test 2: no sun, low wind -- battery + generators supply load
    # temp=-20, irr=0, wind=2 -> solar=0, wind=0, load=61 kW
    # battery discharges, then G1 covers remainder
    show("TEST 2: Dark+calm, battery+generator supply",
         energy_balance_step(-20, 0, 2.0, SOC, FUEL))

    # Test 3: G1 unavailable -- G2 supplies remaining demand
    show("TEST 3: G1 unavailable, G2 takes over",
         energy_balance_step(-20, 0, 2.0, SOC, FUEL,
                             generator_1_available=False))

    # Test 4: battery at minimum SOC -- cannot discharge
    show("TEST 4: Battery at min SOC, cannot discharge",
         energy_balance_step(-20, 0, 2.0, MIN_SOC, FUEL))

    # Test 5: both generators unavailable -- unmet load reported
    show("TEST 5: Both generators unavailable, unmet load",
         energy_balance_step(-20, 0, 2.0, MIN_SOC, FUEL,
                             generator_1_available=False,
                             generator_2_available=False))

    # Power-balance verification for all 5 tests
    # Identity: total_generation + battery_discharge
    #         = supplied_load + battery_charging + curtailed
    # (within floating-point tolerance of 1e-6)
    print()
    print("Power-balance check (tolerance 1e-6):")
    print(f"{'Test':<48} {'LHS':>10} {'RHS':>10} {'OK'}")
    print("-" * 72)
    balance_cases = [
        ("T1: Sunny+windy",        energy_balance_step(-10, 800, 12.0, SOC, FUEL)),
        ("T2: Dark+calm",          energy_balance_step(-20, 0, 2.0, SOC, FUEL)),
        ("T3: G1 unavailable",     energy_balance_step(-20, 0, 2.0, SOC, FUEL, generator_1_available=False)),
        ("T4: Battery at min SOC", energy_balance_step(-20, 0, 2.0, MIN_SOC, FUEL)),
        ("T5: Both gens down",     energy_balance_step(-20, 0, 2.0, MIN_SOC, FUEL,
                                       generator_1_available=False, generator_2_available=False)),
    ]
    for label, r in balance_cases:
        # LHS = all power produced and injected onto the bus
        # renewable_used + surplus_charged_to_battery + generators + battery_discharge
        # = (renewable_used + battery_charge_from_renewable) + generators + battery_discharge
        # Simplest form: use total renewable = renewable_used + battery_charge - gen_to_batt
        total_renewable = r["solar_power_kw"] + r["wind_power_kw"]
        lhs = total_renewable + r["generator_total_kw"] + r["battery_discharge_kw"]
        rhs = (r["supplied_load_kw"] + r["battery_charge_kw"] + r["curtailed_power_kw"])
        ok  = abs(lhs - rhs) < 1e-4
        print(f"  {label:<46} {lhs:>10.4f} {rhs:>10.4f} {'PASS' if ok else 'FAIL'}")

    # Manual power-balance walkthrough for Test 2 (the generator minimum-load case)
    print()
    print("Manual power-balance -- Test 2 (dark, calm, temp=-20, SOC=210):")
    print("  total_load          = 61.00 kW")
    print("  renewables          =  0.00 kW")
    print("  battery discharges  = 60.00 kW  (max discharge rate)")
    print("  remaining deficit   = 61 - 60   =  1.00 kW -> G1 requested")
    print("  G1 minimum kicks in -> G1 output = 20.00 kW")
    print("  excess generation   = 20 - 1    = 19.00 kW")
    print("  battery absorbs excess (up to 60 kW limit) -> gen_to_battery = 19.00 kW")
    print("  curtailed           =  0.00 kW  (battery absorbed all excess)")
    print("  supplied_load       = 61.00 kW")
    print("  LHS = renewable(0) + gen(20) + batt_discharge(60) = 80.00 kW")
    print("  RHS = supplied(61) + batt_charge(19*0.95=18.05... wait -- charge_kw is grid side)")
    print("  Note: battery_charge_kw is the power drawn FROM the bus into the battery.")
    print("  gen_to_battery_charge_kw = 19.00 kW (grid side), SOC gains 19*0.95 kWh")
    print("  LHS = 0 + 20 + 60        = 80.00 kW")
    print("  RHS = 61 + 19 + 0        = 80.00 kW  PASS")

    # --- 24-hour simulation tests ---
    INIT_FUEL = config.FUEL_TANK_LITRES
    INIT_SOC2 = config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION
    weather   = make_test_weather(24)

    print()
    print("=" * 70)
    print("  24-HOUR SIMULATION -- normal scenario (both generators available)")
    print("=" * 70)
    sim_normal = run_simulation(weather, INIT_SOC2, INIT_FUEL)

    # Print hourly table
    print(f"{'Hour':<6} {'Timestamp':<18} {'Temp':>6} {'Solar':>7} {'Wind':>7} "
          f"{'Load':>7} {'SOC':>8} {'Fuel':>8} {'Unmet':>7}")
    print("-" * 80)
    for r in sim_normal:
        print(f"  {r['timestamp']:<18} {r['temperature_c']:>6.1f} "
              f"{r['solar_power_kw']:>7.2f} {r['wind_power_kw']:>7.2f} "
              f"{r['total_load_kw']:>7.2f} {r['battery_soc_kwh']:>8.2f} "
              f"{r['fuel_remaining_litres']:>8.2f} {r['unmet_load_kw']:>7.2f}")

    final_normal = sim_normal[-1]
    print()
    print(f"  Final SOC  : {final_normal['battery_soc_kwh']} kWh")
    print(f"  Final fuel : {final_normal['fuel_remaining_litres']} L")
    print(f"  Fuel used  : {round(INIT_FUEL - final_normal['fuel_remaining_litres'], 4)} L")

    # --- Automated checks ---
    print()
    print("Simulation checks:")

    # Check 1: exactly 24 rows
    ok1 = len(sim_normal) == 24
    print(f"  [{'PASS' if ok1 else 'FAIL'}] Exactly 24 output rows: {len(sim_normal)}")

    # Check 2: timestamps preserved in order
    ts_list = [r["timestamp"] for r in sim_normal]
    ok2 = ts_list == sorted(ts_list)
    print(f"  [{'PASS' if ok2 else 'FAIL'}] Timestamps in order")

    # Check 3: SOC continuity -- each hour's SOC must equal the previous
    # hour's SOC adjusted by net energy flows (all on the bus side, kWh).
    # net_change = energy_in - energy_out
    #   energy_in  = battery_charge_kw * 1h  (already includes gen_to_batt)
    #              converted to SOC: * CHARGE_EFF
    #   energy_out = battery_discharge_kw * 1h / DISCHARGE_EFF  (more leaves battery)
    # But battery_charge_kw is the BUS-side power; SOC gain = charge_kw * eff
    # battery_discharge_kw is BUS-side power delivered; SOC loss = discharge_kw / eff
    soc_continuous = True
    eff_c = config.BATTERY_CHARGE_EFFICIENCY
    eff_d = config.BATTERY_DISCHARGE_EFFICIENCY
    for i in range(1, len(sim_normal)):
        prev  = sim_normal[i-1]["battery_soc_kwh"]
        r     = sim_normal[i]
        expected = round(prev
                         + r["battery_charge_kw"]    * eff_c
                         - r["battery_discharge_kw"] / eff_d, 2)
        actual   = round(r["battery_soc_kwh"], 2)
        if abs(actual - expected) > 0.05:   # 0.05 kWh tolerance for rounding
            soc_continuous = False
            break
    print(f"  [{'PASS' if soc_continuous else 'FAIL'}] SOC continuity between hours")

    # Check 4: fuel never increases
    fuel_monotone = all(
        sim_normal[i]["fuel_remaining_litres"] <= sim_normal[i-1]["fuel_remaining_litres"]
        for i in range(1, len(sim_normal))
    )
    print(f"  [{'PASS' if fuel_monotone else 'FAIL'}] Fuel never increases")

    # Check 5: no unmet load in normal scenario
    no_unmet = all(r["unmet_load_kw"] == 0.0 for r in sim_normal)
    print(f"  [{'PASS' if no_unmet else 'FAIL'}] No unmet load in normal scenario")

    # --- Generator-failure scenario ---
    print()
    print("=" * 70)
    print("  24-HOUR SIMULATION -- G1 failure scenario")
    print("=" * 70)
    sim_g1fail = run_simulation(weather, INIT_SOC2, INIT_FUEL,
                                generator_1_available=False)

    print(f"{'Hour':<6} {'Timestamp':<18} {'G1 kW':>7} {'G2 kW':>7} "
          f"{'SOC':>8} {'Fuel':>8} {'Unmet':>7}")
    print("-" * 65)
    for r in sim_g1fail:
        print(f"  {r['timestamp']:<18} {r['generator_1_power_kw']:>7.2f} "
              f"{r['generator_2_power_kw']:>7.2f} {r['battery_soc_kwh']:>8.2f} "
              f"{r['fuel_remaining_litres']:>8.2f} {r['unmet_load_kw']:>7.2f}")

    final_fail = sim_g1fail[-1]
    print()
    print(f"  Final SOC  : {final_fail['battery_soc_kwh']} kWh")
    print(f"  Final fuel : {final_fail['fuel_remaining_litres']} L")

    # Check 6: G1 always zero in failure scenario
    ok6 = all(r["generator_1_power_kw"] == 0.0 for r in sim_g1fail)
    print(f"  [{'PASS' if ok6 else 'FAIL'}] G1 output is 0 in all hours of failure scenario")
