import { useState } from 'react'
import type { StageName } from '../../api/types'

const MAIN_STAGES: { key: StageName; label: string; tone: string }[] = [
  { key: 'beginner', label: 'Beginner', tone: 'bg-slate-900 text-white' },
  { key: 'adept', label: 'Adept', tone: 'bg-indigo-800 text-white' },
  { key: 'seasoned', label: 'Seasoned', tone: 'bg-lang text-white' },
  { key: 'expert', label: 'Expert', tone: 'bg-lang/70 text-white' },
  { key: 'master', label: 'Master', tone: 'bg-lang/25 text-lang-dark' },
]

const EXTRA_STAGES: { key: StageName; label: string }[] = [
  { key: 'self_study', label: 'Self-Study' },
  { key: 'ghost', label: 'Ghosts' },
]

/**
 * Bunpro-style named-stage tiles mapped from FSRS stability bands, with a
 * Grammar/Vocab toggle. Ghosts are relearning cards still haunting the queue.
 */
export default function StageTiles({
  stages,
}: {
  stages: Record<'vocab' | 'grammar', Record<StageName, number>>
}) {
  const [kind, setKind] = useState<'grammar' | 'vocab'>('grammar')
  const counts = stages[kind]
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xs uppercase tracking-wide text-gray-400">Progress</h2>
        <div className="flex rounded-lg border border-gray-200 overflow-hidden text-xs">
          {(['grammar', 'vocab'] as const).map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setKind(k)}
              className={`px-3 py-1 capitalize ${
                kind === k ? 'bg-lang text-white' : 'bg-white text-gray-500 hover:bg-gray-50'
              }`}
            >
              {k}
            </button>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-5 gap-2">
        {MAIN_STAGES.map((s) => (
          <div key={s.key} className={`rounded-xl p-3 ${s.tone}`}>
            <span className="block text-[10px] uppercase tracking-wide opacity-80">
              {s.label}
            </span>
            <span className="block text-xl font-bold tabular-nums">
              {counts[s.key] ?? 0}
            </span>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2 mt-2">
        {EXTRA_STAGES.map((s) => (
          <div key={s.key} className="rounded-xl p-3 bg-gray-100 text-gray-600">
            <span className="block text-[10px] uppercase tracking-wide opacity-80">
              {s.label}
            </span>
            <span className="block text-xl font-bold tabular-nums">
              {counts[s.key] ?? 0}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
