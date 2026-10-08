import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.restoreAllMocks()
})

// jsdom lacks ResizeObserver, which Recharts' ResponsiveContainer needs.
globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }
