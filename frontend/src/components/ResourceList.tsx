import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { setReferenceRead } from '../api/curriculum'
import type { ReferenceLink } from '../api/types'

/** The read-tracking key for one reference: its url, or its title for books. */
function refKey(ref: ReferenceLink): string {
  return ref.url ?? ref.title
}

/**
 * Bunpro-style Resources section: references split into Online (links) and
 * Offline (book + page), each with a per-user read mark. Read state is
 * optimistic — the check flips immediately and the server catches up.
 *
 * Render with `key={pointId}` so the local read-set reseeds per point.
 */
export default function ResourceList({
  pointId,
  references,
  readRefs = [],
}: {
  /** grammar point id — omit to render without read-tracking (e.g. vocab) */
  pointId?: string
  references: ReferenceLink[]
  readRefs?: string[]
}) {
  const [read, setRead] = useState<Set<string>>(() => new Set(readRefs))
  const toggleMutation = useMutation({
    mutationFn: ({ key, next }: { key: string; next: boolean }) =>
      setReferenceRead(pointId!, key, next),
  })

  if (references.length === 0) return null
  const online = references.filter((r) => r.url)
  const offline = references.filter((r) => !r.url && r.book)

  const toggle = (key: string) => {
    if (!pointId) return
    const next = !read.has(key)
    setRead((prev) => {
      const copy = new Set(prev)
      if (next) copy.add(key)
      else copy.delete(key)
      return copy
    })
    toggleMutation.mutate({ key, next })
  }

  const ReadMark = ({ k }: { k: string }) =>
    pointId ? (
      <button
        type="button"
        onClick={() => toggle(k)}
        aria-pressed={read.has(k)}
        aria-label={read.has(k) ? 'Mark unread' : 'Mark read'}
        title={read.has(k) ? 'Mark unread' : 'Mark read'}
        className={`shrink-0 w-5 h-5 rounded-full border flex items-center justify-center text-[11px] leading-none transition ${
          read.has(k)
            ? 'bg-green-500 border-green-500 text-white'
            : 'border-gray-300 text-transparent hover:border-green-400 hover:text-green-300'
        }`}
      >
        ✓
      </button>
    ) : null

  const group = (label: string, items: ReferenceLink[]) =>
    items.length > 0 && (
      <div>
        <span className="block text-[10px] uppercase tracking-wide text-gray-400 mb-1">
          {label}
        </span>
        <ul className="space-y-1.5">
          {items.map((ref) => {
            const k = refKey(ref)
            const isRead = read.has(k)
            return (
              <li key={k} className="flex items-center gap-2">
                <ReadMark k={k} />
                {ref.url ? (
                  <a
                    href={ref.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`hover:underline ${
                      isRead ? 'text-gray-400' : 'text-lang'
                    }`}
                  >
                    {ref.title}
                  </a>
                ) : (
                  <span className={isRead ? 'text-gray-400' : 'text-gray-700'}>
                    {ref.title}
                    <span className="text-gray-400">
                      {' — '}
                      {ref.book}
                      {ref.page ? `, p. ${ref.page}` : ''}
                    </span>
                  </span>
                )}
              </li>
            )
          })}
        </ul>
      </div>
    )

  return (
    <div>
      <h3 className="font-semibold text-gray-700 mb-1">Resources</h3>
      <div className="space-y-2">
        {group('Online', online)}
        {group('Offline', offline)}
      </div>
    </div>
  )
}
