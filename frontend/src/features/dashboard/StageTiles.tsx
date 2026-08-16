import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { StageName } from '../../api/types'

// The five tiles walk through the active language's flag palette
// (stage tokens are set by LanguageThemeApplier — see stageRamp).
const MAIN_STAGES: { key: StageName; label: string; tone: string }[] = [
  { key: 'beginner', label: 'stages.beginner', tone: 'bg-stage-1 text-stage-1-on' },
  { key: 'adept', label: 'stages.adept', tone: 'bg-stage-2 text-stage-2-on' },
  { key: 'seasoned', label: 'stages.seasoned', tone: 'bg-stage-3 text-stage-3-on' },
  { key: 'expert', label: 'stages.expert', tone: 'bg-stage-4 text-stage-4-on' },
  { key: 'master', label: 'stages.master', tone: 'bg-stage-5 text-stage-5-on' },
]

const EXTRA_STAGES: { key: StageName; label: string }[] = [
  { key: 'self_study', label: 'stages.selfStudy' },
  { key: 'ghost', label: 'stages.ghosts' },
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
  const { t } = useTranslation()
  const [kind, setKind] = useState<'grammar' | 'vocab'>('grammar')
  const counts = stages[kind]
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xs uppercase tracking-wide text-gray-500">{t('dashboard.progressTitle')}</h2>
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
              {k === 'grammar' ? t('common.grammar') : t('common.vocab')}
            </button>
          ))}
        </div>
      </div>
      {/* 3-up on phones (5-up squeezed "SEASONED" into ~64px — beta
          screenshot 2026-07-17), 5-up from md. */}
      <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
        {MAIN_STAGES.map((s) => (
          <div key={s.key} className={`rounded-xl p-3 min-w-0 ${s.tone}`}>
            <span className="block text-[10px] uppercase tracking-wide opacity-80 truncate">
              {t(s.label)}
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
              {t(s.label)}
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
