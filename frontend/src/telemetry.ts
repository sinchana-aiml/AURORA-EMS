import type { TwinTelemetry } from './types'

// Mapped from the documented verified 24-hour AURORA-EMS Digital Twin example
// (docs/telemetry_schema.md). This is explicitly simulated/prototype telemetry.
export const bharatiTelemetry: TwinTelemetry = {
  timestamp: '2024-07-01T23:00', temperatureC: -18, irradianceWm2: 50, windSpeedMs: 5, totalLoadKw: 59.4,
  solarPowerKw: 1.9168, windPowerKw: 11.1111, renewableUsedKw: 13.0279,
  generatorTotalKw: 20, batterySocKwh: 103.5, fuelRemainingLitres: 4806.2881,
  unmetLoadKw: 0, criticalLoadServed: true,
}

export const renewableShare = Math.round((bharatiTelemetry.renewableUsedKw / bharatiTelemetry.totalLoadKw) * 100)
export const batteryPercent = Math.round((bharatiTelemetry.batterySocKwh / 300) * 100)
