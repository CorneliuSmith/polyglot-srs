import { useEffect, useState, type ReactNode } from 'react'

/**
 * One-at-a-time stepping for a review queue — the "review it like a card"
 * mode (owner: "click through the review cards with < and > and click accept
 * or not... review in a streamlined fashion").
 *
 * Deliberately a HOOK returning a slice plus a nav element, not a wrapper
 * component. Every queue panel renders its items inside its own markup —
 * `<ul>/<li>` here, a stack of `<div>` cards there — and a wrapper would
 * have had to reproduce each one. Panels instead swap `items.map` for
 * `shown.map` and drop `{nav}` above it, keeping the exact card they
 * already render, actions and all. That is the whole point: focus mode is
 * the SAME card, one at a time, not a second rendering of it that can drift.
 *
 * Advancing is a consequence of the clamp, not a separate mechanism. Acting
 * on an item (accept, reject, resolve) removes it from the refetched list,
 * so the next item slides into the index the reviewer is already sitting on
 * — a queue of 67 is cleared by pressing Accept 67 times, never touching
 * the arrows. The clamp only does visible work on the last item, where it
 * steps back rather than showing an empty frame.
 */
export function useFocusList<T>(
  items: T[],
  focus: boolean,
  /** Singular noun for the counter: "3 of 67 change requests". */
  noun: string,
): { shown: T[]; nav: ReactNode } {
  const [index, setIndex] = useState(0)
  const max = Math.max(0, items.length - 1)
  const i = Math.min(index, max)

  useEffect(() => {
    if (index > max) setIndex(max)
  }, [index, max])

  // Leaving focus mode resets to the top, so re-entering a queue doesn't
  // drop the reviewer at a position they set in a different session.
  useEffect(() => {
    if (!focus) setIndex(0)
  }, [focus])

  useEffect(() => {
    if (!focus) return
    function onKey(e: KeyboardEvent) {
      // A reviewer typing a note in a textarea is moving a cursor, not
      // moving through the queue. Without this, writing "más" jumps the
      // card out from under them mid-word.
      const el = e.target as HTMLElement | null
      const tag = el?.tagName
      if (
        tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' ||
        el?.isContentEditable
      ) {
        return
      }
      if (e.key === 'ArrowLeft') setIndex((n) => Math.max(0, n - 1))
      if (e.key === 'ArrowRight') setIndex((n) => Math.min(max, n + 1))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [focus, max])

  if (!focus || items.length === 0) return { shown: items, nav: null }

  return {
    shown: [items[i]],
    nav: (
      <div
        className="flex items-center justify-between gap-2 rounded-lg border border-gray-200 bg-gray-50 px-2 py-1.5"
        data-testid="focus-nav"
      >
        <button
          type="button"
          onClick={() => setIndex((n) => Math.max(0, n - 1))}
          disabled={i === 0}
          aria-label={`Previous ${noun}`}
          className="rounded-md border border-gray-200 bg-white px-2.5 py-1 text-sm font-semibold text-gray-600 hover:bg-gray-50 disabled:opacity-30"
        >
          ‹
        </button>
        <span className="text-xs tabular-nums text-gray-600">
          <span className="font-semibold">{i + 1}</span> of {items.length}{' '}
          {items.length === 1 ? noun : `${noun}s`}
          <span className="ms-2 hidden text-[10px] uppercase tracking-wide text-gray-400 sm:inline">
            ← → to move
          </span>
        </span>
        <button
          type="button"
          onClick={() => setIndex((n) => Math.min(max, n + 1))}
          disabled={i === max}
          aria-label={`Next ${noun}`}
          className="rounded-md border border-gray-200 bg-white px-2.5 py-1 text-sm font-semibold text-gray-600 hover:bg-gray-50 disabled:opacity-30"
        >
          ›
        </button>
      </div>
    ),
  }
}
