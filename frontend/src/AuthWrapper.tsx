import { useEffect, useState } from 'react'
import App from './App'
import AuthExperience from './AuthExperience'

export default function AuthWrapper() {
  const [authenticated, setAuthenticated] = useState<boolean>(() => {
    return sessionStorage.getItem('aurora_auth') === 'true'
  })

  useEffect(() => {
    const handleLogoutEvent = () => {
      sessionStorage.removeItem('aurora_auth')
      sessionStorage.removeItem('aurora_auth_user')
      setAuthenticated(false)
    }

    window.addEventListener('aurora-logout', handleLogoutEvent)
    return () => window.removeEventListener('aurora-logout', handleLogoutEvent)
  }, [])

  const handleLoginSuccess = () => {
    sessionStorage.setItem('aurora_auth', 'true')
    sessionStorage.setItem('aurora_auth_user', 'operator@aurora.ems')
    setAuthenticated(true)
  }

  if (authenticated) {
    return <App />
  }

  return <AuthExperience onLoginSuccess={handleLoginSuccess} />
}
