import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import PredictionPanel from '../components/PredictionPanel'
import { useFetch, useForm } from '../hooks'

export default function PatientDetail() {
  const { id } = useParams()
  const { user } = useAuth()
  const clinical = ['admin', 'doctor'].includes(user.role)
  const { data: p, error, reload } = useFetch(() => api.get(`/patients/${id}`), [id])
  if (error) return <p className="error">{error}</p>
  if (!p) return <p>Loading…</p>

  return (
    <>
      <Link to="/patients">← Patients</Link>
      <h2>{p.name} <span className="muted">#{p.patient_id}</span></h2>
      <section className="card">
        <PatientProfile p={p} canEdit={['admin', 'reception'].includes(user.role)} onSaved={reload} />
      </section>
      {clinical ? (
        <>
          <PredictionPanel patientId={p.patient_id} age={p.age} />
          <Records patientId={p.patient_id} />
        </>
      ) : <p className="muted">Clinical records and predictions are visible to doctors and administrators only.</p>}
    </>
  )
}

function PatientProfile({ p, canEdit, onSaved }) {
  const [editing, setEditing] = useState(false)
  const { values, bind } = useForm({ contact: p.contact, address: p.address || '' })
  const [error, setError] = useState('')
  const save = async (e) => {
    e.preventDefault()
    try {
      await api.patch(`/patients/${p.patient_id}`, { contact: values.contact, address: values.address || null })
      setEditing(false)
      onSaved()
    } catch (err) { setError(err.message) }
  }
  if (!editing) {
    return (
      <div className="kv">
        <div><b>Age</b> {p.age} ({p.date_of_birth})</div><div><b>Gender</b> {p.gender}</div>
        <div><b>Contact</b> {p.contact}</div><div><b>Address</b> {p.address || '—'}</div>
        <div><b>Registered</b> {p.registration_date.slice(0, 10)}</div>
        {canEdit && <button className="link" onClick={() => setEditing(true)}>Edit contact details</button>}
      </div>
    )
  }
  return (
    <form className="formgrid" onSubmit={save}>
      <label>Contact<input {...bind('contact')} required minLength={5} /></label>
      <label>Address<input {...bind('address')} /></label>
      {error && <p className="error wide">{error}</p>}
      <div className="row"><button>Save</button><button type="button" className="link" onClick={() => setEditing(false)}>Cancel</button></div>
    </form>
  )
}

function Records({ patientId }) {
  const { data, reload } = useFetch(() => api.get(`/medical-records/patient/${patientId}`), [patientId])
  const { values, bind, reset } = useForm({ symptoms: '', notes: '', bp_systolic: '', weight_kg: '' })
  const [error, setError] = useState('')
  const submit = async (e) => {
    e.preventDefault()
    setError('')
    const measurements = {}
    if (values.bp_systolic) measurements.bp_systolic = Number(values.bp_systolic)
    if (values.weight_kg) measurements.weight_kg = Number(values.weight_kg)
    try {
      await api.post('/medical-records', {
        patient_id: patientId, symptoms: values.symptoms || null, notes: values.notes || null,
        measurements: Object.keys(measurements).length ? measurements : null,
      })
      reset()
      reload()
    } catch (err) { setError(err.message) }
  }
  return (
    <section className="card">
      <h3>Medical records</h3>
      <form className="formgrid" onSubmit={submit}>
        <label>Systolic BP<input type="number" {...bind('bp_systolic')} /></label>
        <label>Weight (kg)<input type="number" step="0.1" {...bind('weight_kg')} /></label>
        <label className="wide">Symptoms<input {...bind('symptoms')} /></label>
        <label className="wide">Notes<textarea rows={2} {...bind('notes')} /></label>
        {error && <p className="error wide">{error}</p>}
        <button>Add record</button>
      </form>
      {data && data.length === 0 && <p className="muted">No records yet.</p>}
      {data && data.map((r) => (
        <div key={r.record_id} className="record">
          <div className="muted">{r.created_at.replace('T', ' ').slice(0, 16)} · {r.doctor_name || 'Unassigned'}</div>
          {r.measurements && <div>{Object.entries(r.measurements).map(([k, v]) => `${k}: ${v}`).join(' · ')}</div>}
          {r.symptoms && <div><b>Symptoms:</b> {r.symptoms}</div>}
          {r.notes && <div><b>Notes:</b> {r.notes}</div>}
        </div>
      ))}
    </section>
  )
}
