import { useState } from 'react'
import { useAuth } from '../auth'

const DEMO = [
  ['admin@hospital.example.com', 'Admin'],
  ['doctor@hospital.example.com', 'Doctor'],
  ['reception@hospital.example.com', 'Reception'],
  ['analyst@hospital.example.com', 'Analyst'],
]

export default function Login() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(email, password)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login">
      <form className="card" onSubmit={submit}>
        <h1>🏥 Smart Hospital</h1>
        <p className="muted">Hospital management &amp; disease-risk prediction</p>
        <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
        {error && <p className="error">{error}</p>}
        <button disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        <div className="demo">
          <p className="muted">Demo accounts (password <code>Password123!</code>):</p>
          {DEMO.map(([em, label]) => (
            <button type="button" key={em} className="link" onClick={() => { setEmail(em); setPassword('Password123!') }}>{label}</button>
          ))}
        </div>
      </form>
    </div>
  )
}
