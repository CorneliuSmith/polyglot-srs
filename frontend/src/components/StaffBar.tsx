import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronUp, SquarePen } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { canSuggestForLanguage, getMyRoles } from '../api/contribute'
import { usePrefsStore } from '../stores/prefsStore'
import { useReviewModeStore } from '../stores/reviewModeStore'
import { useViewAsKey } from '../stores/viewAsStore'
import ViewAsBar from './ViewAsBar'

/**
 * The one strip of staff chrome above every authenticated page. Two controls,
 * both persistent and both sticky:
 *
 *   Review Mode — any reviewer / contributor / admin. Turns on click-to-flag
 *                 across cards, tutor replies and readings.
 *   View as     — admins only. Previews the app at each access level.
 *
 * Together in one bar on purpose: separately they'd be two competing strips
 * at the top of a phone screen, and both are "I am here as staff right now"
 * controls. Renders nothing at all for a plain learner.
 */
export default function StaffBar() {
  const { t } = useTranslation()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const reviewMode = useReviewModeStore((s) => s.reviewMode)
  const setReviewMode = useReviewModeStore((s) => s.setReviewMode)

  // Keyed by preview level, NOT ViewAsBar's ['my-roles-real']. Sharing that
  // entry meant Review Mode was decided by whichever level happened to fetch
  // it first and then sat in cache for five minutes — so the strip stayed on
  // (or off) no matter which role you previewed.
  const { data } = useQuery({
    queryKey: ['my-roles', useViewAsKey()],
    queryFn: getMyRoles,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  // Review Mode follows the ACTIVE language: a reviewer for Spanish gets no
  // flag affordance while studying Turkish, because the endpoint would
  // reject the flag anyway.
  // Session-scoped rather than persisted: a staff member who opens it
  // wants it for that sitting, not forever, and forgetting is the safer
  // default for a mode that changes what taps do.
  const [collapsed, setCollapsed] = useState(true)
  const canReview =
    !!data && canSuggestForLanguage(data.roles ?? [], activeLanguageId)

  return (
    <>
      <ViewAsBar />
      {canReview && (
        <div
          data-testid="staff-bar"
          className={
            'sticky top-0 z-30 border-b ' +
            (reviewMode
              ? 'border-amber-300 bg-amber-100 text-amber-900'
              : 'border-gray-200 bg-gray-50 text-gray-600')
          }
        >
          {/* Collapsed by default. This is scaffolding for a handful of
              staff, and expanded it took the top of EVERY screen on a
              phone — including while testing as a learner, which is
              exactly when it should be least in the way. It stays visible
              as a chip so it's never lost, and it forces itself open while
              review mode is ON: a flagging mode you can't see you're in is
              worse than a bar you didn't want. */}
          {collapsed && !reviewMode ? (
            <div className="max-w-3xl mx-auto px-4 py-1">
              <button
                type="button"
                onClick={() => setCollapsed(false)}
                data-testid="staff-bar-expand"
                aria-expanded={false}
                className="flex items-center gap-1.5 text-[11px] opacity-70 hover:opacity-100"
              >
                <SquarePen aria-hidden className="h-3 w-3" />
                {t('staffBar.reviewMode')}
              </button>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto flex items-center gap-2 px-4 py-1.5 text-xs">
              <label className="flex items-center gap-2 min-w-0 flex-1">
                <SquarePen aria-hidden className="h-3.5 w-3.5 shrink-0" />
                <span className="font-medium">{t('staffBar.reviewMode')}</span>
                <input
                  type="checkbox"
                  checked={reviewMode}
                  onChange={(e) => setReviewMode(e.target.checked)}
                  className="h-4 w-4 accent-amber-600"
                />
                <span className="min-w-0 flex-1 truncate opacity-80">
                  {reviewMode ? t('staffBar.flagOn') : t('staffBar.flagOff')}
                </span>
              </label>
              {!reviewMode && (
                <button
                  type="button"
                  onClick={() => setCollapsed(true)}
                  data-testid="staff-bar-collapse"
                  aria-expanded
                  aria-label={t('staffBar.collapse')}
                  className="shrink-0 opacity-70 hover:opacity-100"
                >
                  <ChevronUp aria-hidden className="h-4 w-4" />
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </>
  )
}
