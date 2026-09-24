export type Station = {
  id: string
  name: string
  country: string
  latitude: number
  longitude: number
  source: 'aurora-simulation' | 'research-network-reference'
  status: 'Online' | 'Reference'
}

export type TwinTelemetry = {
  timestamp: string
  temperatureC: number
  irradianceWm2: number
  windSpeedMs: number
  totalLoadKw: number
  solarPowerKw: number
  windPowerKw: number
  renewableUsedKw: number
  generatorTotalKw: number
  batterySocKwh: number
  fuelRemainingLitres: number
  unmetLoadKw: number
  criticalLoadServed: boolean
}

export type BackendTwinTelemetry = {
  timestamp: string
  temperature_c: number
  irradiance_w_m2: number
  wind_speed_ms: number
  electrical_load_kw: number
  heating_load_kw: number
  total_load_kw: number
  solar_power_kw: number
  wind_power_kw: number
  renewable_used_kw: number
  battery_charge_kw: number
  battery_discharge_kw: number
  battery_soc_kwh: number
  generator_1_power_kw: number
  generator_2_power_kw: number
  generator_total_kw: number
  generator_to_battery_charge_kw: number
  excess_generation_kw: number
  fuel_used_litres: number
  fuel_remaining_litres: number
  curtailed_power_kw: number
  unmet_load_kw: number
  supplied_load_kw: number
  critical_load_served: boolean
}

export type ForecastRow = {
  timestamp: string
  step_ahead: number
  solar_power_kw_p10: number
  solar_power_kw_p50: number
  solar_power_kw_p90: number
  wind_power_kw_p10: number
  wind_power_kw_p50: number
  wind_power_kw_p90: number
  total_load_kw_p50: number
  net_load_kw_p50: number
  temperature_c_pred: number
  wind_speed_ms_pred: number
  irradiance_w_m2_pred: number
  storm_risk_flag: boolean
  turbine_cutout_risk: boolean
  confidence_score: number
  forecast_mode: string
}

export type DispatchSummary = {
  optimized_fuel_used_litres?: number
  optimized_final_soc_kwh?: number
  fuel_saved_liters?: number
  fuel_saved_pct?: number
}

export type DashboardPayload = {
  station: { id: string; name: string; latitude: number; longitude: number }
  provenance: { data_mode: string; weather_source: string; weather_sample: string }
  telemetry: { latest: BackendTwinTelemetry; history: BackendTwinTelemetry[] }
  forecast: { available: boolean; horizon_hours: number; rows: ForecastRow[]; error?: string }
  dispatch: { available: boolean; strategy: string; history: Record<string, unknown>[]; summary: DispatchSummary; error?: string }
  resilience: { available: boolean; connectivity_status: string; scenario: string; latest: Record<string, unknown> | null; error?: string }
}
