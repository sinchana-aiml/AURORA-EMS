import { Line } from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'
import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import type { TwinTelemetry } from './types'

type EnvironmentState = { telemetry: TwinTelemetry; stormRisk: boolean; connectivityStatus?: string }
const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))
const seeded = (index: number, multiplier: number) => ((index * multiplier) % 101) / 101

function useReducedMotion() {
  const [reduced, setReduced] = useState(false)
  useEffect(() => { const media = window.matchMedia('(prefers-reduced-motion: reduce)'); const update = () => setReduced(media.matches); update(); media.addEventListener('change', update); return () => media.removeEventListener('change', update) }, [])
  return reduced
}

function AuroraRibbons({ stormRisk, reduced }: { stormRisk: boolean; reduced: boolean }) {
  const group = useRef<THREE.Group>(null)
  const ribbons = useMemo(() => [-.55, -.18, .2, .55].map((offset) => Array.from({ length: 28 }, (_, index) => {
    const t = index / 27
    return new THREE.Vector3(-5 + t * 10, 1.4 + Math.sin(t * Math.PI * 2.2 + offset * 4) * .28 + offset * .16, -3.8 + Math.cos(t * Math.PI * 1.4) * .6)
  })), [])
  useFrame(({ clock }) => { if (!group.current || reduced) return; group.current.position.y = Math.sin(clock.getElapsedTime() * .06) * .12; group.current.rotation.z = Math.sin(clock.getElapsedTime() * .035) * .025 })
  const opacity = stormRisk ? .18 : .10
  return <group ref={group}>{ribbons.map((points, index) => <Line key={index} points={points} color={index % 3 === 1 ? '#55e9c1' : index % 3 === 2 ? '#45aef4' : '#70d9de'} transparent opacity={opacity} lineWidth={index === 1 ? 1.2 : .7} />)}</group>
}

function FallingSnow({ windSpeed, temperature, reduced, layer }: { windSpeed: number; temperature: number; reduced: boolean; layer: 0 | 1 }) {
  const points = useRef<THREE.Points>(null)
  const count = layer === 0 ? 150 : 90
  const positions = useMemo(() => Float32Array.from({ length: count * 3 }, (_, entry) => {
    const index = Math.floor(entry / 3); const axis = entry % 3
    return axis === 0 ? seeded(index + layer * 41, 37) * 9 - 4.5 : axis === 1 ? seeded(index + layer * 31, 53) * 6 - 2.5 : -1.6 - seeded(index + layer * 17, 19) * (layer === 0 ? 2.5 : 4.5)
  }), [count, layer])
  useFrame((_, delta) => {
    if (!points.current || reduced) return
    const position = points.current.geometry.getAttribute('position') as THREE.BufferAttribute
    const drift = clamp(windSpeed, 0, 26) * .009
    for (let index = 0; index < count; index += 1) { const offset = index * 3; position.array[offset] += (drift + (index % 7 - 3) * .002) * delta; position.array[offset + 1] -= (.13 + (index % 5) * .027) * delta; if (position.array[offset + 1] < -2.8) { position.array[offset + 1] = 3.4; position.array[offset] = seeded(index + layer * 13, 37) * 9 - 4.5 } }
    position.needsUpdate = true
  })
  if (temperature > 2) return null
  return <points ref={points}><bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]} /></bufferGeometry><pointsMaterial color={layer === 0 ? '#e8fbff' : '#aee8ff'} size={layer === 0 ? .018 : .012} transparent opacity={layer === 0 ? .26 : .16} depthWrite={false} sizeAttenuation /></points>
}

function AtmosphericParticles({ reduced }: { reduced: boolean }) {
  const points = useRef<THREE.Points>(null)
  const count = 72
  const positions = useMemo(() => Float32Array.from({ length: count * 3 }, (_, entry) => { const index = Math.floor(entry / 3); const axis = entry % 3; return axis === 0 ? seeded(index, 43) * 9 - 4.5 : axis === 1 ? seeded(index, 71) * 5 - 2.5 : -2.4 - seeded(index, 23) * 4.5 }), [])
  useFrame(({ clock }) => { if (!points.current || reduced) return; points.current.rotation.y = clock.getElapsedTime() * .004; points.current.position.y = Math.sin(clock.getElapsedTime() * .035) * .08 })
  return <points ref={points}><bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]} /></bufferGeometry><pointsMaterial color="#81cdeb" size={.011} transparent opacity={.13} depthWrite={false} sizeAttenuation /></points>
}

function PolarMist({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null)
  useFrame(({ clock }) => { if (!group.current || reduced) return; group.current.position.x = Math.sin(clock.getElapsedTime() * .025) * .26; group.current.position.y = Math.cos(clock.getElapsedTime() * .02) * .06 })
  return <group ref={group} position={[0,-2.5,-4.8]}>{[-2.8, 0, 2.8].map((x, index) => <mesh key={x} position={[x, index % 2 ? .13 : 0, 0]} scale={[2.7, .38, .24]}><sphereGeometry args={[1,20,12]} /><meshBasicMaterial color={index === 1 ? '#245c78' : '#1b4e72'} transparent opacity={.055} depthWrite={false} /></mesh>)}</group>
}

function GlobalScene({ environment, reduced }: { environment: EnvironmentState | null; reduced: boolean }) {
  const windSpeed = environment?.telemetry.windSpeedMs ?? 0
  const temperature = environment?.telemetry.temperatureC ?? 6
  return <><AuroraRibbons stormRisk={environment?.stormRisk ?? false} reduced={reduced} /><FallingSnow windSpeed={windSpeed} temperature={temperature} reduced={reduced} layer={0} /><FallingSnow windSpeed={windSpeed} temperature={temperature} reduced={reduced} layer={1} /><AtmosphericParticles reduced={reduced} /><PolarMist reduced={reduced} /></>
}

export default function Polar3DAtmosphere() {
  const [environment, setEnvironment] = useState<EnvironmentState | null>(null)
  const reduced = useReducedMotion()
  useEffect(() => { const update = (event: Event) => setEnvironment((event as CustomEvent<EnvironmentState>).detail); window.addEventListener('aurora-globe-data', update); return () => window.removeEventListener('aurora-globe-data', update) }, [])
  return <div className="polar-3d-atmosphere" aria-hidden="true"><Canvas camera={{ position:[0,0,6], fov:52 }} dpr={[1,1.5]} gl={{ alpha:true, antialias:true }}><GlobalScene environment={environment} reduced={reduced} /></Canvas></div>
}
