import { useState } from 'react'
import { api } from '../api'
import { useFetch, useForm } from '../hooks'

const today = () => new Date().toISOString().slice(0, 10)

export default function Appointments() {
  const [filters, setFilters] = useState({ date: '', status: '' })
  const { data, error, loading, reload } = useFetch(() => api.get('/appointments', filters), [filters.date, filters.status])
  const [showForm, setShowForm] = useState(false)
  const [actionError, setActionError] = useState('')

  const act = async (id, body) => {
    setActionError('')
    try { await api.patch(`/appointments/${id}`, body); reload() } catch (err) { setActionError(err.message) }
  }
  const reschedule = (a) => {
    const d = window.prompt('New date (YYYY-MM-DD)', a.date)
    if (!d) return
    const t = window.prompt('New time (HH:MM)', a.time.slice(0, 5))
    if (!t) return
    act(a.appointment_id, { date: d, time: t.length === 5 ? `${t}:00` : t })
  }

  return (
    <>
      <div className="row between">
        <h2>Appointments</h2>
        <button onClick={() => setShowForm((s) => !s)}>{showForm ? 'Close' : '+ New appointment'}</button>
      </div>
      {showForm && <AppointmentForm onDone={() => { setShowForm(false); reload() }} />}
      <div className="row">
        <label>Date <input type="date" value={filters.date} onChange={(e) => setFilters({ ...filters, date: e.target.value })} /></label>
        <label>Status
          <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="">All</option><option>scheduled</option><option>completed</option><option>cancelled</option>
          </select>
        </label>
      </div>
      {(error || actionError) && <p className="error">{error || actionError}</p>}
      {loading ? <p>Loading…</p> : (
        <table>
          <thead><tr><th>Date</th><th>Time</th><th>Patient</th><th>Doctor</th><th>Purpose</th><th>Status</th><th /></tr></thead>
          <tbody>
            {data.map((a) => (
              <tr key={a.appointment_id}>
                <td>{a.date}</td><td>{a.time.slice(0, 5)}</td><td>{a.patient_name}</td><td>{a.doctor_name}</td>
                <td>{a.purpose || '—'}</td><td><span className={`pill st-${a.status}`}>{a.status}</span></td>
                <td className="actions">
                  {a.status === 'scheduled' && <>
                    <button className="link" onClick={() => act(a.appointment_id, { status: 'completed' })}>Complete</button>
                    <button className="link" onClick={() => reschedule(a)}>Reschedule</button>
                    <button className="link danger" onClick={() => window.confirm('Cancel this appointment?') && act(a.appointment_id, { status: 'cancelled' })}>Cancel</button>
                  </>}
                </td>
              </tr>
            ))}
            {data.length === 0 && <tr><td colSpan="7" className="muted">No appointments match.</td></tr>}
          </tbody>
        </table>
      )}
    </>
  )
}

function AppointmentForm({ onDone }) {
  const { data: patients } = useFetch(() => api.get('/patients', { limit: 200 }))
  const { data: doctors } = useFetch(() => api.get('/doctors', { active_only: true }))
  const { values, bind, setValues } = useForm({ patient_id: '', doctor_id: '', date: today(), time: '', purpose: '' })
  const [error, setError] = useState('')
  const ready = values.doctor_id && values.date
  const { data: slots, loading: slotsLoading } = useFetch(
    () => (ready ? api.get(`/doctors/${values.doctor_id}/slots`, { date: values.date }) : Promise.resolve(null)),
    [values.doctor_id, values.date],
  )
  const slotList = slots?.slots ?? []
  // Doctors without a published schedule return no slots; fall back to manual entry only then.
  const { data: sched } = useFetch(
    () => (values.doctor_id ? api.get(`/doctors/${values.doctor_id}/availability`) : Promise.resolve(null)),
    [values.doctor_id],
  )
  const restricted = !!sched && sched.length > 0

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/appointments', {
        patient_id: Number(values.patient_id), doctor_id: Number(values.doctor_id), date: values.date,
        time: `${values.time}:00`, purpose: values.purpose || null,
      })
      onDone()
    } catch (err) { setError(err.message) }
  }
  return (
    <form className="card formgrid" onSubmit={submit}>
      <label>Patient
        <select {...bind('patient_id')} required>
          <option value="">Select…</option>
          {patients?.map((p) => <option key={p.patient_id} value={p.patient_id}>{p.name} (#{p.patient_id})</option>)}
        </select>
      </label>
      <label>Doctor
        <select name="doctor_id" value={values.doctor_id} required
          onChange={(e) => setValues({ ...values, doctor_id: e.target.value, time: '' })}>
          <option value="">Select…</option>
          {doctors?.map((d) => <option key={d.doctor_id} value={d.doctor_id}>{d.name} — {d.department.department_name}</option>)}
        </select>
      </label>
      <label>Date
        <input type="date" min={today()} name="date" value={values.date} required
          onChange={(e) => setValues({ ...values, date: e.target.value, time: '' })} />
      </label>
      {restricted || slotList.length ? (
        <label>Available time
          <select {...bind('time')} required>
            <option value="">{slotsLoading ? 'Loading…' : slotList.length ? 'Select a slot…' : 'No free slots that day'}</option>
            {slotList.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
      ) : (
        <label>Time<input type="time" {...bind('time')} required /></label>
      )}
      <label className="wide">Purpose<input {...bind('purpose')} /></label>
      {error && <p className="error wide">{error}</p>}
      <button>Book appointment</button>
    </form>
  )
}
