import { createContext, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken } from './api'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

// Mirrors the backend's role matrix so the UI hides what the API would reject anyway.
export const NAV = [
  { to: '/', label: 'Dashboard', roles: ['admin', 'doctor', 'reception', 'analyst'] },
  { to: '/patients', label: 'Patients', roles: ['admin', 'doctor', 'reception'] },
  { to: '/appointments', label: 'Appointments', roles: ['admin', 'doctor', 'reception'] },
  { to: '/staff', label: 'Doctors & Departments', roles: ['admin', 'doctor', 'reception'] },
  { to: '/models', label: 'ML Models', roles: ['admin', 'doctor', 'analyst'] },
  { to: '/users', label: 'Users', roles: ['admin'] },
  { to: '/audit', label: 'Audit Log', roles: ['admin'] },
  { to: '/account', label: 'My account', roles: ['admin', 'doctor', 'reception', 'analyst'] },
]

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!getToken())

  useEffect(() => {
    if (!getToken()) return
    api.get('/auth/me').then(setUser).catch(() => setToken(null)).finally(() => setLoading(false))
  }, [])

  const login = async (email, password) => {
    const res = await api.post('/auth/login', { email, password })
    setToken(res.access_token)
    setUser(res.user)
  }
  const logout = () => {
    setToken(null)
    setUser(null)
  }
  return <AuthCtx.Provider value={{ user, loading, login, logout }}>{children}</AuthCtx.Provider>
}
