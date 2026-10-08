import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import { useFetch, useForm } from '../hooks'

export const LEVEL_COLOR = { low: '#2e9e5b', moderate: '#e0a100', high: '#d64545' }

const YES_NO = [[0, 'No'], [1, 'Yes']]
const codes = (...n) => n.map((c) => [c, `Code ${c}`])

// Field spec: [key, label, kind, extra]. kind = number | select. `extra` is {step,min,max} or options.
export const DISEASES = {
  diabetes: {
    title: 'Diabetes',
    endpoint: '/predict/diabetes',
    defaults: (age) => ({ pregnancies: 0, glucose: '', blood_pressure: '', skin_thickness: 20, insulin: 0, bmi: '', diabetes_pedigree: 0.5, age }),
    fields: [
      ['pregnancies', 'Pregnancies', 'number', { step: 1, min: 0, max: 20 }],
      ['glucose', 'Glucose (mg/dL)', 'number', { step: 1, min: 40, max: 400 }],
      ['blood_pressure', 'Diastolic BP (mm Hg)', 'number', { step: 1, min: 30, max: 200 }],
      ['skin_thickness', 'Skin thickness (mm)', 'number', { step: 1, min: 0, max: 100 }],
      ['insulin', 'Insulin (mu U/ml, 0 = unknown)', 'number', { step: 1, min: 0, max: 900 }],
      ['bmi', 'BMI', 'number', { step: 0.1, min: 10, max: 70 }],
      ['diabetes_pedigree', 'Diabetes pedigree function', 'number', { step: 0.001, min: 0, max: 3 }],
      ['age', 'Age', 'number', { step: 1, min: 1, max: 120 }],
    ],
  },
  heart_disease: {
    title: 'Heart disease',
    endpoint: '/predict/heart-disease',
    defaults: (age) => ({ age, sex: 1, cp: 0, trestbps: '', chol: '', fbs: 0, restecg: 0, thalach: '', exang: 0, oldpeak: 0, slope: 1, ca: 0, thal: 2 }),
    fields: [
      ['age', 'Age', 'number', { step: 1, min: 1, max: 120 }],
      ['sex', 'Sex', 'select', [[1, 'Male'], [0, 'Female']]],
      ['cp', 'Chest-pain type (dataset code)', 'select', codes(0, 1, 2, 3)],
      ['trestbps', 'Resting systolic BP (mm Hg)', 'number', { step: 1, min: 70, max: 250 }],
      ['chol', 'Cholesterol (mg/dL)', 'number', { step: 1, min: 80, max: 700 }],
      ['fbs', 'Fasting glucose > 120 mg/dL', 'select', YES_NO],
      ['restecg', 'Resting ECG (dataset code)', 'select', codes(0, 1, 2)],
      ['thalach', 'Max heart rate achieved', 'number', { step: 1, min: 50, max: 250 }],
      ['exang', 'Exercise-induced angina', 'select', YES_NO],
      ['oldpeak', 'ST depression (oldpeak)', 'number', { step: 0.1, min: 0, max: 10 }],
      ['slope', 'ST slope (dataset code)', 'select', codes(0, 1, 2)],
      ['ca', 'Major vessels coloured (0–3)', 'select', codes(0, 1, 2, 3).map(([c]) => [c, String(c)])],
      ['thal', 'Thalassemia (dataset code)', 'select', codes(1, 2, 3)],
    ],
  },
}

const stamp = (iso) => iso.replace('T', ' ').slice(0, 16)

export default function PredictionPanel({ patientId, age }) {
  const [disease, setDisease] = useState('diabetes')
  const spec = DISEASES[disease]
  return (
    <section className="card">
      <div className="row between">
        <h3>Risk prediction</h3>
        <div className="tabs">
          {Object.entries(DISEASES).map(([k, d]) => (
            <button key={k} type="button" className={k === disease ? 'tab active' : 'tab'} onClick={() => setDisease(k)}>{d.title}</button>
          ))}
        </div>
      </div>
      {/* key forces a fresh form/state when switching disease */}
      <DiseaseForm key={disease} disease={disease} spec={spec} patientId={patientId} age={age} />
    </section>
  )
}

function DiseaseForm({ disease, spec, patientId, age }) {
  const { data: history, reload } = useFetch(() => api.get(`/predictions/${patientId}`, { disease }), [patientId, disease])
  const { values, bind } = useForm(spec.defaults(age))
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const body = { patient_id: patientId }
      spec.fields.forEach(([k]) => { body[k] = Number(values[k]) })
      setResult(await api.post(spec.endpoint, body))
      reload()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return (
    <>
      <form className="formgrid" onSubmit={submit}>
        {spec.fields.map(([k, label, kind, extra]) => (
          <label key={k}>{label}
            {kind === 'select'
              ? <select {...bind(k)}>{extra.map(([v, text]) => <option key={v} value={v}>{text}</option>)}</select>
              : <input type="number" required {...extra} {...bind(k)} />}
          </label>
        ))}
        <button disabled={busy}>{busy ? 'Calculating…' : 'Estimate risk'}</button>
      </form>
      {error && <p className="error">{error}</p>}
      {result && <PredictionResult r={result} />}
      <RiskTrend history={history} />
      <h4>History</h4>
      {history && history.length === 0 && <p className="muted">No {spec.title.toLowerCase()} predictions yet.</p>}
      {history && history.length > 0 && (
        <table>
          <thead><tr><th>Date</th><th>Risk</th><th>Level</th><th>Model</th></tr></thead>
          <tbody>
            {history.map((h) => (
              <tr key={h.prediction_id} onClick={() => setResult(h)} className="clickable">
                <td>{stamp(h.created_at)}</td>
                <td>{(h.risk_score * 100).toFixed(1)}%</td>
                <td><span className="pill" style={{ background: LEVEL_COLOR[h.risk_level] }}>{h.risk_level}</span></td>
                <td className="muted">{h.model_version}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  )
}

export function RiskTrend({ history }) {
  if (!history || history.length < 2) return null
  // x is the (unique) prediction id so several predictions within the same minute stay separate points.
  const data = [...history].reverse().map((h) => ({ id: h.prediction_id, when: stamp(h.created_at), risk: Math.round(h.risk_score * 1000) / 10 }))
  const label = (id) => data.find((d) => d.id === id)?.when ?? ''
  return (
    <>
      <h4>Risk over time</h4>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ left: 0, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="id" tickFormatter={label} tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} unit="%" />
          <Tooltip labelFormatter={label} />
          <Line type="monotone" dataKey="risk" name="Risk %" stroke="#2f6fdb" strokeWidth={2} dot isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </>
  )
}

export function PredictionResult({ r }) {
  const chart = r.explanation.map((e) => ({ name: `${e.feature} = ${e.value}`, impact: Math.round(e.impact * 1000) / 10 }))
  return (
    <div className="result" style={{ borderColor: LEVEL_COLOR[r.risk_level] }}>
      <div className="big" style={{ color: LEVEL_COLOR[r.risk_level] }}>{(r.risk_score * 100).toFixed(1)}% — {r.risk_level} risk</div>
      <div className="muted">Model {r.model_version} · {stamp(r.created_at)}</div>
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
