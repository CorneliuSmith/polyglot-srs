import type { StageName } from '../api/types'

// Same palette as the dashboard's stage tiles so a card wears one color
// everywhere.
const STAGE_STYLES: Record<StageName, { label: string; tone: string }> = {
  beginner: { label: 'Beginner', tone: 'bg-slate-900 text-white' },
  adept: { label: 'Adept', tone: 'bg-indigo-800 text-white' },
  seasoned: { label: 'Seasoned', tone: 'bg-lang text-white' },
  expert: { label: 'Expert', tone: 'bg-lang/70 text-white' },
  master: { label: 'Master', tone: 'bg-lang/25 text-lang-dark' },
  self_study: { label: 'Self-Study', tone: 'bg-gray-200 text-gray-700' },
  ghost: { label: 'Ghost', tone: 'bg-purple-100 text-purple-700' },
}

/** Named SRS stage pill; `stage: null` renders a "Not studied" outline. */
export default function StageBadge({ stage }: { stage: StageName | null }) {
  if (!stage) {
    return (
      <span className="text-[10px] uppercase tracking-wide rounded-full px-2 py-0.5 border border-gray-200 text-gray-400">
        Not studied
      </span>
    )
  }
  const s = STAGE_STYLES[stage]
  return (
    <span
      className={`text-[10px] uppercase tracking-wide rounded-full px-2 py-0.5 ${s.tone}`}
    >
      {s.label}
    </span>
  )
}
