import { Billboard, Html, Line, OrbitControls, Sparkles, useTexture } from '@react-three/drei'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { stations } from './stations'
import type { Station, TwinTelemetry } from './types'

const RADIUS = 1.34
const CAMERA_VECTOR = new THREE.Vector3(0, -1, 0)

const latLngToVector = (latitude: number, longitude: number, radius = RADIUS) => {
  const lat = THREE.MathUtils.degToRad(latitude)
  const lon = THREE.MathUtils.degToRad(longitude)
  return new THREE.Vector3(radius * Math.cos(lat) * Math.cos(lon), radius * Math.sin(lat), radius * Math.cos(lat) * Math.sin(lon))
}

const atmosphereVertex = 'varying vec3 n; void main(){ n=normalize(normalMatrix*normal); gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }'
const atmosphereFragment = 'varying vec3 n; void main(){ float rim=pow(1.-abs(n.z),3.2); gl_FragColor=vec4(.08,.72,1.,rim*.30); }'
const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))
type GlobeEnvironment = { telemetry: TwinTelemetry; stormRisk: boolean; connectivityStatus?: string }

function Aurora({ active, stormRisk }: { active: boolean; stormRisk: boolean }) {
  const ribbon = useRef<THREE.Group>(null)
  const lines = useMemo(() => [-.42, 0, .42].map((offset) => Array.from({ length: 24 }, (_, index) => {
    const t = index / 23
    return new THREE.Vector3(-2.6 + t * 5.2, 1.72 + Math.sin(t * Math.PI * 2.1 + offset * 3) * .18 + offset * .18, -.9 + Math.cos(t * Math.PI * 1.35) * .28)
  })), [])
  useFrame(({ clock }) => { if (ribbon.current) { ribbon.current.rotation.z = Math.sin(clock.getElapsedTime() * .08) * .045; ribbon.current.position.y = Math.sin(clock.getElapsedTime() * .13) * .05 } })
  if (!active) return null
  const opacity = stormRisk ? .30 : .18
  return <group ref={ribbon}>{lines.map((points, index) => <Line key={index} points={points} color={index === 1 ? '#55f0c6' : '#4abfff'} transparent opacity={opacity} lineWidth={index === 1 ? 1.25 : .8} />)}</group>
}

function Snowfall({ windSpeed, temperature }: { windSpeed: number; temperature: number }) {
  const points = useRef<THREE.Points>(null)
  const particleState = useMemo(() => Array.from({ length: 320 }, (_, index) => ({ speed: .22 + (index % 7) * .035, drift: (index % 13 - 6) * .004 })), [])
  const positions = useMemo(() => Float32Array.from({ length: particleState.length * 3 }, (_, index) => {
    const particle = Math.floor(index / 3); const channel = index % 3
    return channel === 0 ? ((particle * 37) % 100) / 100 * 5 - 2.5 : channel === 1 ? ((particle * 53) % 100) / 100 * 4 - 1.4 : -1.8 - ((particle * 19) % 100) / 100 * 2.8
  }), [particleState.length])
  useFrame((_, delta) => {
    if (!points.current) return
    const attribute = points.current.geometry.getAttribute('position') as THREE.BufferAttribute
    const drift = clamp(windSpeed, 0, 22) * .012
    particleState.forEach((particle, index) => { const offset = index * 3; attribute.array[offset] += (particle.drift + drift) * delta; attribute.array[offset + 1] -= particle.speed * delta; if (attribute.array[offset + 1] < -1.65) { attribute.array[offset + 1] = 2.5; attribute.array[offset] = ((index * 37) % 100) / 100 * 5 - 2.5 } })
    attribute.needsUpdate = true
  })
  if (temperature > 1) return null
  return <points ref={points}><bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]} /></bufferGeometry><pointsMaterial color="#d8f5ff" size={.018} transparent opacity={.36} depthWrite={false} sizeAttenuation /></points>
}

function WindField({ windSpeed }: { windSpeed: number }) {
  const points = useRef<THREE.Points>(null)
  const count = Math.round(clamp(windSpeed * 6, 16, 100))
  const positions = useMemo(() => Float32Array.from({ length: 108 * 3 }, (_, index) => { const particle = Math.floor(index / 3); const channel = index % 3; return channel === 0 ? ((particle * 29) % 100) / 100 * 5 - 2.5 : channel === 1 ? ((particle * 47) % 100) / 100 * 2.7 - .5 : -1.4 - ((particle * 17) % 100) / 100 * 2 }), [])
  useFrame((_, delta) => { if (!points.current) return; const attribute = points.current.geometry.getAttribute('position') as THREE.BufferAttribute; const speed = .28 + clamp(windSpeed, 0, 30) * .055; for (let index = 0; index < count; index += 1) { const offset = index * 3; attribute.array[offset] += speed * delta; if (attribute.array[offset] > 2.6) attribute.array[offset] = -2.6 } attribute.needsUpdate = true })
  return <points ref={points}><bufferGeometry drawRange={{ start: 0, count }}><bufferAttribute attach="attributes-position" args={[positions, 3]} /></bufferGeometry><pointsMaterial color="#75dfff" size={.013} transparent opacity={clamp(windSpeed / 42, .10, .34)} depthWrite={false} sizeAttenuation /></points>
}

function EnergyPath({ position, color, power, phase }: { position: THREE.Vector3; color: string; power: number; phase: number }) {
  const particle = useRef<THREE.Mesh>(null)
  const normal = useMemo(() => position.clone().normalize(), [position])
  const rotation = useMemo(() => new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), normal), [normal])
  const path = useMemo(() => [new THREE.Vector3(-.10, .015, 0), new THREE.Vector3(0, .15, .015), new THREE.Vector3(.10, .015, 0)], [])
  useFrame(({ clock }) => { const t = (clock.getElapsedTime() * (.22 + clamp(power, 0, 80) / 180) + phase) % 1; particle.current?.position.copy(new THREE.QuadraticBezierCurve3(path[0], path[1], path[2]).getPoint(t)) })
  if (power <= .05) return null
  return <group position={position} quaternion={rotation}><Line points={path} color={color} transparent opacity={clamp(power / 110, .16, .52)} lineWidth={.75} /><mesh ref={particle}><sphereGeometry args={[.014, 10, 10]} /><meshBasicMaterial color={color} toneMapped={false} /></mesh></group>
}

function StationMarker({ station, onSelect, online }: { station: Station; onSelect: (station: Station) => void; online: boolean }) {
  const marker = useRef<THREE.Group>(null)
  const position = useMemo(() => latLngToVector(station.latitude, station.longitude, RADIUS + .04), [station])
  const { gl } = useThree()
  useFrame(({ clock }) => marker.current?.scale.setScalar(1 + Math.sin(clock.getElapsedTime() * 2.2) * .10))
  return <group ref={marker} position={position}><mesh onPointerOver={() => { gl.domElement.style.cursor = 'pointer' }} onPointerOut={() => { gl.domElement.style.cursor = 'grab' }} onClick={(event) => { event.stopPropagation(); onSelect(station) }}><sphereGeometry args={[.035, 18, 18]} /><meshBasicMaterial color={online ? '#54f4ca' : '#f5bb64'} toneMapped={false} /></mesh><mesh rotation-x={Math.PI / 2}><ringGeometry args={[.065,.075,32]} /><meshBasicMaterial color={online ? '#6efbda' : '#f5bb64'} transparent opacity={.8} side={THREE.DoubleSide} /></mesh><pointLight color={online ? '#56f0c3' : '#f5bb64'} intensity={2.2} distance={.48} /><mesh position={[0,.07,0]}><cylinderGeometry args={[.004,.004,.13,6]} /><meshBasicMaterial color="#bdeeff" /></mesh><mesh position={[0,.142,0]}><sphereGeometry args={[.011,8,8]} /><meshBasicMaterial color={online ? '#53f4ca' : '#f5bb64'} toneMapped={false} /></mesh><Billboard><Html position={[.08,.08,0]} distanceFactor={1.12} transform><div className="station-label"><b>BHARATI</b><small>AURORA TWIN<br />{online ? 'ONLINE' : 'LINK DEGRADED'}</small></div></Html></Billboard></group>
}

function Earth({ station, onSelect, telemetry, connectivityStatus }: { station: Station; onSelect: (station: Station) => void; telemetry: TwinTelemetry; connectivityStatus?: string }) {
  const globe = useRef<THREE.Group>(null)
  const clouds = useRef<THREE.Mesh>(null)
  const target = useRef(new THREE.Quaternion())
  const [dayMap, cloudMap] = useTexture(['/assets/earth/nasa-blue-marble-day-2048.jpg', '/assets/earth/nasa-blue-marble-clouds-2048.jpg'])
  const { gl } = useThree()
  useEffect(() => {
    const maxAnisotropy = Math.min(8, gl.capabilities.getMaxAnisotropy())
    dayMap.colorSpace = THREE.SRGBColorSpace
    dayMap.anisotropy = maxAnisotropy
    dayMap.generateMipmaps = true
    cloudMap.colorSpace = THREE.NoColorSpace
    cloudMap.anisotropy = maxAnisotropy
    cloudMap.generateMipmaps = true
    dayMap.needsUpdate = true
    cloudMap.needsUpdate = true
  }, [cloudMap, dayMap, gl])
  useEffect(() => { target.current.setFromUnitVectors(latLngToVector(station.latitude, station.longitude).normalize(), CAMERA_VECTOR) }, [station])
  useFrame((_, delta) => { if (globe.current) globe.current.quaternion.slerp(target.current, .025); if (clouds.current) clouds.current.rotation.y += delta * .006 })
  const stationPosition = useMemo(() => latLngToVector(station.latitude, station.longitude, RADIUS + .06), [station])
  return <group ref={globe}><mesh><sphereGeometry args={[RADIUS, 128, 128]} /><meshPhongMaterial map={dayMap} bumpMap={dayMap} bumpScale={.045} specular="#1c4d68" shininess={12} /></mesh><mesh ref={clouds} scale={1.012}><sphereGeometry args={[RADIUS, 112, 112]} /><meshBasicMaterial color="#d8f4ff" alphaMap={cloudMap} transparent opacity={.38} depthWrite={false} /></mesh><mesh scale={1.075}><sphereGeometry args={[RADIUS, 80, 80]} /><shaderMaterial transparent side={THREE.BackSide} vertexShader={atmosphereVertex} fragmentShader={atmosphereFragment} /></mesh><EnergyPath position={stationPosition} color="#50eac1" power={telemetry.renewableUsedKw} phase={0} /><EnergyPath position={stationPosition} color="#58bcff" power={telemetry.batteryDischargeKw} phase={.33} /><EnergyPath position={stationPosition} color="#e4ae63" power={telemetry.generatorTotalKw} phase={.66} /><StationMarker station={station} onSelect={onSelect} online={connectivityStatus === 'ONLINE'} /></group>
}

function Scene({ selected, onSelect, telemetry, stormRisk, connectivityStatus }: { selected: Station; onSelect: (station: Station) => void; telemetry: TwinTelemetry | null; stormRisk: boolean; connectivityStatus?: string }) {
  const windSpeed = telemetry?.windSpeedMs ?? 0
  const temperature = telemetry?.temperatureC ?? 8
  const auroraActive = temperature < 2 || stormRisk
  return <><ambientLight intensity={.42} /><directionalLight position={[-3,-2,4]} intensity={1.45} color="#d2efff" /><pointLight position={[2,-1,-3]} intensity={.45} color="#2be6c1" /><Sparkles count={70} scale={7} size={1.05} speed={.035} color="#72ddff" /><Aurora active={auroraActive} stormRisk={stormRisk} /><Snowfall windSpeed={windSpeed} temperature={temperature} /><WindField windSpeed={windSpeed} />{telemetry && <Earth station={selected} onSelect={onSelect} telemetry={telemetry} connectivityStatus={connectivityStatus} />}<OrbitControls enablePan={false} enableDamping dampingFactor={.08} minDistance={2.75} maxDistance={4.7} rotateSpeed={.5} autoRotate autoRotateSpeed={.18} /></>
}

export default function Globe({ selected, onSelect, resetToken }: { selected: Station; onSelect: (station: Station) => void; resetToken: number }) {
  const [environment, setEnvironment] = useState<GlobeEnvironment | null>(null)
  useEffect(() => { const update = (event: Event) => setEnvironment((event as CustomEvent<GlobeEnvironment>).detail); window.addEventListener('aurora-globe-data', update); return () => window.removeEventListener('aurora-globe-data', update) }, [])
  return <Canvas key={resetToken} camera={{ position:[0,-3.82,0], fov:42 }} gl={{ antialias:true }} dpr={[1,2]}><color attach="background" args={['#020a16']} /><fog attach="fog" args={['#020a16',4,9]} /><Scene selected={selected} onSelect={onSelect} telemetry={environment?.telemetry ?? null} stormRisk={environment?.stormRisk ?? false} connectivityStatus={environment?.connectivityStatus} /></Canvas>
}
