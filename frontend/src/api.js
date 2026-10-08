const TOKEN_KEY = 'sh_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY))

export class ApiError extends Error {
  constructor(message, status, errors) {
    super(message)
    this.status = status
    this.errors = errors || []
  }
}

async function request(method, path, body, params) {
  const qs = params
    ? '?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null)).toString()
    : ''
  const headers = { 'Content-Type': 'application/json' }
  if (getToken()) headers.Authorization = `Bearer ${getToken()}`
  const res = await fetch(`/api${path}${qs}`, { method, headers, body: body ? JSON.stringify(body) : undefined })
  if (res.status === 204) return null
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    if (res.status === 401 && getToken()) {
      setToken(null)
      window.location.assign('/login')
    }
    const detail = Array.isArray(data.errors) && data.errors.length
      ? data.errors.map((e) => `${e.field}: ${e.message}`).join('; ')
      : typeof data.detail === 'string' ? data.detail : 'Request failed'
    throw new ApiError(detail, res.status, data.errors)
  }
  return data
}

export const api = {
  get: (p, params) => request('GET', p, null, params),
  post: (p, b) => request('POST', p, b),
  patch: (p, b) => request('PATCH', p, b),
  put: (p, b) => request('PUT', p, b),
  del: (p) => request('DELETE', p),
}
