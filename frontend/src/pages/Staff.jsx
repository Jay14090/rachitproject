import { useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { useFetch, useForm } from '../hooks'

export default function Staff() {
  const { user } = useAuth()
  const isAdmin = user.role === 'admin'
  const depts = useFetch(() => api.get('/departments'))
  const docs = useFetch(() => api.get('/doctors'))
  const reloadAll = () => { depts.reload(); docs.reload() }
  const [scheduleFor, setScheduleFor] = useState(null)

  return (
    <>
      <h2>Doctors &amp; Departments</h2>
      <div className="grid2">
        <section className="card">
          <h3>Departments</h3>
          <ul className="plain">
            {depts.data?.map((d) => (
              <li key={d.department_id}><b>{d.department_name}</b> <span className="muted">{d.description}</span></li>
            ))}
          </ul>
          {isAdmin && <DepartmentForm onDone={reloadAll} />}
        </section>
        <section className="card">
          <h3>Doctors</h3>
          <table>
            <thead><tr><th>Name</th><th>Specialization</th><th>Department</th><th>Status</th>{isAdmin && <th />}</tr></thead>
            <tbody>
              {docs.data?.map((d) => (
                <tr key={d.doctor_id}>
                  <td>{d.name}</td><td>{d.specialization}</td><td>{d.department.department_name}</td>
                  <td><span className={`pill st-${d.status === 'active' ? 'scheduled' : 'cancelled'}`}>{d.status}</span></td>
                  {isAdmin && <td className="actions"><button className="link" onClick={() => setScheduleFor(scheduleFor === d.doctor_id ? null : d.doctor_id)}>Schedule</button><button className="link" onClick={async () => {
                    await api.patch(`/doctors/${d.doctor_id}`, { status: d.status === 'active' ? 'inactive' : 'active' })
                    reloadAll()
                  }}>{d.status === 'active' ? 'Deactivate' : 'Activate'}</button></td>}
                </tr>
              ))}
            </tbody>
          </table>
          {scheduleFor && <ScheduleEditor key={scheduleFor} doctor={docs.data.find((d) => d.doctor_id === scheduleFor)} onClose={() => setScheduleFor(null)} />}
          {isAdmin && depts.data && <DoctorForm departments={depts.data} onDone={reloadAll} />}
        </section>
      </div>
    </>
  )
}

function DepartmentForm({ onDone }) {
  const { values, bind, reset } = useForm({ department_name: '', description: '' })
  const [error, setError] = useState('')
  const submit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/departments', { department_name: values.department_name, description: values.description || null })
      reset()
      onDone()
    } catch (err) { setError(err.message) }
  }
  return (
    <form className="formgrid" onSubmit={submit}>
      <label>New department<input {...bind('department_name')} required minLength={2} /></label>
      <label>Description<input {...bind('description')} /></label>
      {error && <p className="error wide">{error}</p>}
      <button>Add department</button>
    </form>
  )
}

function DoctorForm({ departments, onDone }) {
  const { values, bind, reset } = useForm({ name: '', specialization: '', department_id: '' })
  const [error, setError] = useState('')
  const submit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/doctors', { ...values, department_id: Number(values.department_id) })
      reset()
      onDone()
    } catch (err) { setError(err.message) }
  }
  return (
    <form className="formgrid" onSubmit={submit}>
      <label>Name<input {...bind('name')} required minLength={2} /></label>
      <label>Specialization<input {...bind('specialization')} required minLength={2} /></label>
      <label>Department
        <select {...bind('department_id')} required>
          <option value="">Select…</option>
          {departments.map((d) => <option key={d.department_id} value={d.department_id}>{d.department_name}</option>)}
        </select>
      </label>
      {error && <p className="error wide">{error}</p>}
      <button>Add doctor</button>
    </form>
  )
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function ScheduleEditor({ doctor, onClose }) {
  const { data, loading } = useFetch(() => api.get(`/doctors/${doctor.doctor_id}/availability`), [doctor.doctor_id])
  const [rows, setRows] = useState(null)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const current = rows ?? (data ? data.map((w) => ({ ...w, start_time: w.start_time.slice(0, 5), end_time: w.end_time.slice(0, 5) })) : [])
  const update = (i, patch) => setRows(current.map((r, j) => (j === i ? { ...r, ...patch } : r)))
  const save = async () => {
    setError(''); setMsg('')
    try {
      await api.put(`/doctors/${doctor.doctor_id}/availability`,
        current.map((r) => ({ weekday: Number(r.weekday), start_time: `${r.start_time}:00`, end_time: `${r.end_time}:00` })))
      setMsg('Schedule saved'); setRows(null)
    } catch (err) { setError(err.message) }
  }
  if (loading) return <p>Loading…</p>
  return (
    <div className="card">
      <div className="row between"><h4>Weekly schedule — {doctor.name}</h4><button className="link" onClick={onClose}>Close</button></div>
      <p className="muted">30-minute slots inside these windows. No windows = no restriction on bookings.</p>
      {current.map((r, i) => (
        <div className="row" key={i}>
          <select value={r.weekday} onChange={(e) => update(i, { weekday: e.target.value })}>{DAYS.map((d, n) => <option key={d} value={n}>{d}</option>)}</select>
          <input type="time" value={r.start_time} onChange={(e) => update(i, { start_time: e.target.value })} />
          <span>to</span>
          <input type="time" value={r.end_time} onChange={(e) => update(i, { end_time: e.target.value })} />
          <button type="button" className="link danger" onClick={() => setRows(current.filter((_, j) => j !== i))}>Remove</button>
        </div>
      ))}
      <div className="row">
        <button type="button" className="link" onClick={() => setRows([...current, { weekday: 0, start_time: '09:00', end_time: '12:00' }])}>+ Add window</button>
        <button type="button" onClick={save}>Save schedule</button>
      </div>
      {error && <p className="error">{error}</p>}
      {msg && <p className="muted">{msg}</p>}
    </div>
  )
}
