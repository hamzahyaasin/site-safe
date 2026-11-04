import { useEffect, useId, useRef } from 'react'
import { cn } from '../../lib/utils.js'
import Button from './Button.jsx'

const widths = {
  md: 'max-w-md',
  lg: 'max-w-xl',
}

/** Slide-over panel. Escape or the backdrop closes it; focus moves into it and back to the opener. */
export default function Drawer({ open, onClose, title, description, children, footer, size = 'md' }) {
  const panelRef = useRef(null)
  const titleId = useId()
  const onCloseRef = useRef(onClose)

  useEffect(() => {
    onCloseRef.current = onClose
  })

  useEffect(() => {
    if (!open) return undefined
    document.body.style.overflow = 'hidden'
    const previous = document.activeElement
    // Focus the first text field (or the panel) unless something inside already took focus (autoFocus).
    // Selects are skipped: some save on change, and arrow keys would change them.
    const t = window.setTimeout(() => {
      const panel = panelRef.current
      if (!panel || panel.contains(document.activeElement)) return
      const first = panel.querySelector(
        'input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([disabled]):not([readonly]), textarea:not([disabled])',
      )
      ;(first || panel).focus()
    }, 0)
    const onKey = (e) => {
      // A confirm dialog on top handles its own Escape.
      if (e.key === 'Escape' && !document.querySelector('[role=alertdialog]')) onCloseRef.current?.()
    }
    window.addEventListener('keydown', onKey)
    return () => {
      window.clearTimeout(t)
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
      previous?.focus?.()
    }
  }, [open])

  if (!open) return null

  return (
    <>
      <div aria-hidden className="animate-fade-in fixed inset-0 z-40 bg-black/60 backdrop-blur-[2px]" onClick={onClose} />
      <aside
        ref={panelRef}
        tabIndex={-1}
        className={cn(
          'animate-slide-in fixed right-0 top-0 z-50 flex h-full w-full flex-col border-l border-zinc-800 bg-[#151821] shadow-2xl shadow-black/50 outline-none',
          widths[size] || widths.md,
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="flex items-start justify-between gap-3 border-b border-zinc-800 px-5 py-4">
          <div className="min-w-0">
            <h2 id={titleId} className="truncate text-base font-semibold text-zinc-50">
              {title}
            </h2>
            {description ? <p className="mt-0.5 text-xs text-zinc-400">{description}</p> : null}
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close panel" className="-mr-1.5 -mt-0.5">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-5 scrollbar-thin">{children}</div>
        {footer ? <div className="border-t border-zinc-800 bg-[#12141c] px-5 py-3.5">{footer}</div> : null}
      </aside>
    </>
  )
}
