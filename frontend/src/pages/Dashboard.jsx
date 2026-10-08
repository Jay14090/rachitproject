import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from 'recharts'
import { api } from '../api'
import { useFetch } from '../hooks'

const RISK_COLORS = { low: '#2e9e5b', moderate: '#e0a100', high: '#d64545' }

export default function Dashboard() {
  const { data, error, loading } = useFetch(() => api.get('/dashboard'))
  if (loading) return <p>Loading…</p>
  if (error) return <p className="error">{error}</p>
  const t = data.totals
  const risk = Object.entries(data.risk_distribution).map(([name, value]) => ({ name, value }))
  const noRisk = risk.every((r) => r.value === 0)

  return (
    <>
      <h2>Dashboard</h2>
      <div className="stats">
        <Stat label="Patients" value={t.patients} />
        <Stat label="Active doctors" value={t.active_doctors} />
        <Stat label="Appointments today" value={t.appointments_today} />
        <Stat label="Risk predictions" value={t.predictions} />
      </div>
      <div className="grid2">
        <section className="card">
          <h3>Scheduled appointments — next 7 days</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data.appointments_next_7_days.map((d) => ({ ...d, day: d.date.slice(5) }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" name="Appointments" fill="#2f6fdb" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </section>
        <section className="card">
          <h3>Diabetes risk levels (all predictions)</h3>
          {noRisk ? <p className="muted">No predictions yet.</p> : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={risk} dataKey="value" nameKey="name" outerRadius={85} label>
                  {risk.map((r) => <Cell key={r.name} fill={RISK_COLORS[r.name]} />)}
                </Pie>
                <Legend />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </section>
      </div>
      <section className="card">
        <h3>Appointments by status</h3>
        <div className="stats">
          {Object.entries(data.appointments_by_status).map(([k, v]) => <Stat key={k} label={k} value={v} small />)}
        </div>
      </section>
    </>
  )
}

function Stat({ label, value, small }) {
  return (
    <div className={`stat ${small ? 'small' : ''}`}>
      <div className="num">{value}</div>
      <div className="lbl">{label}</div>
    </div>
  )
}
