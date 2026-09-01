import { useEffect } from 'react'
import { cn } from '../../lib/utils.js'
import Button from './Button.jsx'

export default function Drawer({ open, onClose, title, description, children, footer }) {
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [open])

  if (!open) return null

  return (
    <>
      <button
        type="button"
        aria-label="Close panel"
        className="fixed inset-0 z-40 bg-black/50"
        onClick={onClose}
      />
      <aside
        className={cn(
          'fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col border-l border-zinc-800 bg-[#151821] shadow-2xl',
          'animate-slide-in',
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
      >
        <div className="border-b border-zinc-800 px-5 py-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 id="drawer-title" className="text-base font-semibold text-zinc-100">
                {title}
              </h2>
              {description ? (
                <p className="mt-0.5 text-xs text-zinc-500">{description}</p>
              ) : null}
            </div>
            <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close">
              ✕
            </Button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4 scrollbar-thin">{children}</div>
        {footer ? (
          <div className="border-t border-zinc-800 px-5 py-4">{footer}</div>
        ) : null}
      </aside>
    </>
  )
}
