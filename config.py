# config.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS Station Configuration
# All physical constants and rated parameters for the virtual polar station.
# Every other module imports from here — no magic numbers elsewhere.
# ─────────────────────────────────────────────────────────────────────────────

# ── Simulation time ───────────────────────────────────────────────────────────
TIMESTEP_HOURS             = 1    # Each simulation step represents 1 hour
SIMULATION_TIMESTEP_HOURS  = 1.0  # Floating-point timestep used by battery model

# ── Solar PV array ────────────────────────────────────────────────────────────
SOLAR_CAPACITY_KW        = 40.0    # Rated peak output (kW)
SOLAR_REF_IRRADIANCE     = 1000.0  # Reference irradiance (W/m²)
SOLAR_PERFORMANCE_RATIO  = 0.82    # System performance ratio (losses, wiring, etc.)
SOLAR_TEMP_COEFF         = -0.004  # Power change per °C above reference (fraction/°C)
SOLAR_REF_TEMP_C         = 25.0    # Reference cell temperature (°C)

# ── Wind turbine ──────────────────────────────────────────────────────────────
WIND_CAPACITY_KW    = 50.0  # Rated output at rated wind speed (kW)
WIND_CUT_IN_MS      = 3.0   # Minimum wind speed to generate (m/s)
WIND_RATED_MS       = 12.0  # Wind speed at rated output (m/s)
WIND_CUT_OUT_MS     = 25.0  # Wind speed above which turbine shuts down (m/s)

# ── Diesel generators ────────────────────────────────────────────────────────
# Generator 1
GENERATOR_1_RATED_KW      = 80.0   # Maximum output (kW)
GENERATOR_1_MINIMUM_KW    = 20.0   # Minimum operating output (kW)
GENERATOR_1_IDLE_FUEL_LPH = 3.0    # Fuel burned per hour just to keep running (L/h)
GENERATOR_1_FUEL_PER_KWH  = 0.25   # Additional fuel per kWh generated (L/kWh)

# Generator 2
GENERATOR_2_RATED_KW      = 120.0  # Maximum output (kW)
GENERATOR_2_MINIMUM_KW    = 30.0   # Minimum operating output (kW)
GENERATOR_2_IDLE_FUEL_LPH = 4.0    # Fuel burned per hour just to keep running (L/h)
GENERATOR_2_FUEL_PER_KWH  = 0.23   # Additional fuel per kWh generated (L/kWh)

# Shared fuel tank
FUEL_TANK_LITRES          = 5000.0 # Total diesel fuel available (litres)

# ── Battery storage ───────────────────────────────────────────────────────────
BATTERY_CAPACITY_KWH         = 300.0  # Total usable energy capacity (kWh)
BATTERY_MAX_CHARGE_KW        = 60.0   # Maximum charging power (kW)
BATTERY_MAX_DISCHARGE_KW     = 60.0   # Maximum discharging power (kW)
BATTERY_CHARGE_EFFICIENCY    = 0.95   # Charging efficiency (95 %)
BATTERY_DISCHARGE_EFFICIENCY = 0.95   # Discharging efficiency (95 %)
BATTERY_MIN_SOC_FRACTION     = 0.25   # Minimum SOC — never discharge below 25 %
BATTERY_INITIAL_SOC_FRACTION = 0.70   # Starting SOC for simulation (70 %)

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

# ── Compatibility aliases for Member 2 ───────────────────────────────────────
# Maps Member 2's original variable names to Member 1's canonical constants.
# Do not remove until Member 2's module is updated to use the new names.
SOLAR_EFFICIENCY      = SOLAR_PERFORMANCE_RATIO
NUM_GENERATORS        = 2
GEN_RATED_KW          = GENERATOR_1_RATED_KW
GEN_MIN_LOAD_FRAC     = GENERATOR_1_MINIMUM_KW / GENERATOR_1_RATED_KW
GEN_FUEL_RATE_L_KWH   = GENERATOR_1_FUEL_PER_KWH
BATTERY_MAX_SOC       = 1.00
BATTERY_MIN_SOC       = BATTERY_MIN_SOC_FRACTION
BATTERY_CHARGE_EFF    = BATTERY_CHARGE_EFFICIENCY
BATTERY_DISCHARGE_EFF = BATTERY_DISCHARGE_EFFICIENCY
BATTERY_MAX_RATE_KW   = BATTERY_MAX_CHARGE_KW
BATTERY_INITIAL_SOC   = BATTERY_INITIAL_SOC_FRACTION
