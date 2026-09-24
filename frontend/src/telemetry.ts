import type { TwinTelemetry } from './types'

export const renewableShare = (telemetry: TwinTelemetry) => telemetry.totalLoadKw === 0 ? 0 : Math.round((telemetry.renewableUsedKw / telemetry.totalLoadKw) * 100)
export const batteryPercent = (telemetry: TwinTelemetry) => Math.round((telemetry.batterySocKwh / 300) * 100)
