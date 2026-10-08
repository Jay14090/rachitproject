import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { useFetch, useForm } from '../hooks'

export default function Patients() {
  const { user } = useAuth()
  const canCreate = ['admin', 'reception'].includes(user.role)
  const [q, setQ] = useState('')
  const [search, setSearch] = useState('')
  const { data, error, loading, reload } = useFetch(() => api.get('/patients', { q: search }), [search])
  const [showForm, setShowForm] = useState(false)

  return (
    <>
      <div className="row between">
        <h2>Patients</h2>
        {canCreate && <button onClick={() => setShowForm((s) => !s)}>{showForm ? 'Close' : '+ Register patient'}</button>}
      </div>
      {showForm && <PatientForm onDone={() => { setShowForm(false); reload() }} />}
      <form className="row" onSubmit={(e) => { e.preventDefault(); setSearch(q) }}>
        <input placeholder="Search by name, phone or ID" value={q} onChange={(e) => setQ(e.target.value)} />
        <button>Search</button>
        {search && <button type="button" className="link" onClick={() => { setQ(''); setSearch('') }}>Clear</button>}
      </form>
      {error && <p className="error">{error}</p>}
      {loading ? <p>Loading…</p> : (
        <table>
          <thead><tr><th>ID</th><th>Name</th><th>Age</th><th>Gender</th><th>Contact</th><th /></tr></thead>
          <tbody>
            {data.map((p) => (
              <tr key={p.patient_id}>
                <td>{p.patient_id}</td><td>{p.name}</td><td>{p.age}</td><td>{p.gender}</td><td>{p.contact}</td>
                <td><Link to={`/patients/${p.patient_id}`}>Open</Link></td>
              </tr>
            ))}
            {data.length === 0 && <tr><td colSpan="6" className="muted">No patients found.</td></tr>}
          </tbody>
        </table>
      )}
    </>
  )
}

function PatientForm({ onDone }) {
  const { values, bind } = useForm({ name: '', date_of_birth: '', gender: 'female', contact: '', address: '' })
  const [error, setError] = useState('')
  const submit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/patients', { ...values, address: values.address || null })
      onDone()
    } catch (err) {
      setError(err.message)
    }
  }
  return (
    <form className="card formgrid" onSubmit={submit}>
      <label>Full name<input {...bind('name')} required minLength={2} /></label>
      <label>Date of birth<input type="date" {...bind('date_of_birth')} required max={new Date().toISOString().slice(0, 10)} /></label>
      <label>Gender
        <select {...bind('gender')}><option value="female">Female</option><option value="male">Male</option><option value="other">Other</option></select>
      </label>
      <label>Contact<input {...bind('contact')} required minLength={5} /></label>
      <label className="wide">Address<input {...bind('address')} /></label>
      {error && <p className="error wide">{error}</p>}
      <button>Save patient</button>
    </form>
  )
}
