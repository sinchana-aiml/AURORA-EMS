import React, { useState } from 'react'
import { Activity, AlertCircle, ArrowLeft, ArrowRight, Eye, EyeOff, Lock, Mail, ShieldCheck, Sparkles, Zap } from 'lucide-react'

interface AuthExperienceProps {
  onLoginSuccess: () => void
}

const DEMO_USER = 'operator@aurora.ems'
const DEMO_PASS = 'aurora2026'

export default function AuthExperience({ onLoginSuccess }: AuthExperienceProps) {
  const [view, setView] = useState<'splash' | 'login'>('splash')
  const [isSliding, setIsSliding] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleTransitionToLogin = () => {
    setIsSliding(true)
    setTimeout(() => {
      setView('login')
      setIsSliding(false)
    }, 250)
  }

  const handleTransitionToSplash = () => {
    setIsSliding(true)
    setTimeout(() => {
      setView('splash')
      setIsSliding(false)
    }, 250)
  }

  const handleAutoFill = () => {
    setUsername(DEMO_USER)
    setPassword(DEMO_PASS)
    setError(null)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    setTimeout(() => {
      if (username.trim().toLowerCase() === DEMO_USER && password === DEMO_PASS) {
        onLoginSuccess()
      } else {
        setError('Invalid username or password.')
        setIsSubmitting(false)
      }
    }, 600)
  }

  return (
    <div className="auth-view-root">
      <div className="auth-card-stage">
        {view === 'splash' ? (
          <div className={`auth-card ${isSliding ? 'auth-slide-exit' : 'auth-slide-enter'}`}>
            <div className="splash-brand-badge">
              <i />
              <span>AURORA-EMS DEMO & PROTOTYPE</span>
            </div>

            <div className="splash-header">
              <h1>AURORA-EMS</h1>
              <p>Polar Station Energy Command Center</p>
            </div>

            <div className="splash-features">
              <div className="splash-feature-item">
                <div className="splash-feature-icon">
                  <Activity size={18} />
                </div>
                <div>
                  <b>Bharati Research Station Twin</b>
                  <div style={{ fontSize: '0.76rem', color: '#64748b' }}>Real-time simulated telemetry & load metrics</div>
                </div>
              </div>

              <div className="splash-feature-item">
                <div className="splash-feature-icon">
                  <Sparkles size={18} />
                </div>
                <div>
                  <b>AI Forecast & Dispatch Engine</b>
                  <div style={{ fontSize: '0.76rem', color: '#64748b' }}>Optimized battery & generator microgrid control</div>
                </div>
              </div>

              <div className="splash-feature-item">
                <div className="splash-feature-icon">
                  <ShieldCheck size={18} />
                </div>
                <div>
                  <b>Resilience & Contingency Management</b>
                  <div style={{ fontSize: '0.76rem', color: '#64748b' }}>Polar weather risk evaluation & turbine safety</div>
                </div>
              </div>
            </div>

            <button className="auth-primary-btn" onClick={handleTransitionToLogin}>
              <span>ENTER EMS OPERATIONS COMMAND</span>
              <ArrowRight size={18} />
            </button>

            <div className="splash-footer-note">
              [PROTOTYPE NOTE] Demo operator credentials provided on next screen.
            </div>
          </div>
        ) : (
          <div className={`auth-card ${isSliding ? 'auth-slide-exit' : 'auth-slide-enter'}`}>
            <div className="login-header">
              <h2>Operator Login</h2>
              <p>Enter research operator credentials to access Bharati station command</p>
            </div>

            <div className="demo-credentials-box">
              <div className="demo-credentials-header">
                <span className="demo-tag">
                  <Zap size={13} />
                  DEMO / PROTOTYPE CREDENTIALS
                </span>
                <button type="button" className="autofill-btn" onClick={handleAutoFill}>
                  Auto-fill
                </button>
              </div>

              <div className="demo-credentials-list">
                <div>
                  <span>Username / Email</span>
                  <code>{DEMO_USER}</code>
                </div>
                <div>
                  <span>Password</span>
                  <code>{DEMO_PASS}</code>
                </div>
              </div>
            </div>

            <form className="auth-form" onSubmit={handleSubmit}>
              {error && (
                <div className="auth-error-banner">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}

              <div className="auth-input-group">
                <label htmlFor="auth-username">Operator ID / Email</label>
                <div className="auth-input-wrapper">
                  <Mail className="auth-input-icon" size={17} />
                  <input
                    id="auth-username"
                    type="email"
                    className="auth-input"
                    placeholder="operator@aurora.ems"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="auth-input-group">
                <label htmlFor="auth-password">Security Access Key</label>
                <div className="auth-input-wrapper">
                  <Lock className="auth-input-icon" size={17} />
                  <input
                    id="auth-password"
                    type={showPassword ? 'text' : 'password'}
                    className="auth-input"
                    placeholder="••••••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    className="auth-toggle-pwd"
                    onClick={() => setShowPassword((prev) => !prev)}
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button type="submit" className="auth-primary-btn" disabled={isSubmitting}>
                <span>{isSubmitting ? 'AUTHENTICATING...' : 'AUTHENTICATE & ENTER COMMAND'}</span>
                {!isSubmitting && <ArrowRight size={18} />}
              </button>

              <div className="auth-secondary-actions">
                <button type="button" className="auth-back-link" onClick={handleTransitionToSplash}>
                  <ArrowLeft size={14} />
                  <span>Back to opening screen</span>
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  )
}
