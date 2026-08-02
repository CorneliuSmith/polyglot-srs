import { useTranslation } from 'react-i18next'
import type { StageName } from '../api/types'

// Same palette as the dashboard's stage tiles so a card wears one color
// everywhere. Labels come from the `stages.*` i18n keys.
const STAGE_STYLES: Record<StageName, { labelKey: string; tone: string }> = {
  beginner: { labelKey: 'stages.beginner', tone: 'bg-stage-1 text-stage-1-on' },
  adept: { labelKey: 'stages.adept', tone: 'bg-stage-2 text-stage-2-on' },
  seasoned: { labelKey: 'stages.seasoned', tone: 'bg-stage-3 text-stage-3-on' },
  expert: { labelKey: 'stages.expert', tone: 'bg-stage-4 text-stage-4-on' },
  master: { labelKey: 'stages.master', tone: 'bg-stage-5 text-stage-5-on' },
  self_study: { labelKey: 'stages.selfStudy', tone: 'bg-gray-200 text-gray-700' },
  ghost: { labelKey: 'stages.ghost', tone: 'bg-purple-100 text-purple-700' },
}

/** Named SRS stage pill; `stage: null` renders a "Not studied" outline. */
export default function StageBadge({ stage }: { stage: StageName | null }) {
  const { t } = useTranslation()
  if (!stage) {
    return (
      <span className="text-[10px] uppercase tracking-wide rounded-full px-2 py-0.5 border border-gray-200 text-gray-400">
        {t('stages.notStudied')}
      </span>
    )
  }
  const s = STAGE_STYLES[stage]
  return (
    <span
      className={`text-[10px] uppercase tracking-wide rounded-full px-2 py-0.5 ${s.tone}`}
    >
      {t(s.labelKey)}
    </span>
  )
}
