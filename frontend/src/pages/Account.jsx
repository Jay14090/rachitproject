import { useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { useForm } from '../hooks'

export default function Account() {
  const { user } = useAuth()
  const { values, bind, reset } = useForm({ current_password: '', new_password: '', confirm: '' })
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setDone(false)
    if (values.new_password !== values.confirm) return setError('New passwords do not match')
    try {
      await api.post('/auth/change-password', { current_password: values.current_password, new_password: values.new_password })
      reset()
      setDone(true)
    } catch (err) { setError(err.message) }
  }

  return (
    <>
      <h2>My account</h2>
      <section className="card">
        <p><b>{user.name}</b> · {user.email} · <span className="badge">{user.role}</span></p>
      </section>
      <form className="card formgrid" onSubmit={submit}>
        <h3 className="wide">Change password</h3>
        <label>Current password<input type="password" autoComplete="current-password" required {...bind('current_password')} /></label>
        <label>New password (min 8)<input type="password" autoComplete="new-password" required minLength={8} {...bind('new_password')} /></label>
        <label>Confirm new password<input type="password" autoComplete="new-password" required minLength={8} {...bind('confirm')} /></label>
        {error && <p className="error wide">{error}</p>}
        {done && <p className="wide" role="status">Password updated.</p>}
        <button>Update password</button>
      </form>
    </>
  )
}
