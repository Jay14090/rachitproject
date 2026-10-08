import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import { useAuth } from '../auth'
import { useFetch, useForm } from '../hooks'

const LEVEL_COLOR = { low: '#2e9e5b', moderate: '#e0a100', high: '#d64545' }

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
          <Prediction patientId={p.patient_id} age={p.age} />
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

const FIELDS = [
  ['pregnancies', 'Pregnancies', '1', 0, 20],
  ['glucose', 'Glucose (mg/dL)', '1', 40, 400],
  ['blood_pressure', 'Diastolic BP (mm Hg)', '1', 30, 200],
  ['skin_thickness', 'Skin thickness (mm)', '1', 0, 100],
  ['insulin', 'Insulin (mu U/ml, 0 = unknown)', '1', 0, 900],
  ['bmi', 'BMI', '0.1', 10, 70],
  ['diabetes_pedigree', 'Diabetes pedigree function', '0.001', 0, 3],
  ['age', 'Age', '1', 1, 120],
]

function Prediction({ patientId, age }) {
  const { data: history, reload } = useFetch(() => api.get(`/predictions/${patientId}`), [patientId])
  const { values, bind } = useForm({
    pregnancies: 0, glucose: '', blood_pressure: '', skin_thickness: 20, insulin: 0, bmi: '', diabetes_pedigree: 0.5, age,
  })
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const body = { patient_id: patientId }
      FIELDS.forEach(([k]) => { body[k] = Number(values[k]) })
      setResult(await api.post('/predict/diabetes', body))
      reload()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return (
    <section className="card">
      <h3>Diabetes risk prediction</h3>
      <form className="formgrid" onSubmit={submit}>
        {FIELDS.map(([k, label, step, min, max]) => (
          <label key={k}>{label}<input type="number" step={step} min={min} max={max} required {...bind(k)} /></label>
        ))}
        <button disabled={busy}>{busy ? 'Calculating…' : 'Estimate risk'}</button>
      </form>
      {error && <p className="error">{error}</p>}
      {result && <PredictionResult r={result} />}
      <h4>History</h4>
      {history && history.length === 0 && <p className="muted">No predictions yet.</p>}
      {history && history.length > 0 && (
        <table>
          <thead><tr><th>Date</th><th>Risk</th><th>Level</th><th>Model</th></tr></thead>
          <tbody>
            {history.map((h) => (
              <tr key={h.prediction_id} onClick={() => setResult(h)} className="clickable">
                <td>{h.created_at.replace('T', ' ').slice(0, 16)}</td>
                <td>{(h.risk_score * 100).toFixed(1)}%</td>
                <td><span className="pill" style={{ background: LEVEL_COLOR[h.risk_level] }}>{h.risk_level}</span></td>
                <td className="muted">{h.model_version}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

function PredictionResult({ r }) {
  const chart = r.explanation.map((e) => ({ name: `${e.feature} = ${e.value}`, impact: Math.round(e.impact * 1000) / 10 }))
  return (
    <div className="result" style={{ borderColor: LEVEL_COLOR[r.risk_level] }}>
      <div className="row between">
        <div>
          <div className="big" style={{ color: LEVEL_COLOR[r.risk_level] }}>{(r.risk_score * 100).toFixed(1)}% — {r.risk_level} risk</div>
          <div className="muted">Model {r.model_version} · {r.created_at.replace('T', ' ').slice(0, 16)}</div>
        </div>
      </div>
      <h4>What drove this estimate</h4>
      <p className="muted">Change in predicted risk (percentage points) vs. an average value for each factor. Positive = pushes risk up.</p>
      <ResponsiveContainer width="100%" height={Math.max(220, chart.length * 30)}>
        <BarChart data={chart} layout="vertical" margin={{ left: 120 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" unit=" pp" />
          <YAxis type="category" dataKey="name" width={180} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="impact" name="Impact (pp)">
            {chart.map((c, i) => <Cell key={i} fill={c.impact >= 0 ? '#d64545' : '#2e9e5b'} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="disclaimer">⚠ {r.disclaimer}</p>
    </div>
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
