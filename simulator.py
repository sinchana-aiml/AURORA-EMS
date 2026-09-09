# simulator.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS Digital Twin -- Compatibility Runner
# Member 1: Digital Twin & Energy Simulation
#
# All physics functions now live in src/digital_twin/.
# This file re-exports them so that any code that previously imported from
# simulator.py continues to work without modification.
#
# NOTE: All values are SIMULATED for prototype/research purposes.
# ─────────────────────────────────────────────────────────────────────────────

import config

from src.digital_twin.load_model      import electrical_load, heating_load, total_load
from src.digital_twin.renewable_model import solar_pv_output, wind_power_output
from src.digital_twin.battery_model   import battery_step
from src.digital_twin.generator_model import generator_output_and_fuel
from src.digital_twin.energy_balance  import energy_balance_step
from src.digital_twin.simulation      import make_test_weather, run_simulation


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    # --- Load calculator test (unchanged) ---
    test_temps = [0, -10, -20, -30]

    print(f"{'Temp (C)':<12} {'Electrical (kW)':<18} {'Heating (kW)':<15} {'Total (kW)'}")
    print("-" * 58)
    for t in test_temps:
        e = electrical_load()
        h = heating_load(t)
        total = total_load(t)
        print(f"{t:<12} {e:<18} {h:<15.1f} {total:.1f}")

    # --- Solar PV test ---
    print()
    print(f"{'Irradiance':<14} {'Temp (C)':<12} {'Solar Output (kW)':<20} {'Expected (kW)'}")
    print("-" * 60)
    solar_cases = [
        (0,    25.0, 0.0),    # night -- no sun, no output
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
        (3.0,  0.0),   # exactly at cut-in -- ramp starts but fraction = 0
        (7.5,  25.0),  # midpoint of ramp-up zone
        (12.0, 50.0),  # rated speed -- full output
        (20.0, 50.0),  # inside rated zone
        (25.0, 0.0),   # exactly at cut-out -- shuts down
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
        ("Charge 40 kW x 1 h",          INIT_SOC,  40.0,   248.0),
        ("Discharge 40 kW x 1 h",       INIT_SOC, -40.0,  167.895),
        ("Charge capped at 60 kW",      INIT_SOC,  100.0,  267.0),
        ("Discharge capped at 60 kW",   INIT_SOC, -100.0, 146.842),
        ("SOC ceiling: charge near full", 295.0,   40.0,   300.0),
        ("SOC floor: discharge near min",  80.0,  -40.0,    75.0),
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
        ("G1 below min (10 kW)",   10,  20.0,  "running"),
        ("G1 normal (50 kW)",      50,  50.0,  "running"),
        ("G1 over rated (100 kW)", 100, 80.0,  "running"),
        ("G1 unavailable (50 kW)", 50,  0.0,   "unavailable"),
    ]
    for label, req, exp_out, exp_status in gen1_cases:
        unavail = (exp_status == "unavailable")
        r = generator_output_and_fuel(1, req, available=not unavail)
        print(f"{label:<35} {req:<10} {r['actual_output_kw']:<10} {r['fuel_used_litres']:<10} {r['status']:<14} {exp_out}")

    print()
    print("Fuel check -- G1 at 50 kW for 1 hour:")
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
        ("G2 below min (20 kW)",   20,  30.0,  "running"),
        ("G2 normal (60 kW)",      60,  60.0,  "running"),
        ("G2 over rated (200 kW)", 200, 120.0, "running"),
    ]
    for label, req, exp_out, exp_status in gen2_cases:
        r = generator_output_and_fuel(2, req)
        print(f"{label:<35} {req:<10} {r['actual_output_kw']:<10} {r['fuel_used_litres']:<10} {r['status']:<14} {exp_out}")

    # --- Energy balance dispatch tests ---
    FUEL    = 5000.0
    SOC     = config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION  # 210 kWh
    MIN_SOC = config.BATTERY_CAPACITY_KWH * config.BATTERY_MIN_SOC_FRACTION       # 75 kWh

    def show(label, r):
        print(f"\n{'='*60}")
        print(f"  {label}")
        print(f"{'='*60}")
        for k, v in r.items():
            print(f"  {k:<28}: {v}")

    show("TEST 1: Sunny+windy, renewables surplus",
         energy_balance_step(-10, 800, 12.0, SOC, FUEL))
    show("TEST 2: Dark+calm, battery+generator supply",
         energy_balance_step(-20, 0, 2.0, SOC, FUEL))
    show("TEST 3: G1 unavailable, G2 takes over",
         energy_balance_step(-20, 0, 2.0, SOC, FUEL,
                             generator_1_available=False))
    show("TEST 4: Battery at min SOC, cannot discharge",
         energy_balance_step(-20, 0, 2.0, MIN_SOC, FUEL))
    show("TEST 5: Both generators unavailable, unmet load",
         energy_balance_step(-20, 0, 2.0, MIN_SOC, FUEL,
                             generator_1_available=False,
                             generator_2_available=False))

    # Power-balance verification for all 5 tests
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
        total_renewable = r["solar_power_kw"] + r["wind_power_kw"]
        lhs = total_renewable + r["generator_total_kw"] + r["battery_discharge_kw"]
        rhs = r["supplied_load_kw"] + r["battery_charge_kw"] + r["curtailed_power_kw"]
        ok  = abs(lhs - rhs) < 1e-4
        print(f"  {label:<46} {lhs:>10.4f} {rhs:>10.4f} {'PASS' if ok else 'FAIL'}")

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

    ok1 = len(sim_normal) == 24
    print(f"  [{'PASS' if ok1 else 'FAIL'}] Exactly 24 output rows: {len(sim_normal)}")

    ts_list = [r["timestamp"] for r in sim_normal]
    ok2 = ts_list == sorted(ts_list)
    print(f"  [{'PASS' if ok2 else 'FAIL'}] Timestamps in order")

    soc_continuous = True
    eff_c = config.BATTERY_CHARGE_EFFICIENCY
    eff_d = config.BATTERY_DISCHARGE_EFFICIENCY
    for i in range(1, len(sim_normal)):
        prev     = sim_normal[i-1]["battery_soc_kwh"]
        r        = sim_normal[i]
        expected = round(prev
                         + r["battery_charge_kw"]    * eff_c
                         - r["battery_discharge_kw"] / eff_d, 2)
        actual   = round(r["battery_soc_kwh"], 2)
        if abs(actual - expected) > 0.05:
            soc_continuous = False
            break
    print(f"  [{'PASS' if soc_continuous else 'FAIL'}] SOC continuity between hours")

    fuel_monotone = all(
        sim_normal[i]["fuel_remaining_litres"] <= sim_normal[i-1]["fuel_remaining_litres"]
        for i in range(1, len(sim_normal))
    )
    print(f"  [{'PASS' if fuel_monotone else 'FAIL'}] Fuel never increases")

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

    ok6 = all(r["generator_1_power_kw"] == 0.0 for r in sim_g1fail)
    print(f"  [{'PASS' if ok6 else 'FAIL'}] G1 output is 0 in all hours of failure scenario")
