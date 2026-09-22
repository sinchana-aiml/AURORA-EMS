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
