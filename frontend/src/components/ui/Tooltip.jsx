import { useEffect, useRef, useState } from 'react'
import { cn } from '../../lib/utils.js'

export default function Tooltip({ content, children, side = 'top' }) {
  const [open, setOpen] = useState(false)
  const timeoutRef = useRef(null)

  useEffect(() => () => window.clearTimeout(timeoutRef.current), [])

  const sideClass = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  }

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => {
        window.clearTimeout(timeoutRef.current)
        setOpen(true)
      }}
      onMouseLeave={() => {
        timeoutRef.current = window.setTimeout(() => setOpen(false), 80)
      }}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open && content ? (
        <span
          role="tooltip"
          className={cn(
            'pointer-events-none absolute z-50 whitespace-nowrap rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-[11px] text-zinc-300 shadow-lg',
            sideClass[side],
          )}
        >
          {content}
        </span>
      ) : null}
    </span>
  )
}
