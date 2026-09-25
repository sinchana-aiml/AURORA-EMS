import { Billboard, Html, Line, Sparkles, Text } from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'
import React, { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { AlertCircle, ArrowRight, Eye, EyeOff, Lock, Mail, ShieldCheck, Sparkles as SparklesIcon, Zap } from 'lucide-react'

interface AuthExperienceProps {
  onLoginSuccess: () => void
}

const DEMO_USER = 'operator@aurora.ems'
const DEMO_PASS = 'aurora2026'

const FALLING_WORDS = [
  'AURORA', 'EMS', 'PREDICT', 'SIMULATE', 'OPTIMIZE', 'PROTECT',
  'ENERGY', 'AI', 'POLAR', 'STATION', 'ANTARCTICA', 'DIGITAL TWIN',
  'FORECAST', 'BHARATI'
]

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

// 3D Background Aurora Ribbons
function AuroraRibbons({ stage }: { stage: 'intro' | 'falling' | 'login' | 'authenticating' }) {
  const group = useRef<THREE.Group>(null)
  const ribbons = useMemo(() => [-.5, -.2, .25, .55].map((offset) => Array.from({ length: 28 }, (_, index) => {
    const t = index / 27
    return new THREE.Vector3(-6 + t * 12, 1.8 + Math.sin(t * Math.PI * 2.2 + offset * 4) * .35 + offset * .2, -4 + Math.cos(t * Math.PI * 1.4) * .6)
  })), [])

  useFrame(({ clock }) => {
    if (!group.current) return
    group.current.position.y = Math.sin(clock.getElapsedTime() * .08) * .15
    group.current.rotation.z = Math.sin(clock.getElapsedTime() * .04) * .03
  })

  const opacity = stage === 'authenticating' ? .45 : stage === 'intro' ? .22 : .16
  return (
    <group ref={group}>
      {ribbons.map((points, index) => (
        <Line
          key={index}
          points={points}
          color={index % 3 === 1 ? '#55e9c1' : index % 3 === 2 ? '#38bdf8' : '#70d9de'}
          transparent
          opacity={opacity}
          lineWidth={index === 1 ? 1.4 : .8}
        />
      ))}
    </group>
  )
}

// 3D Falling Text Mesh Cloud
function Falling3DTextCloud({ stage, reduced }: { stage: 'intro' | 'falling' | 'login' | 'authenticating'; reduced: boolean }) {
  const items = useMemo(() => FALLING_WORDS.map((word, i) => ({
    word,
    position: new THREE.Vector3(
      ((i * 37) % 9 - 4.5) * 1.2,
      ((i * 53) % 7 - 3.5) * 1.1,
      -2 - (i % 8) * 1.8
    ),
    speed: 0.6 + (i % 5) * 0.25,
    rotSpeed: (i % 4 - 2) * 0.008,
    color: i % 2 === 0 ? '#38bdf8' : '#55e9c1'
  })), [])

  const groupRef = useRef<THREE.Group>(null)

  useFrame((_, delta) => {
    if (!groupRef.current || reduced) return
    items.forEach((item, index) => {
      if (stage === 'falling') {
        item.position.y -= item.speed * delta * 1.8
        if (item.position.y < -5) item.position.y = 5
      }
    })
  })

  if (stage === 'intro') return null

  return (
    <group ref={groupRef}>
      {items.map((item, index) => (
        <Billboard key={index} position={item.position}>
          <Text
            fontSize={stage === 'falling' ? 0.45 : 0.25}
            color={item.color}
            fillOpacity={stage === 'falling' ? 0.85 : 0.2}
            letterSpacing={0.08}
          >
            {item.word}
          </Text>
        </Billboard>
      ))}
    </group>
  )
}

// Holographic 3D Telemetry Overlay Labels
function HolographicTelemetry({ stage }: { stage: 'intro' | 'falling' | 'login' | 'authenticating' }) {
  if (stage !== 'login') return null

  return (
    <group>
      <Billboard position={[-2.9, 1.85, 0]}>
        <Html transform distanceFactor={2.4}>
          <div className="holo-telemetry-tag">
            <i /> BHARATI STATION — ANTARCTICA
          </div>
        </Html>
      </Billboard>

      <Billboard position={[2.9, 1.85, 0]}>
        <Html transform distanceFactor={2.4}>
          <div className="holo-telemetry-tag">
            <i /> SYSTEM ONLINE • TELEMETRY 100%
          </div>
        </Html>
      </Billboard>

      <Billboard position={[-2.9, -1.85, 0]}>
        <Html transform distanceFactor={2.4}>
          <div className="holo-telemetry-tag">
            <i /> ENERGY GRID STABLE • 600 kWh SOC
          </div>
        </Html>
      </Billboard>

      <Billboard position={[2.9, -1.85, 0]}>
        <Html transform distanceFactor={2.4}>
          <div className="holo-telemetry-tag">
            <i /> AI FORECAST READY • P50 LOAD OPTIMIZED
          </div>
        </Html>
      </Billboard>
    </group>
  )
}

// Main 3D Scene Controller
function SceneController({ stage, reduced }: { stage: 'intro' | 'falling' | 'login' | 'authenticating'; reduced: boolean }) {
  useFrame(({ camera }) => {
    if (reduced) {
      camera.position.set(0, 0, 4.5)
      return
    }

    if (stage === 'intro') {
      camera.position.z = THREE.MathUtils.lerp(camera.position.z, 6, 0.05)
    } else if (stage === 'falling') {
      camera.position.z = THREE.MathUtils.lerp(camera.position.z, 1.5, 0.04)
    } else if (stage === 'login') {
      camera.position.z = THREE.MathUtils.lerp(camera.position.z, 4.5, 0.06)
      camera.position.y = THREE.MathUtils.lerp(camera.position.y, 0, 0.05)
    } else if (stage === 'authenticating') {
      camera.position.z = THREE.MathUtils.lerp(camera.position.z, 0.5, 0.08)
    }
  })

  return (
    <>
      <ambientLight intensity={0.4} />
      <directionalLight position={[-3, 2, 4]} intensity={1.2} color="#d2efff" />
      <Sparkles count={80} scale={8} size={1.2} speed={0.04} color="#38bdf8" />
      <AuroraRibbons stage={stage} />
      <Falling3DTextCloud stage={stage} reduced={reduced} />
      <HolographicTelemetry stage={stage} />
    </>
  )
}

export default function AuthExperience({ onLoginSuccess }: AuthExperienceProps) {
  const [stage, setStage] = useState<'intro' | 'falling' | 'login' | 'authenticating'>('intro')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const reducedMotion = useReducedMotion()

  // Automated 3-Stage Transition Timeline
  useEffect(() => {
    if (reducedMotion) {
      setStage('login')
      return
    }

    const timer1 = setTimeout(() => {
      setStage('falling')
    }, 2800)

    const timer2 = setTimeout(() => {
      setStage('login')
    }, 5000)

    return () => {
      clearTimeout(timer1)
      clearTimeout(timer2)
    }
  }, [reducedMotion])

  const handleSkipIntro = () => {
    setStage('login')
  }

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
      setStage('authenticating')
      setTimeout(() => {
        onLoginSuccess()
      }, 700)
    } else {
      setError('Invalid username or password.')
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-view-root">
      {/* 3D Canvas Background & Falling Text Field */}
      <div className="auth-canvas-container">
        <Canvas camera={{ position: [0, 0, 6], fov: 48 }} dpr={[1, 1.5]} gl={{ antialias: true }}>
          <color attach="background" args={['#020914']} />
          <fog attach="fog" args={['#020914', 4, 10]} />
          <SceneController stage={stage} reduced={reducedMotion} />
        </Canvas>
      </div>

      {/* Stage 1: AURORA INTRO Overlay */}
      {stage === 'intro' && (
        <div className="intro-stage-overlay">
          <div className="intro-badge">
            <i />
            <span>AURORA-EMS POLAR DIGITAL TWIN</span>
          </div>

          <h1 className="intro-title">AURORA-EMS</h1>

          <p className="intro-description">
            AI-Driven Energy Management System for Polar Research Stations
          </p>

          <div className="intro-taglines">
            <span>PREDICT</span>
            <span>SIMULATE</span>
            <span>OPTIMIZE</span>
            <span>PROTECT</span>
          </div>
        </div>
      )}

      {/* Stage 3: LOGIN COMMAND CENTER Overlay */}
      {(stage === 'login' || stage === 'authenticating') && (
        <div className={`login-stage-container ${stage === 'authenticating' ? 'login-success-zoom' : ''}`}>
          <div className="login-card-panel">
            <div className="login-card-header">
              <span className="brand-icon">◆</span>
              <h2>AURORA-EMS</h2>
              <p>POLAR ENERGY INTELLIGENCE</p>
            </div>

            {/* Quick Demo Credentials Autofill Banner */}
            <div className="demo-hint-banner">
              <div className="demo-hint-text">
                Demo Operator: <b>{DEMO_USER}</b> / <b>{DEMO_PASS}</b>
              </div>
              <button type="button" className="autofill-action-btn" onClick={handleAutoFill}>
                Auto-fill
              </button>
            </div>

            <form className="login-form" onSubmit={handleSubmit}>
              {error && (
                <div className="error-alert-banner">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}

              <div className="form-field">
                <label htmlFor="input-username">Username / Station ID</label>
                <div className="input-rel-wrap">
                  <Mail className="input-icon" size={17} />
                  <input
                    id="input-username"
                    type="email"
                    className="form-input"
                    placeholder="operator@aurora.ems"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="form-field">
                <label htmlFor="input-password">Password</label>
                <div className="input-rel-wrap">
                  <Lock className="input-icon" size={17} />
                  <input
                    id="input-password"
                    type={showPassword ? 'text' : 'password'}
                    className="form-input"
                    placeholder="••••••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    className="toggle-pwd-btn"
                    onClick={() => setShowPassword((prev) => !prev)}
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div className="form-row-options">
                <label className="remember-check">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                  />
                  <span>Remember this device</span>
                </label>
                <a href="#forgot" onClick={(e) => { e.preventDefault(); alert('Demo environment: Please use password "aurora2026"') }} className="forgot-link">
                  Forgot password?
                </a>
              </div>

              <button type="submit" className="login-submit-btn" disabled={isSubmitting}>
                <span>{isSubmitting ? 'AUTHENTICATING...' : 'ENTER COMMAND CENTER'}</span>
                {!isSubmitting && <ArrowRight size={17} />}
              </button>

              <div className="register-footer">
                <span>Don't have an account?</span>
                <a href="#register" onClick={(e) => { e.preventDefault(); alert('Demo environment: Bharati station account active.') }}>
                  Register
                </a>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Skip Intro Button */}
      {stage !== 'login' && stage !== 'authenticating' && (
        <button className="skip-intro-btn" onClick={handleSkipIntro}>
          <span>SKIP INTRO</span>
          <ArrowRight size={13} />
        </button>
      )}
    </div>
  )
}
