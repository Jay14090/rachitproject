import { useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { useFetch, useForm } from '../hooks'

export default function Users() {
  const { user: me } = useAuth()
  const { data, error, reload } = useFetch(() => api.get('/users'))
  const { data: doctors } = useFetch(() => api.get('/doctors'))
  const { values, bind, reset } = useForm({ name: '', email: '', password: '', role: 'reception', doctor_id: '' })
  const [formError, setFormError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setFormError('')
    try {
      await api.post('/users', { ...values, doctor_id: values.doctor_id ? Number(values.doctor_id) : null })
      reset()
      reload()
    } catch (err) { setFormError(err.message) }
  }
  const toggle = async (u) => {
    try { await api.patch(`/users/${u.user_id}`, { status: u.status === 'active' ? 'inactive' : 'active' }); reload() }
    catch (err) { setFormError(err.message) }
  }

  return (
    <>
      <h2>Users</h2>
      <form className="card formgrid" onSubmit={submit}>
        <label>Name<input {...bind('name')} required minLength={2} /></label>
        <label>Email<input type="email" {...bind('email')} required /></label>
        <label>Password (min 8)<input type="password" {...bind('password')} required minLength={8} /></label>
        <label>Role
          <select {...bind('role')}><option value="admin">admin</option><option value="doctor">doctor</option><option value="reception">reception</option><option value="analyst">analyst</option></select>
        </label>
        {values.role === 'doctor' && (
          <label>Linked doctor profile
            <select {...bind('doctor_id')}><option value="">None</option>
              {doctors?.map((d) => <option key={d.doctor_id} value={d.doctor_id}>{d.name}</option>)}
            </select>
          </label>
        )}
        {formError && <p className="error wide">{formError}</p>}
        <button>Create user</button>
      </form>
      {error && <p className="error">{error}</p>}
      <table>
        <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th /></tr></thead>
        <tbody>
          {data?.map((u) => (
            <tr key={u.user_id}>
              <td>{u.name}</td><td>{u.email}</td><td><span className="badge">{u.role}</span></td>
              <td><span className={`pill st-${u.status === 'active' ? 'scheduled' : 'cancelled'}`}>{u.status}</span></td>
              <td>{u.user_id !== me.user_id && <button className="link" onClick={() => toggle(u)}>{u.status === 'active' ? 'Deactivate' : 'Activate'}</button>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
