import { Billboard, Html, Line, OrbitControls, Sparkles } from '@react-three/drei'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { stations } from './stations'
import type { Station } from './types'

const RADIUS = 1.34
const CAMERA_VECTOR = new THREE.Vector3(0, -1, 0)
const latLngToVector = (latitude: number, longitude: number, radius = RADIUS) => {
  const lat = THREE.MathUtils.degToRad(latitude)
  const lon = THREE.MathUtils.degToRad(longitude)
  return new THREE.Vector3(radius * Math.cos(lat) * Math.cos(lon), radius * Math.sin(lat), radius * Math.cos(lat) * Math.sin(lon))
}

// Simplified coastline vertices form a genuine polar geographic land layer,
// rather than a flat Antarctica decal. Detail is deliberately modest for UI performance.
const antarcticCoast = [
  [-74, -62], [-70, -58], [-66, -57], [-64, -60], [-63, -65], [-65, -72], [-68, -78], [-68, -88], [-70, -96], [-72, -108], [-73, -118], [-74, -128], [-74, -142], [-75, -154], [-77, -166], [-78, 178], [-79, 164], [-78, 151], [-76, 143], [-75, 134], [-74, 124], [-75, 113], [-74, 102], [-72, 92], [-69, 82], [-68, 73], [-67, 63], [-68, 53], [-69, 44], [-70, 35], [-70, 26], [-69, 18], [-70, 9], [-71, -1], [-72, -12], [-72, -23], [-73, -34], [-74, -45], [-74, -54],
] as const

function AntarcticaLand() {
  const geometry = useMemo(() => {
    const vertices = [latLngToVector(-89.5, 0, RADIUS + 0.018)]
    antarcticCoast.forEach(([lat, lon]) => vertices.push(latLngToVector(lat, lon, RADIUS + 0.02)))
    const positions = new Float32Array(vertices.length * 3)
    const colours = new Float32Array(vertices.length * 3)
    vertices.forEach((point, index) => {
      positions.set(point.toArray(), index * 3)
      const shade = 0.68 + (index % 4) * 0.07
      colours.set([shade * 0.72, shade * 0.9, shade], index * 3)
    })
    const indices: number[] = []
    for (let index = 1; index < vertices.length; index += 1) indices.push(0, index, index === vertices.length - 1 ? 1 : index + 1)
    const land = new THREE.BufferGeometry()
    land.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    land.setAttribute('color', new THREE.BufferAttribute(colours, 3))
    land.setIndex(indices)
    land.computeVertexNormals()
    return land
  }, [])
  return <mesh geometry={geometry}><meshStandardMaterial vertexColors roughness={0.72} metalness={0.08} transparent opacity={0.96} side={THREE.DoubleSide} /></mesh>
}

function GeographicGrid() {
  const lines = useMemo(() => {
    const result: THREE.Vector3[][] = []
    for (let latitude = -75; latitude <= 75; latitude += 15) result.push(Array.from({ length: 73 }, (_, i) => latLngToVector(latitude, -180 + i * 5, RADIUS + 0.007)))
    for (let longitude = -180; longitude < 180; longitude += 20) result.push(Array.from({ length: 37 }, (_, i) => latLngToVector(-90 + i * 5, longitude, RADIUS + 0.008)))
    return result
  }, [])
  return <group>{lines.map((points, index) => <Line key={index} points={points} color="#56c9eb" transparent opacity={index < 11 ? 0.09 : 0.06} lineWidth={0.45} />)}</group>
}

function EnergyArc({ from, to }: { from: Station; to: Station }) {
  const traveller = useRef<THREE.Mesh>(null)
  const curve = useMemo(() => {
    const start = latLngToVector(from.latitude, from.longitude, RADIUS + 0.035)
    const end = latLngToVector(to.latitude, to.longitude, RADIUS + 0.035)
    return new THREE.QuadraticBezierCurve3(start, start.clone().add(end).normalize().multiplyScalar(1.82), end)
  }, [from, to])
  const points = useMemo(() => curve.getPoints(60), [curve])
  useFrame(({ clock }) => traveller.current?.position.copy(curve.getPoint((clock.getElapsedTime() * 0.09 + to.longitude / 360) % 1)))
  return <><Line points={points} color="#39d9cf" transparent opacity={0.34} lineWidth={0.75} dashed dashSize={0.05} gapSize={0.05} /><mesh ref={traveller}><sphereGeometry args={[0.018, 10, 10]} /><meshBasicMaterial color="#a9fff1" toneMapped={false} /></mesh></>
}

function StationMarker({ station, selected, onSelect }: { station: Station; selected: boolean; onSelect: (station: Station) => void }) {
  const [hovered, setHovered] = useState(false)
  const marker = useRef<THREE.Group>(null)
  const position = useMemo(() => latLngToVector(station.latitude, station.longitude, RADIUS + 0.036), [station])
  const colour = station.source === 'aurora-simulation' ? '#51f0bb' : '#4dcfff'
  const { gl } = useThree()
  useFrame(({ clock }) => marker.current?.scale.setScalar(1 + Math.sin(clock.getElapsedTime() * 2.5 + station.longitude) * 0.12 + (selected ? 0.18 : 0)))
  return <group ref={marker} position={position}>
    <mesh onPointerOver={() => { setHovered(true); gl.domElement.style.cursor = 'pointer' }} onPointerOut={() => { setHovered(false); gl.domElement.style.cursor = 'grab' }} onClick={(event) => { event.stopPropagation(); onSelect(station) }}>
      <sphereGeometry args={[0.033, 18, 18]} /><meshBasicMaterial color={colour} toneMapped={false} />
    </mesh>
    <mesh rotation-x={Math.PI / 2}><ringGeometry args={[selected || hovered ? 0.06 : 0.045, selected || hovered ? 0.068 : 0.05, 32]} /><meshBasicMaterial color={colour} transparent opacity={selected || hovered ? 0.85 : 0.36} side={THREE.DoubleSide} /></mesh>
    <pointLight color={colour} intensity={selected ? 2.5 : 1.2} distance={0.42} />
    {selected && <Billboard><Html distanceFactor={8} transform><div className="station-label"><b>{station.name}</b><small>{station.source === 'aurora-simulation' ? 'AURORA TWIN · ONLINE' : 'RESEARCH NETWORK REFERENCE'}</small></div></Html></Billboard>}
  </group>
}

function Earth({ selected, onSelect }: { selected: Station; onSelect: (station: Station) => void }) {
  const network = useRef<THREE.Group>(null)
  const target = useRef(new THREE.Quaternion())
  useEffect(() => { target.current.setFromUnitVectors(latLngToVector(selected.latitude, selected.longitude).normalize(), CAMERA_VECTOR) }, [selected])
  useFrame(() => network.current?.quaternion.slerp(target.current, 0.035))
  return <group ref={network}>
    <mesh><sphereGeometry args={[RADIUS, 96, 96]} /><shaderMaterial vertexShader={`varying vec3 normalDir; varying vec3 world; void main(){normalDir=normal;world=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`} fragmentShader={`varying vec3 normalDir; varying vec3 world; void main(){float bands=0.5+0.5*sin(world.y*38.0+sin(world.x*13.0)*1.8);float depth=0.5+0.5*normalDir.z;vec3 ocean=mix(vec3(0.005,0.035,0.08),vec3(0.015,0.15,0.25),depth);ocean+=bands*0.025;gl_FragColor=vec4(ocean,1.0);}`} /><AntarcticaLand /><GeographicGrid /></mesh>
    <mesh scale={1.075}><sphereGeometry args={[RADIUS, 64, 64]} /><shaderMaterial transparent side={THREE.BackSide} vertexShader={`varying vec3 n; void main(){n=normalize(normalMatrix*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`} fragmentShader={`varying vec3 n; void main(){float rim=pow(1.0-abs(n.z),3.0);gl_FragColor=vec4(0.16,0.75,1.0,rim*0.30);}`} /></mesh>
    {stations.slice(1).map((station) => <EnergyArc key={station.id} from={stations[0]} to={station} />)}
    {stations.map((station) => <StationMarker key={station.id} station={station} selected={selected.id === station.id} onSelect={onSelect} />)}
  </group>
}

function TwinScene({ selected, onSelect }: { selected: Station; onSelect: (station: Station) => void }) {
  return <><ambientLight intensity={0.55} /><directionalLight position={[-3, -2, 4]} intensity={1.1} color="#8cdbff" /><Sparkles count={120} scale={8} size={1} speed={0.08} color="#74d8ff" /><Earth selected={selected} onSelect={onSelect} /><OrbitControls enablePan={false} enableDamping dampingFactor={0.07} minDistance={2.6} maxDistance={5.3} rotateSpeed={0.55} /></>
}

export default function Globe({ selected, onSelect, resetToken }: { selected: Station; onSelect: (station: Station) => void; resetToken: number }) {
  return <Canvas key={resetToken} camera={{ position: [0, -3.82, 0], fov: 42 }} gl={{ antialias: true }} dpr={[1, 2]}><color attach="background" args={['#020a16']} /><fog attach="fog" args={['#020a16', 4, 9]} /><TwinScene selected={selected} onSelect={onSelect} /></Canvas>
}
