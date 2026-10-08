import { api, ApiError, getToken, setToken } from '../api'

const respond = (status, body) => Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) })

describe('api client', () => {
  it('sends the bearer token and JSON body', async () => {
    setToken('abc')
    const f = vi.spyOn(globalThis, 'fetch').mockReturnValue(respond(200, { ok: true }))
    await api.post('/patients', { name: 'X' })
    const [url, init] = f.mock.calls[0]
    expect(url).toBe('/api/patients')
    expect(init.headers.Authorization).toBe('Bearer abc')
    expect(init.body).toBe('{"name":"X"}')
  })

  it('drops empty query params', async () => {
    const f = vi.spyOn(globalThis, 'fetch').mockReturnValue(respond(200, []))
    await api.get('/patients', { q: '', limit: 5, status: null })
    expect(f.mock.calls[0][0]).toBe('/api/patients?limit=5')
  })

  it('turns validation errors into a readable message', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(respond(422, {
      detail: 'Validation failed', errors: [{ field: 'contact', message: 'bad' }, { field: 'name', message: 'short' }],
    }))
    await expect(api.post('/patients', {})).rejects.toMatchObject({ message: 'contact: bad; name: short', status: 422 })
  })

  it('uses the server detail for plain errors and returns null on 204', async () => {
    const f = vi.spyOn(globalThis, 'fetch')
    f.mockReturnValueOnce(respond(409, { detail: 'Department already exists' }))
    await expect(api.post('/departments', {})).rejects.toBeInstanceOf(ApiError)
    f.mockReturnValueOnce(Promise.resolve({ ok: true, status: 204 }))
    expect(await api.del('/departments/1')).toBeNull()
  })

  it('clears the session on 401 for a logged-in user', async () => {
    setToken('stale')
    delete window.location
    window.location = { assign: vi.fn() }
    vi.spyOn(globalThis, 'fetch').mockReturnValue(respond(401, { detail: 'Not authenticated' }))
    await expect(api.get('/patients')).rejects.toThrow()
    expect(getToken()).toBeNull()
    expect(window.location.assign).toHaveBeenCalledWith('/login')
  })
})
