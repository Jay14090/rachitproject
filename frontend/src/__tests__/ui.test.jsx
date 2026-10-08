import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { NAV, AuthProvider } from '../auth'
import Login from '../pages/Login'
import PredictionPanel from '../components/PredictionPanel'
import * as apiModule from '../api'

describe('navigation by role', () => {
  const visible = (role) => NAV.filter((n) => n.roles.includes(role)).map((n) => n.label)

  it('hides clinical and admin pages from analysts', () => {
    const labels = visible('analyst')
    expect(labels).toEqual(expect.arrayContaining(['Dashboard', 'ML Models', 'My account']))
    expect(labels).not.toContain('Patients')
    expect(labels).not.toContain('Users')
  })

  it('shows admin-only pages only to admins', () => {
    expect(visible('admin')).toEqual(expect.arrayContaining(['Users', 'Audit Log']))
    for (const r of ['doctor', 'reception', 'analyst']) expect(visible(r)).not.toContain('Audit Log')
  })
})

describe('Login page', () => {
  it('fills demo credentials and shows server errors', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false, status: 401, json: () => Promise.resolve({ detail: 'Invalid email or password' }),
    })
    render(<AuthProvider><Login /></AuthProvider>)
    await userEvent.click(screen.getByRole('button', { name: 'Doctor' }))
    expect(screen.getByLabelText('Email').value).toBe('doctor@hospital.example.com')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByText('Invalid email or password')).toBeTruthy()
  })
})

describe('PredictionPanel', () => {
  it('switches between the diabetes and heart-disease forms and posts the right endpoint', async () => {
    const post = vi.spyOn(apiModule.api, 'post').mockResolvedValue({
      prediction_id: 1, patient_id: 7, disease_type: 'heart_disease', risk_score: 0.72, risk_level: 'high',
      model_version: 'heart-random-forest-v1', created_at: '2026-10-08T10:00:00', disclaimer: 'Not a diagnosis',
      explanation: [{ feature: 'ca', value: 2, impact: 0.2 }],
    })
    vi.spyOn(apiModule.api, 'get').mockResolvedValue([])
    render(<MemoryRouter><PredictionPanel patientId={7} age={55} /></MemoryRouter>)

    expect(screen.getByLabelText(/Glucose/)).toBeTruthy()
    await userEvent.click(screen.getByRole('button', { name: 'Heart disease' }))
    expect(screen.getByLabelText(/Cholesterol/)).toBeTruthy()
    expect(screen.queryByLabelText(/Glucose/)).toBeNull()

    await userEvent.type(screen.getByLabelText(/Resting systolic BP/), '140')
    await userEvent.type(screen.getByLabelText(/Cholesterol/), '240')
    await userEvent.type(screen.getByLabelText(/Max heart rate/), '150')
    await userEvent.click(screen.getByRole('button', { name: 'Estimate risk' }))

    await waitFor(() => expect(post).toHaveBeenCalled())
    const [endpoint, body] = post.mock.calls[0]
    expect(endpoint).toBe('/predict/heart-disease')
    expect(body).toMatchObject({ patient_id: 7, age: 55, trestbps: 140, chol: 240, thalach: 150, sex: 1 })
    expect(await screen.findByText(/72\.0% — high risk/)).toBeTruthy()
    expect(screen.getByText(/Not a diagnosis/)).toBeTruthy()
  })
})
