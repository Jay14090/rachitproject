import { useState } from 'react'
import { api } from '../api'
import { useFetch } from '../hooks'

export default function AuditLog() {
  const [action, setAction] = useState('')
  const { data, error, loading } = useFetch(() => api.get('/audit-logs', { action, limit: 200 }), [action])
  return (
    <>
      <h2>Audit log</h2>
      <p className="muted">Records who did what and when. Entries hold IDs only — no patient details.</p>
      <label>Filter by action <input placeholder="e.g. patient_created" value={action} onChange={(e) => setAction(e.target.value.trim())} /></label>
      {error && <p className="error">{error}</p>}
      {loading ? <p>Loading…</p> : (
        <table>
          <thead><tr><th>Time (UTC)</th><th>User</th><th>Action</th><th>Entity</th><th>Details</th></tr></thead>
          <tbody>
            {data.map((l) => (
              <tr key={l.log_id}>
                <td>{l.timestamp.replace('T', ' ').slice(0, 19)}</td><td>{l.user_name || '—'}</td><td><code>{l.action}</code></td>
                <td>{l.entity_type ? `${l.entity_type} #${l.entity_id ?? ''}` : '—'}</td>
                <td className="muted">{l.metadata ? JSON.stringify(l.metadata) : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  )
}
