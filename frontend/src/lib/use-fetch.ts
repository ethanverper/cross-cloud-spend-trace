import { useEffect, useRef, useState } from "react"

interface FetchState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

/** Small fetch hook: re-runs whenever `deps` change, guards against a
 * stale response landing after a newer request started (fast filter
 * changes shouldn't flicker back to an old result). */
export function useFetch<T>(fn: () => Promise<T>, deps: unknown[]): FetchState<T> {
  const [state, setState] = useState<FetchState<T>>({ data: null, loading: true, error: null })
  const requestId = useRef(0)

  useEffect(() => {
    const id = ++requestId.current
    setState((s) => ({ ...s, loading: true, error: null }))
    fn()
      .then((data) => {
        if (requestId.current === id) setState({ data, loading: false, error: null })
      })
      .catch((err: Error) => {
        if (requestId.current === id) setState({ data: null, loading: false, error: err.message })
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return state
}
