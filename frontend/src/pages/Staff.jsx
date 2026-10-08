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
                  {isAdmin && <td><button className="link" onClick={async () => {
                    await api.patch(`/doctors/${d.doctor_id}`, { status: d.status === 'active' ? 'inactive' : 'active' })
                    reloadAll()
                  }}>{d.status === 'active' ? 'Deactivate' : 'Activate'}</button></td>}
                </tr>
              ))}
            </tbody>
          </table>
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
