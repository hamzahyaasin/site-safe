import { useEffect, useState } from 'react'
import { useAuth } from '../../context/AuthContext.jsx'

// The evidence frame (FR-29) is served only to signed-in users, so it is
// fetched with the session's token rather than linked as a plain <img src>.
export default function AlertSnapshot({ alertId }) {
  const { api } = useAuth()
  const [state, setState] = useState({ url: null, error: null })

  useEffect(() => {
    let url = null
    let cancelled = false
    api
      .get(`alerts/${alertId}/snapshot/`, { responseType: 'blob' })
      .then(({ data }) => {
        if (cancelled) return
        url = URL.createObjectURL(data)
        setState({ url, error: null })
      })
      .catch((err) => {
        if (cancelled) return
        setState({
          url: null,
          error:
            err.response?.status === 404
              ? 'Snapshot no longer available (removed by the retention policy).'
              : 'Snapshot could not be loaded.',
        })
      })
    return () => {
      cancelled = true
      if (url) URL.revokeObjectURL(url)
    }
  }, [api, alertId])

  if (state.error) return <p className="text-sm text-zinc-500">{state.error}</p>
  if (!state.url) return <div className="h-40 w-full max-w-md animate-pulse rounded bg-zinc-800" />
  return (
    <a href={state.url} target="_blank" rel="noreferrer" className="block max-w-md">
      <img
        src={state.url}
        alt="Camera frame that confirmed this alert"
        className="w-full rounded border border-zinc-800"
      />
    </a>
  )
}
