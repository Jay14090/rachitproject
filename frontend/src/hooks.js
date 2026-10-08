import { useCallback, useEffect, useState } from 'react'

/** Fetch on mount / when deps change; returns {data, error, loading, reload}. */
export function useFetch(fn, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const load = useCallback(() => {
    setState((s) => ({ ...s, loading: true }))
    return fn().then(
      (data) => setState({ data, error: null, loading: false }),
      (error) => setState({ data: null, error: error.message, loading: false }),
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(() => { load() }, [load])
  return { ...state, reload: load }
}

/** Generic form state helper. */
export function useForm(initial) {
  const [values, setValues] = useState(initial)
  const bind = (name) => ({
    name,
    value: values[name] ?? '',
    onChange: (e) => setValues((v) => ({ ...v, [name]: e.target.value })),
  })
  return { values, setValues, bind, reset: () => setValues(initial) }
}
