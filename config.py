# config.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS Station Configuration
# All physical constants and rated parameters for the virtual polar station.
# Every other module imports from here — no magic numbers elsewhere.
# ─────────────────────────────────────────────────────────────────────────────

# ── Simulation time ───────────────────────────────────────────────────────────
TIMESTEP_HOURS = 1          # Each simulation step represents 1 hour

# ── Solar PV array ────────────────────────────────────────────────────────────
SOLAR_CAPACITY_KW   = 30.0  # Rated peak output (kW)
SOLAR_EFFICIENCY    = 0.18  # Panel efficiency (18 %)
SOLAR_TEMP_COEFF    = -0.004 # Power loss per °C above 25 °C (fraction/°C)

# ── Wind turbine ──────────────────────────────────────────────────────────────
WIND_CAPACITY_KW    = 50.0  # Rated output at rated wind speed (kW)
WIND_CUT_IN_MS      = 3.0   # Minimum wind speed to generate (m/s)
WIND_RATED_MS       = 12.0  # Wind speed at rated output (m/s)
WIND_CUT_OUT_MS     = 25.0  # Wind speed above which turbine shuts down (m/s)

# ── Diesel generators (two identical units) ───────────────────────────────────
NUM_GENERATORS      = 2
GEN_RATED_KW        = 60.0  # Rated output per generator (kW)
GEN_MIN_LOAD_FRAC   = 0.30  # Minimum load fraction (30 % of rated)
GEN_FUEL_RATE_L_KWH = 0.28  # Fuel consumption (litres per kWh generated)
FUEL_TANK_LITRES    = 5000.0 # Total diesel fuel available (litres)

# ── Battery storage ───────────────────────────────────────────────────────────
BATTERY_CAPACITY_KWH  = 200.0  # Usable energy capacity (kWh)
BATTERY_MAX_SOC       = 1.00   # Maximum state of charge (100 %)
BATTERY_MIN_SOC       = 0.20   # Minimum reserve — never discharge below this
BATTERY_CHARGE_EFF    = 0.95   # Charging efficiency (95 %)
BATTERY_DISCHARGE_EFF = 0.95   # Discharging efficiency (95 %)
BATTERY_MAX_RATE_KW   = 50.0   # Maximum charge/discharge power (kW)
BATTERY_INITIAL_SOC   = 0.80   # Starting SOC for simulation (80 %)

# ── Station electrical loads ──────────────────────────────────────────────────
BASE_LOAD_KW          = 20.0   # Always-on critical systems (kW)
HEATING_BASE_KW       = 15.0   # Heating load at 0 °C reference (kW)
HEATING_TEMP_COEFF    = 0.8    # Extra kW of heating per °C below 0 °C
FLEXIBLE_LOAD_KW      = 10.0   # Deferrable loads (labs, non-critical equipment)

# ── Critical vs flexible load split ──────────────────────────────────────────
# Critical loads must always be served if any generation is available.
# Flexible loads can be shed during shortfalls.
CRITICAL_LOAD_KW      = BASE_LOAD_KW  # kW that must never be cut

# ── Scenario thresholds ───────────────────────────────────────────────────────
STORM_WIND_THRESHOLD_MS   = 20.0  # Wind speed that triggers storm scenario (m/s)
LOW_FUEL_THRESHOLD_L      = 500.0 # Fuel level that triggers low-fuel alert (L)
COMMS_OUTAGE_PROBABILITY  = 0.02  # 2 % chance per hour of comms outage
