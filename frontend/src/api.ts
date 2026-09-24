import type { BackendTwinTelemetry, DashboardPayload, TwinTelemetry } from './types'

const toTwinTelemetry = (telemetry: BackendTwinTelemetry): TwinTelemetry => ({
  timestamp: telemetry.timestamp,
  temperatureC: telemetry.temperature_c,
  irradianceWm2: telemetry.irradiance_w_m2,
  windSpeedMs: telemetry.wind_speed_ms,
  totalLoadKw: telemetry.total_load_kw,
  solarPowerKw: telemetry.solar_power_kw,
  windPowerKw: telemetry.wind_power_kw,
  renewableUsedKw: telemetry.renewable_used_kw,
  generatorTotalKw: telemetry.generator_total_kw,
  batterySocKwh: telemetry.battery_soc_kwh,
  fuelRemainingLitres: telemetry.fuel_remaining_litres,
  unmetLoadKw: telemetry.unmet_load_kw,
  criticalLoadServed: telemetry.critical_load_served,
})

export type DashboardData = DashboardPayload & { currentTelemetry: TwinTelemetry }

export async function fetchDashboardData(scenario = 'normal', horizonHours = 24): Promise<DashboardData> {
  const response = await fetch(`/api/dashboard?scenario=${encodeURIComponent(scenario)}&horizon_hours=${horizonHours}`)
  if (!response.ok) throw new Error(`Dashboard API returned ${response.status}`)
  const payload: DashboardPayload = await response.json()
  return { ...payload, currentTelemetry: toTwinTelemetry(payload.telemetry.latest) }
}
