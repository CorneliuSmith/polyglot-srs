import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BookOpen, Dumbbell, MessagesSquare } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { getGymManifest } from '../../api/gym'
import { usePrefsStore } from '../../stores/prefsStore'
import DirArrow from '../../components/DirArrow'
import SectionHeader from '../../components/SectionHeader'
import NewPicksPrompt from '../recommendations/NewPicksPrompt'
import PersonalDecksSection from '../decks/PersonalDecksSection'

function FeatureTile({
  icon: Icon,
  label,
  caption,
  testId,
  onClick,
  disabled = false,
}: {
  icon: LucideIcon
  label: string
  caption: string
  testId: string
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className="rounded-2xl border-2 border-lang/20 bg-white hover:border-lang hover:bg-lang-soft/40 disabled:opacity-50 p-3 text-center transition-colors"
      style={{ minHeight: '44px' }}
    >
      <Icon aria-hidden className="mx-auto h-7 w-7 text-lang" strokeWidth={1.75} />
      <span className="block mt-1.5 text-sm font-bold text-gray-900">{label}</span>
      <span className="block mt-0.5 text-[11px] leading-tight text-gray-500">
        {caption}
      </span>
    </button>
  )
}

function LinkRow({
  title,
  sub,
  onClick,
  disabled = false,
  testId,
}: {
  title: string
  sub: string
  onClick: () => void
  disabled?: boolean
  testId?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className="w-full bg-white hover:bg-gray-50 disabled:opacity-50 text-gray-800 font-semibold rounded-xl px-6 py-3 text-sm border border-gray-200 transition-colors text-start flex items-center justify-between"
      style={{ minHeight: '44px' }}
    >
      <span>
        {title}
        <span className="block text-xs font-normal text-gray-500">{sub}</span>
      </span>
      <DirArrow className="text-lang" />
    </button>
  )
}

/**
 * The optional extras, separated from the daily loop.
 *
 * Gym, Read and Tutor used to sit on the dashboard as tiles AND in the
 * header nav, so the same three destinations existed at two levels with
 * different affordances. They live here now, with the other things a
 * learner reaches for when they want more than their reviews: their own
 * cards, the grammar path, their own text, and this week's picks.
 */
export default function PracticePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  // No form categories means an uninflected language — no Gym to offer.
  const { data: gymManifest } = useQuery({
    queryKey: ['gym-manifest', activeLanguageId],
    queryFn: () => getGymManifest(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
  })
  const hasGym = (gymManifest?.columns.length ?? 0) > 0

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-4 pb-24 md:pb-6">
        <SectionHeader title={t('nav.practice')} />

        <div
          data-testid="feature-tiles"
          className={`grid gap-3 ${hasGym ? 'grid-cols-3' : 'grid-cols-2'}`}
        >
          {hasGym && (
            <FeatureTile
              icon={Dumbbell}
              label={t('nav.gym')}
              caption={t('dashboard.gymCaption')}
              testId="tile-gym"
              onClick={() => navigate('/gym')}
            />
          )}
          <FeatureTile
            icon={BookOpen}
            label={t('nav.read')}
            caption={t('dashboard.readCaption')}
            testId="tile-read"
            onClick={() => navigate('/read')}
            disabled={!activeLanguageId}
          />
          <FeatureTile
            icon={MessagesSquare}
            label={t('nav.tutor')}
            caption={t('dashboard.tutorCaption')}
            testId="tile-tutor"
            onClick={() => navigate('/tutor')}
            disabled={!activeLanguageId}
          />
        </div>

        <LinkRow
          title={t('dashboard.grammarPathTitle')}
          sub={t('dashboard.grammarPathSub')}
          onClick={() => navigate('/grammar')}
          disabled={!activeLanguageId}
          testId="row-grammar"
        />
        <LinkRow
          title={t('dashboard.ownTextTitle')}
          sub={t('dashboard.ownTextSub')}
          onClick={() => navigate('/notes')}
          disabled={!activeLanguageId}
          testId="row-notes"
        />
        {/* The reco entry moved to the Study page + desktop rail (owner:
            recommendations are not practice). The new-picks nudge stays —
            it's a transient "this week's batch is in" prompt, not a
            destination. */}
        <NewPicksPrompt />

        {activeLanguageId && <PersonalDecksSection languageId={activeLanguageId} />}
      </div>
    </div>
  )
}
