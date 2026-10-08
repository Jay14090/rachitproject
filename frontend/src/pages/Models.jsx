import { api, getToken } from '../api'
import { useAuth } from '../auth'
import { useFetch } from '../hooks'

const pct = (v) => (v == null ? '—' : (v * 100).toFixed(1) + '%')
const TITLES = { diabetes: 'Diabetes', heart_disease: 'Heart disease' }

async function downloadCsv() {
  const res = await fetch('/api/reports/predictions.csv', { headers: { Authorization: `Bearer ${getToken()}` } })
  if (!res.ok) return window.alert('Export failed')
  const url = URL.createObjectURL(await res.blob())
  const a = Object.assign(document.createElement('a'), { href: url, download: 'predictions.csv' })
  a.click()
  URL.revokeObjectURL(url)
}

export default function Models() {
  const { user } = useAuth()
  const { data, error, loading } = useFetch(() => api.get('/models'))
  const usage = useFetch(() => api.get('/models/usage'))
  if (loading) return <p>Loading…</p>
  if (error) return <p className="error">{error}</p>
  return (
    <>
      <div className="row between">
        <h2>ML models</h2>
        {['admin', 'analyst'].includes(user.role) && <button onClick={downloadCsv}>⬇ Export predictions (CSV, de-identified)</button>}
      </div>
      <p className="muted">Predictions are decision-support estimates, not diagnoses. Metrics are on a held-out 20% test split.</p>
      {data.length === 0 && <p className="muted">No model registered. Run <code>python ml/train_diabetes.py</code> and <code>python ml/train_heart.py</code>.</p>}

      {usage.data?.length > 0 && (
        <section className="card">
          <h3>Usage &amp; monitoring</h3>
          <table>
            <thead><tr><th>Model version</th><th>Predictions</th><th>Avg risk</th><th>Low / Moderate / High</th><th>Last used</th></tr></thead>
            <tbody>
              {usage.data.map((u) => (
                <tr key={u.model_version}>
                  <td>{u.model_version}</td><td>{u.prediction_count}</td><td>{pct(u.avg_risk_score)}</td>
                  <td>{u.risk_levels.low} / {u.risk_levels.moderate} / {u.risk_levels.high}</td>
                  <td className="muted">{u.last_used ? u.last_used.replace('T', ' ').slice(0, 16) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {data.map((m) => (
        <section className="card" key={m.model_id}>
          <div className="row between">
            <h3>{TITLES[m.disease_type] || m.disease_type}: {m.version} {m.active_flag && <span className="pill st-scheduled">active</span>}</h3>
            <span className="muted">{m.algorithm} · trained {m.trained_at.slice(0, 10)}</span>
          </div>
          <div className="stats">
            {['accuracy', 'precision', 'recall', 'f1', 'roc_auc'].map((k) => (
              <div className="stat small" key={k}><div className="num">{pct(m.metrics[k])}</div><div className="lbl">{k.replace('_', '-')}</div></div>
            ))}
          </div>
          {m.metrics.confusion_matrix && (
            <p className="muted">Confusion matrix — TN {m.metrics.confusion_matrix.tn} · FP {m.metrics.confusion_matrix.fp} ·
              FN {m.metrics.confusion_matrix.fn} · TP {m.metrics.confusion_matrix.tp}</p>
          )}
          {m.metrics.comparison && (
            <>
              <h4>Algorithm comparison</h4>
              <table>
                <thead><tr><th>Algorithm</th><th>CV ROC-AUC</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>F1</th><th>Test ROC-AUC</th></tr></thead>
                <tbody>
                  {Object.entries(m.metrics.comparison).map(([name, r]) => (
                    <tr key={name} className={name === m.algorithm ? 'selected' : ''}>
                      <td>{name}{name === m.algorithm && ' ✓'}</td>
                      <td>{r.cv_roc_auc_mean.toFixed(3)} ± {r.cv_roc_auc_std.toFixed(3)}</td>
                      <td>{pct(r.test.accuracy)}</td><td>{pct(r.test.precision)}</td><td>{pct(r.test.recall)}</td>
                      <td>{pct(r.test.f1)}</td><td>{pct(r.test.roc_auc)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </section>
      ))}
    </>
  )
}
