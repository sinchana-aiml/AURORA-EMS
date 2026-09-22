import type { Station } from './types'

export const stations: Station[] = [
  { id: 'bharati', name: 'Bharati', country: 'India', latitude: -69.4069, longitude: 76.1956, source: 'aurora-simulation', status: 'Online' },
  { id: 'maitri', name: 'Maitri', country: 'India', latitude: -70.7667, longitude: 11.7333, source: 'research-network-reference', status: 'Reference' },
  { id: 'mcmurdo', name: 'McMurdo', country: 'United States', latitude: -77.8419, longitude: 166.6863, source: 'research-network-reference', status: 'Reference' },
  { id: 'amundsen', name: 'Amundsen-Scott', country: 'United States', latitude: -90, longitude: 0, source: 'research-network-reference', status: 'Reference' },
  { id: 'concordia', name: 'Concordia', country: 'France / Italy', latitude: -75.1000, longitude: 123.3500, source: 'research-network-reference', status: 'Reference' },
]
