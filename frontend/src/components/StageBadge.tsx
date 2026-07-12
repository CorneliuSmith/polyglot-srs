import type { StageName } from '../api/types'

// Same palette as the dashboard's stage tiles so a card wears one color
// everywhere.
const STAGE_STYLES: Record<StageName, { label: string; tone: string }> = {
  beginner: { label: 'Beginner', tone: 'bg-stage-1 text-stage-1-on' },
  adept: { label: 'Adept', tone: 'bg-stage-2 text-stage-2-on' },
  seasoned: { label: 'Seasoned', tone: 'bg-stage-3 text-stage-3-on' },
  expert: { label: 'Expert', tone: 'bg-stage-4 text-stage-4-on' },
  master: { label: 'Master', tone: 'bg-stage-5 text-stage-5-on' },
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
