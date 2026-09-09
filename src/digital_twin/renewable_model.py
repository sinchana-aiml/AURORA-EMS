# src/digital_twin/renewable_model.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Renewable Generation Model
# Solar PV and wind turbine output calculations.
# All formulas are PROTOTYPE / SIMULATED — not real NCPOR measurements.
# ─────────────────────────────────────────────────────────────────────────────

import config


def solar_pv_output(irradiance_w_m2, temperature_c):
    """
    Returns solar PV power output in kW.

    irradiance_w_m2 : sunlight intensity hitting the panels (W/m2)
    temperature_c   : outside air temperature (C)

    Formula (transparent prototype):
      irradiance_factor  = how much sun vs the reference 1000 W/m2
      temperature_factor = how much the heat reduces panel output
      output = capacity x irradiance_factor x temperature_factor x performance_ratio
    """
    # Step 1: fraction of reference sunlight (0.0 at night, 1.0 at full sun)
    irradiance_factor = max(0, irradiance_w_m2 / config.SOLAR_REF_IRRADIANCE)

    # Step 2: panels lose efficiency when warmer than 25 C, gain slightly when colder
    temperature_factor = 1 + config.SOLAR_TEMP_COEFF * (temperature_c - config.SOLAR_REF_TEMP_C)

    # Step 3: multiply rated capacity by both factors and the system performance ratio
    output_kw = (config.SOLAR_CAPACITY_KW
                 * irradiance_factor
                 * temperature_factor
                 * config.SOLAR_PERFORMANCE_RATIO)

    # Step 4: clamp — output cannot be negative or exceed rated capacity
    return max(0.0, min(output_kw, config.SOLAR_CAPACITY_KW))  # kW


def wind_power_output(wind_speed_ms):
    """
    Returns wind turbine power output in kW using a linear power curve.

    wind_speed_ms : wind speed in metres per second (m/s)

    Power curve (4 regions):
      Below cut-in  (< 3.0 m/s)  : turbine is still, output = 0 kW
      Ramp-up zone  (3.0-12.0)   : output rises linearly from 0 to 50 kW
      Rated zone    (12.0-24.9)  : turbine runs at full 50 kW
      Cut-out       (>= 25.0 m/s): turbine shuts down for safety, output = 0 kW
    """
    # Region 1: too slow to spin the turbine
    if wind_speed_ms < config.WIND_CUT_IN_MS:
        return 0.0

    # Region 4: too fast — turbine shuts down to avoid damage
    if wind_speed_ms >= config.WIND_CUT_OUT_MS:
        return 0.0

    # Region 2: linearly scale output between cut-in and rated speed
    if wind_speed_ms < config.WIND_RATED_MS:
        fraction = ((wind_speed_ms - config.WIND_CUT_IN_MS)
                    / (config.WIND_RATED_MS - config.WIND_CUT_IN_MS))
        return config.WIND_CAPACITY_KW * fraction  # kW

    # Region 3: at or above rated speed — full output
    return config.WIND_CAPACITY_KW  # kW
