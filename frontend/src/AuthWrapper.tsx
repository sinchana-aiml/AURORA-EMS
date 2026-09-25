import { useState } from 'react'
import App from './App'
import AuthExperience from './AuthExperience'

export default function AuthWrapper() {
  const [authenticated, setAuthenticated] = useState<boolean>(() => {
    return sessionStorage.getItem('aurora_auth') === 'true'
  })

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
