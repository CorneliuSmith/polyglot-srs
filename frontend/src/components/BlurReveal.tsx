import { useState, type ReactNode } from 'react'

/**
 * Blur-until-toggled text (Bunpro example lists): the translation (or
 * sentence) starts blurred so learners test themselves before peeking.
 * Click toggles one item; a parent "show all" switch overrides via
 * `forceRevealed`.
 */
export default function BlurReveal({
  children,
  forceRevealed = false,
  className = '',
}: {
  children: ReactNode
  forceRevealed?: boolean
  className?: string
}) {
  const [revealed, setRevealed] = useState(false)
  const shown = forceRevealed || revealed

  return (
    <button
      type="button"
      onClick={() => setRevealed((v) => !v)}
      aria-pressed={shown}
      title={shown ? undefined : 'Click to reveal'}
      className={`text-left transition duration-150 ${
        shown ? '' : 'blur-sm select-none opacity-70 hover:opacity-90'
      } ${className}`}
    >
      {children}
    </button>
  )
}
