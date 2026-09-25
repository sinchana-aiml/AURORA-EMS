import { Line, Sparkles } from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'
import React, { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { AlertCircle, ArrowRight, Eye, EyeOff, Lock, User, Shield, Cpu, Activity, Zap } from 'lucide-react'

interface AuthExperienceProps {
  onLoginSuccess: () => void
}

const DEMO_USER = 'operator@aurora.ems'
const DEMO_PASS = 'aurora2026'

function useReducedMotion() {
  const [reduced, setReduced] = useState(false)
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReduced(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])
  return reduced
}

// 3D Polar Earth Globe Mesh for the Login Environment
function LoginEnvironmentGlobe({ reduced }: { reduced: boolean }) {
  const globeRef = useRef<THREE.Group>(null)

  useFrame((_, delta) => {
    if (!globeRef.current || reduced) return
    globeRef.current.rotation.y += delta * 0.05
  })

  return (
    <group ref={globeRef} position={[0, -0.35, -1.1]} rotation={[0.38, 0, 0]}>
      {/* Primary Globe Sphere */}
      <mesh>
        <sphereGeometry args={[1.75, 64, 64]} />
        <meshPhongMaterial
          color="#061b2e"
          emissive="#010c17"
          specular="#38bdf8"
          shininess={22}
          wireframe={false}
        />
      </mesh>

      {/* Outer Atmosphere Glow Shell */}
      <mesh scale={1.038}>
        <sphereGeometry args={[1.75, 48, 48]} />
        <meshBasicMaterial
          color="#38bdf8"
          transparent
          opacity={0.14}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Lat/Long Grid Rings */}
      <mesh scale={1.008} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.74, 1.75, 64]} />
        <meshBasicMaterial color="#50c7ff" transparent opacity={0.28} side={THREE.DoubleSide} />
      </mesh>

      <mesh scale={1.008} rotation={[0, Math.PI / 4, 0]}>
        <ringGeometry args={[1.74, 1.75, 64]} />
        <meshBasicMaterial color="#38bdf8" transparent opacity={0.18} side={THREE.DoubleSide} />
      </mesh>
    </group>
  )
}

// Volumetric 3D Aurora Environment Ribbon Layers
function Volumetric3DAurora({ authenticating, reduced }: { authenticating: boolean; reduced: boolean }) {
  const group = useRef<THREE.Group>(null)

  const layers = useMemo(() => [
    { z: -3.2, color: '#10b981', opacity: 0.35, lineWidth: 1.8, freq: 2.2 },
    { z: -4.8, color: '#38bdf8', opacity: 0.28, lineWidth: 1.4, freq: 1.8 },
    { z: -6.2, color: '#50c7ff', opacity: 0.22, lineWidth: 1.1, freq: 1.4 },
    { z: -7.8, color: '#54eec0', opacity: 0.16, lineWidth: 0.8, freq: 1.1 },
  ], [])

  const ribbonCurves = useMemo(() => layers.map((layer) => {
    return Array.from({ length: 36 }, (_, index) => {
      const t = index / 35
      return new THREE.Vector3(
        -9 + t * 18,
        2.4 + Math.sin(t * Math.PI * layer.freq) * 0.5,
        layer.z + Math.cos(t * Math.PI * 1.35) * 0.7
      )
    })
  }), [layers])

  useFrame(({ clock }) => {
    if (!group.current || reduced) return
    const t = clock.getElapsedTime()
    group.current.position.y = Math.sin(t * 0.08) * 0.2
    group.current.position.x = Math.cos(t * 0.05) * 0.15
    group.current.rotation.z = Math.sin(t * 0.035) * 0.03
  })

  return (
    <group ref={group}>
      {ribbonCurves.map((points, index) => {
        const layer = layers[index]
        const opacity = authenticating ? layer.opacity * 1.6 : layer.opacity
        return (
          <Line
            key={index}
            points={points}
            color={layer.color}
            transparent
            opacity={opacity}
            lineWidth={layer.lineWidth}
          />
        )
      })}
    </group>
  )
}

// 3D Scene Controller & Camera Motion
function SceneController({ authenticating, reduced }: { authenticating: boolean; reduced: boolean }) {
  useFrame(({ camera }) => {
    if (reduced) {
      camera.position.set(0, 0, 5)
      return
    }

    if (authenticating) {
      camera.position.z = THREE.MathUtils.lerp(camera.position.z, 1.2, 0.08)
    } else {
      camera.position.z = THREE.MathUtils.lerp(camera.position.z, 5, 0.04)
    }
  })

  return (
    <>
      <ambientLight intensity={0.45} />
      <directionalLight position={[-3, 3, 4]} intensity={1.35} color="#d2efff" />
      <pointLight position={[2, -1, 3]} intensity={0.85} color="#38bdf8" />
      <Sparkles count={90} scale={11} size={1.3} speed={0.03} color="#38bdf8" />
      <LoginEnvironmentGlobe reduced={reduced} />
      <Volumetric3DAurora authenticating={authenticating} reduced={reduced} />
    </>
  )
}

export default function AuthExperience({ onLoginSuccess }: AuthExperienceProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isAuthenticating, setIsAuthenticating] = useState(false)

  const reducedMotion = useReducedMotion()

  const handleAutoFill = () => {
    setUsername(DEMO_USER)
    setPassword(DEMO_PASS)
    setError(null)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (username.trim().toLowerCase() === DEMO_USER && password === DEMO_PASS) {
      setIsSubmitting(true)
      setIsAuthenticating(true)
      setTimeout(() => {
        onLoginSuccess()
      }, 750)
    } else {
      setError('Invalid username or password.')
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-view-root">
      {/* 3D WebGL Background Canvas */}
      <div className="auth-canvas-container">
        <Canvas camera={{ position: [0, 0, 5], fov: 46 }} dpr={[1, 1.5]} gl={{ antialias: true }}>
          <color attach="background" args={['#02060d']} />
          <fog attach="fog" args={['#02060d', 3.5, 12]} />
          <SceneController authenticating={isAuthenticating} reduced={reducedMotion} />
        </Canvas>
      </div>

      {/* Atmospheric Haze Backdrop */}
      <div className="polar-ambient-backdrop" />

      {/* Top Header Branding & Tagline */}
      <header className="auth-top-header">
        <div className="brand-logo-lockup">
          <svg className="brand-delta-logo" viewBox="0 0 40 40" fill="currentColor">
            <path d="M20 4L36 34H4L20 4Z" />
          </svg>
          <div className="brand-title-wrap">
            <h1>AURORA-EMS</h1>
            <p className="brand-subtitle">
              AI-Driven Energy Management System for Polar Research Stations
            </p>
          </div>
        </div>

        <div className="header-tagline">
          PREDICT • SIMULATE • OPTIMIZE • PROTECT
        </div>
      </header>

      {/* Environmental Floating Status Badges (Non-Numeric Status Annotations) */}
      <div className="holo-pos-left">
        <div className="holo-card-sm">
          <div className="holo-title-row">
            <i className="holo-dot" /> BHARATI STATION
          </div>
          <div className="holo-sub-label">ANTARCTICA</div>
        </div>
      </div>

      <div className="holo-pos-right">
        <div className="holo-status-item">
          <i className="holo-dot" /> SYSTEM ONLINE
        </div>
        <div className="holo-status-item">
          <i className="holo-dot" /> AI ENERGY MANAGEMENT
        </div>
      </div>

      {/* Main Command Center Layout Grid */}
      <main className="auth-main-layout">
        {/* Left Side: Product Description & Capabilities */}
        <section className="product-info-panel">
          <div className="info-kicker-badge">
            <Cpu size={14} />
            <span>AI-DRIVEN ENERGY INTELLIGENCE</span>
          </div>

          <p className="info-description-text">
            "AURORA-EMS combines AI forecasting, energy optimization,
            simulation and digital-twin intelligence to support resilient
            energy management in extreme polar environments."
          </p>

          <div className="capability-grid">
            <div className="capability-item">
              <Zap className="cap-icon" size={15} />
              <span>ENERGY FORECASTING</span>
            </div>
            <div className="capability-item">
              <Activity className="cap-icon" size={15} />
              <span>DIGITAL TWIN SIMULATION</span>
            </div>
            <div className="capability-item">
              <Cpu className="cap-icon" size={15} />
              <span>RENEWABLE OPTIMIZATION</span>
            </div>
            <div className="capability-item">
              <Shield className="cap-icon" size={15} />
              <span>CRITICAL SYSTEM PROTECTION</span>
            </div>
          </div>

          <div className="resilience-tagline">
            "Built for the extreme. Designed for resilience."
          </div>
        </section>

        {/* Right Side: Glassmorphic Command Center Login Card */}
        <section className={`login-card-stage ${isAuthenticating ? 'success-transition-zoom' : ''}`}>
          <div className="reference-login-card">
            <div className="card-brand-header">
              <svg className="card-logo-emblem" viewBox="0 0 40 40" fill="currentColor">
                <path d="M20 4L36 34H4L20 4Z" />
              </svg>
              <h2>AURORA-EMS</h2>
              <p className="card-kicker-text">POLAR ENERGY INTELLIGENCE</p>
            </div>

            <form className="login-form-group" onSubmit={handleSubmit}>
              {error && (
                <div className="auth-error-alert">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}

              <div className="input-field-block">
                <label htmlFor="ref-input-user">Username / Station ID</label>
                <div className="input-relative-wrap">
                  <User className="input-leading-icon" size={17} />
                  <input
                    id="ref-input-user"
                    type="email"
                    className="ref-input-style"
                    placeholder="Enter username or station ID"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="input-field-block">
                <label htmlFor="ref-input-pwd">Password</label>
                <div className="input-relative-wrap">
                  <Lock className="input-leading-icon" size={17} />
                  <input
                    id="ref-input-pwd"
                    type={showPassword ? 'text' : 'password'}
                    className="ref-input-style"
                    placeholder="Enter password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    className="pwd-eye-btn"
                    onClick={() => setShowPassword((prev) => !prev)}
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div className="options-row">
                <label className="remember-device-check">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                  />
                  <span>Remember this device</span>
                </label>
                <a
                  href="#forgot"
                  onClick={(e) => { e.preventDefault(); alert('Demo environment: Please use password "aurora2026"') }}
                  className="forgot-pwd-link"
                >
                  Forgot password?
                </a>
              </div>

              <button type="submit" className="enter-command-btn" disabled={isSubmitting}>
                <span>{isSubmitting ? 'AUTHENTICATING...' : 'ENTER COMMAND CENTER'}</span>
                {!isSubmitting && <ArrowRight size={17} />}
              </button>

              {/* Demo Credentials Box */}
              <div className="demo-access-box">
                <div className="demo-access-info">
                  <span className="demo-access-tag">
                    ⚙️ DEMO ACCESS
                  </span>
                  <div className="demo-access-line">
                    <span>Username:</span> <code>{DEMO_USER}</code>
                  </div>
                  <div className="demo-access-line">
                    <span>Password:</span> <code>{DEMO_PASS}</code>
                  </div>
                </div>
                <button type="button" className="autofill-btn" onClick={handleAutoFill}>
                  <User size={13} />
                  AUTO-FILL
                </button>
              </div>

              <div className="register-card-footer">
                <span>Don't have an account?</span>
                <a
                  href="#register"
                  onClick={(e) => { e.preventDefault(); alert('Demo environment: Bharati station account active.') }}
                >
                  Register
                </a>
              </div>
            </form>
          </div>
        </section>
      </main>
    </div>
  )
}
