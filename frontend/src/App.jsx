import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { NAV, useAuth } from './auth'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Patients from './pages/Patients'
import PatientDetail from './pages/PatientDetail'
import Appointments from './pages/Appointments'
import Staff from './pages/Staff'
import Models from './pages/Models'
import Users from './pages/Users'
import AuditLog from './pages/AuditLog'

function Guard({ roles, children }) {
  const { user } = useAuth()
  return roles.includes(user.role) ? children : <p className="error">You do not have access to this page.</p>
}

function Shell() {
  const { user, logout } = useAuth()
  return (
    <div className="shell">
      <aside>
        <h1>🏥 Smart Hospital</h1>
        <nav>
          {NAV.filter((n) => n.roles.includes(user.role)).map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === '/'}>{n.label}</NavLink>
          ))}
        </nav>
        <div className="who">
          <strong>{user.name}</strong>
          <span className="badge">{user.role}</span>
          <button className="link" onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/patients" element={<Guard roles={['admin', 'doctor', 'reception']}><Patients /></Guard>} />
          <Route path="/patients/:id" element={<Guard roles={['admin', 'doctor', 'reception']}><PatientDetail /></Guard>} />
          <Route path="/appointments" element={<Guard roles={['admin', 'doctor', 'reception']}><Appointments /></Guard>} />
          <Route path="/staff" element={<Guard roles={['admin', 'doctor', 'reception']}><Staff /></Guard>} />
          <Route path="/models" element={<Guard roles={['admin', 'doctor', 'analyst']}><Models /></Guard>} />
          <Route path="/users" element={<Guard roles={['admin']}><Users /></Guard>} />
          <Route path="/audit" element={<Guard roles={['admin']}><AuditLog /></Guard>} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  const { user, loading } = useAuth()
  if (loading) return <p className="center">Loading…</p>
  return user ? <Shell /> : (
    <Routes>
      <Route path="*" element={<Login />} />
    </Routes>
  )
}
