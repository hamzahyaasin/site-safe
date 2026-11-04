import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import Button from '../components/ui/Button.jsx'
import { cn } from '../lib/utils.js'

const FeedbackContext = createContext(null)

const TOAST_MS = 4000

/**
 * In-app feedback: ``toast(message, tone)`` for the result of an action and
 * ``confirm({...})`` (resolves true/false) before a destructive one. Replaces
 * the browser's alert()/confirm() boxes, which block the page and cannot be
 * styled or read consistently.
 */
export function FeedbackProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const [dialog, setDialog] = useState(null)
  const nextId = useRef(1)

  const dismiss = useCallback((id) => setToasts((list) => list.filter((t) => t.id !== id)), [])

  const toast = useCallback(
    (message, tone = 'success') => {
      const id = nextId.current++
      setToasts((list) => [...list.slice(-3), { id, message, tone }])
      window.setTimeout(() => dismiss(id), TOAST_MS)
    },
    [dismiss],
  )

  const confirm = useCallback(
    (options) =>
      new Promise((resolve) => {
        setDialog({ ...options, resolve })
      }),
    [],
  )

  const closeDialog = useCallback(
    (result) => {
      dialog?.resolve(result)
      setDialog(null)
    },
    [dialog],
  )

  const value = useMemo(() => ({ toast, confirm }), [toast, confirm])

  return (
    <FeedbackContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[70] flex w-[min(380px,calc(100vw-2rem))] flex-col gap-2">
        {toasts.map((t) => (
          <Toast key={t.id} toast={t} onDismiss={() => dismiss(t.id)} />
        ))}
      </div>
      {dialog ? <ConfirmDialog dialog={dialog} onClose={closeDialog} /> : null}
    </FeedbackContext.Provider>
  )
}

const TOAST_TONE = {
  success: { ring: 'border-emerald-500/30', icon: 'text-emerald-400', path: <polyline points="20 6 9 17 4 12" /> },
  error: {
    ring: 'border-red-500/30',
    icon: 'text-red-400',
    path: (
      <>
        <circle cx="12" cy="12" r="9" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </>
    ),
  },
  info: {
    ring: 'border-sky-500/30',
    icon: 'text-sky-400',
    path: (
      <>
        <circle cx="12" cy="12" r="9" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
      </>
    ),
  },
}

function Toast({ toast, onDismiss }) {
  const tone = TOAST_TONE[toast.tone] || TOAST_TONE.success
  return (
    <div
      role={toast.tone === 'error' ? 'alert' : 'status'}
      className={cn(
        'animate-pop-in pointer-events-auto flex items-start gap-3 rounded-lg border bg-[#1a1d27]/95 px-3.5 py-3 text-sm text-zinc-100 shadow-xl shadow-black/40 backdrop-blur',
        tone.ring,
      )}
    >
      <svg className={cn('mt-0.5 h-4 w-4 shrink-0', tone.icon)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        {tone.path}
      </svg>
      <p className="min-w-0 flex-1 leading-snug">{toast.message}</p>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss"
        className="-mr-1 rounded p-0.5 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200"
      >
        <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
      </button>
    </div>
  )
}

function ConfirmDialog({ dialog, onClose }) {
  const cancelRef = useRef(null)
  const {
    title,
    message,
    confirmLabel = 'Confirm',
    cancelLabel = 'Cancel',
    tone = 'danger',
  } = dialog

  useEffect(() => {
    const previous = document.activeElement
    // Focus Cancel: Enter on a destructive dialog should not be the destructive choice.
    cancelRef.current?.focus()
    const onKey = (e) => {
      if (e.key === 'Escape') onClose(false)
    }
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('keydown', onKey)
      previous?.focus?.()
    }
  }, [onClose])

  return (
    <div className="animate-fade-in fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4 backdrop-blur-[2px]" onMouseDown={() => onClose(false)}>
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-message"
        className="animate-pop-in w-full max-w-md rounded-xl border border-zinc-700/80 bg-[#1a1d27] p-5 shadow-2xl shadow-black/50"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-3">
          <span
            className={cn(
              'flex h-9 w-9 shrink-0 items-center justify-center rounded-full',
              tone === 'danger' ? 'bg-red-500/15 text-red-400' : 'bg-amber-500/15 text-amber-400',
            )}
          >
            <svg className="h-4.5 w-4.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
              <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </span>
          <div className="min-w-0">
            <h2 id="confirm-title" className="text-base font-semibold text-zinc-50">
              {title}
            </h2>
            {message ? (
              <p id="confirm-message" className="mt-1.5 text-sm leading-relaxed text-zinc-400">
                {message}
              </p>
            ) : null}
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button ref={cancelRef} variant="secondary" onClick={() => onClose(false)}>
            {cancelLabel}
          </Button>
          <Button variant={tone === 'danger' ? 'destructive' : 'primary'} onClick={() => onClose(true)}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}

// eslint-disable-next-line react-refresh/only-export-components -- hook co-located with its provider
export function useFeedback() {
  const ctx = useContext(FeedbackContext)
  if (!ctx) throw new Error('useFeedback must be used within FeedbackProvider')
  return ctx
}

/** The message to show for a failed API call. */
// eslint-disable-next-line react-refresh/only-export-components -- shared with the provider's callers
export function apiErrorText(err, fallback = 'Something went wrong. Please try again.') {
  const data = err?.response?.data
  if (!data) return err?.message || fallback
  if (typeof data === 'string') return data.length > 300 ? fallback : data
  if (data.detail) return data.detail
  const parts = Object.entries(data).map(([field, msgs]) => {
    const text = [].concat(msgs).join(' ')
    return field === 'non_field_errors' ? text : `${field.replace(/_/g, ' ')}: ${text}`
  })
  return parts.join(' · ') || fallback
}
