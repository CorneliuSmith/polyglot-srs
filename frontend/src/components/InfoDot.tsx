import { useEffect, useRef, useState } from 'react'

/**
 * A tiny "i" that opens a short explanation.
 *
 * Click, not CSS `:hover` — a tooltip that needs a mouse is unreadable on
 * the handset most of this app's study traffic happens on, and a `title`
 * attribute cannot hold a worked example. Escape and an outside click both
 * close it; the trigger is small enough to sit inline against a label
 * without disturbing the line.
 */
export default function InfoDot({
  label,
  title,
  children,
  testId,
}: {
  /** Accessible name — "What is a word-by-word breakdown?" */
  label: string
  title: string
  children: React.ReactNode
  testId?: string
}) {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (!open) return
    function onDown(e: MouseEvent) {
      if (!box.current?.contains(e.target as Node)) setOpen(false)
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <span className="relative inline-block" ref={box}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={label}
        data-testid={testId ?? 'info-dot'}
        className="inline-flex h-3.5 w-3.5 items-center justify-center rounded-full border border-gray-300 align-middle text-[9px] font-semibold text-gray-400 hover:border-lang hover:text-lang"
      >
        i
      </button>
      {open && (
        <span
          role="tooltip"
          data-testid={`${testId ?? 'info-dot'}-body`}
          className="absolute start-0 top-5 z-20 block w-64 rounded-lg border border-gray-200 bg-white p-3 text-start normal-case tracking-normal shadow-lg"
        >
          <span className="block text-xs font-semibold text-gray-800">
            {title}
          </span>
          <span className="mt-1 block text-[11px] leading-relaxed text-gray-600">
            {children}
          </span>
        </span>
      )}
    </span>
  )
}
