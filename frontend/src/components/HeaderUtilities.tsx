import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Bell, CircleUserRound, Inbox } from 'lucide-react'
import { usePrefsStore } from '../stores/prefsStore'
import { TOUR_VERSION } from '../features/onboarding/tour'
import Walkthrough from '../features/onboarding/Walkthrough'
import WhatsNewPanel from '../features/announcements/WhatsNewPanel'
import { unseenWhatsNew } from '../features/announcements/whatsNew'
import UiLanguageSwitcher from './UiLanguageSwitcher'
import StaffNotifications from '../features/contribute/StaffNotifications'
import { useReviewNotifications } from './LanguageScopePicker'

/**
 * The four utility circles — account, interface language, what's new, and
 * the tour — as one cluster, owned here so every section renders the same
 * row (owner: "no matter what tab … I want to see the four circle icons").
 *
 * They used to live inline on the Study page only, which made the other
 * three sections second-class in exactly the wrong way: the bell is how
 * changes are announced, and a learner who lives on Practice never saw the
 * badge; the globe is an escape hatch that must exist everywhere a learner
 * can be lost (see SectionHeader for that argument in full).
 *
 * The modals ride along with their buttons: a panel belongs to the thing
 * that opens it, not to whichever page happens to host the button today.
 */
export default function HeaderUtilities({
  autoOpenTour = false,
}: {
  /** Study passes true: the tour offers itself once per edition on the
   * landing page, not on every section a learner happens to open. */
  autoOpenTour?: boolean
}) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const walkthroughDone = usePrefsStore((s) => s.walkthroughDone)
  const walkthroughVersion = usePrefsStore((s) => s.walkthroughVersion)
  const whatsNewSeen = usePrefsStore((s) => s.whatsNewSeen)
  const unseenCount = unseenWhatsNew(whatsNewSeen).length
  const [showTour, setShowTour] = useState(false)
  const [showWhatsNew, setShowWhatsNew] = useState(false)
  const [showStaff, setShowStaff] = useState(false)
  // Staff only, and decided by the server: the endpoint answers a learner
  // with an empty set, so this circle simply never appears for them. The
  // four learner circles are untouched — this is a fifth, not a
  // replacement.
  const { data: staff } = useReviewNotifications()
  const staffWaiting = (staff?.review_total ?? 0) + (staff?.feedback_total ?? 0)

  // Open the feature tour once, for someone who hasn't dismissed it.
  // "Done" is per EDITION, not forever: a learner who dismissed the
  // original seven slides has never seen Speak or the level dial, so a
  // bumped TOUR_VERSION offers the tour once more (owner: "force all to
  // see the new walkthrough"). Closing it stamps the current version, so
  // this is one showing per edition, not a nag.
  useEffect(() => {
    if (!autoOpenTour) return
    if (!walkthroughDone || (walkthroughVersion ?? 0) < TOUR_VERSION) {
      setShowTour(true)
    }
  }, [autoOpenTour, walkthroughDone, walkthroughVersion])

  return (
    <>
      {/* Account as a one-tap symbol (owner): it was reachable only
          through the mobile menu or the More section — the last text-only
          destination while everything else got an icon. */}
      <button
        type="button"
        data-testid="header-account"
        onClick={() => navigate('/account')}
        aria-label={t('nav.account')}
        title={t('nav.account')}
        className="w-9 h-9 md:w-7 md:h-7 flex items-center justify-center rounded-full border border-gray-200 text-gray-500 hover:text-lang hover:border-lang/40"
      >
        <CircleUserRound aria-hidden className="h-4 w-4 md:h-3.5 md:w-3.5" />
      </button>
      <UiLanguageSwitcher />
      <button
        type="button"
        onClick={() => setShowWhatsNew(true)}
        aria-label={t('header.whatsNew')}
        title={t('header.whatsNew')}
        className="relative w-9 h-9 md:w-7 md:h-7 flex items-center justify-center rounded-full border border-gray-200 text-gray-500 hover:text-lang hover:border-lang/40 text-sm md:text-xs leading-none"
      >
        <Bell aria-hidden className="h-4 w-4 md:h-3.5 md:w-3.5" />
        {unseenCount > 0 && (
          <span
            data-testid="whats-new-badge"
            className="absolute -top-1.5 -end-1.5 min-w-4 h-4 rounded-full bg-lang text-white text-[10px] font-bold leading-4 text-center px-0.5"
          >
            {unseenCount}
          </span>
        )}
      </button>
      {staff?.is_staff && (
        <button
          type="button"
          onClick={() => setShowStaff(true)}
          data-testid="header-staff-inbox"
          aria-label="Waiting for review"
          title="What's waiting for you, in every language"
          className="relative w-9 h-9 md:w-7 md:h-7 flex items-center justify-center rounded-full border border-gray-200 text-gray-500 hover:text-lang hover:border-lang/40"
        >
          <Inbox aria-hidden className="h-4 w-4 md:h-3.5 md:w-3.5" />
          {staffWaiting > 0 && (
            <span
              data-testid="staff-inbox-badge"
              className="absolute -top-1.5 -end-1.5 min-w-4 h-4 rounded-full bg-amber-500 text-white text-[10px] font-bold leading-4 text-center px-0.5"
            >
              {staffWaiting}
            </span>
          )}
        </button>
      )}
      <button
        type="button"
        onClick={() => setShowTour(true)}
        aria-label={t('header.takeTour')}
        title={t('header.takeTour')}
        className="w-9 h-9 md:w-7 md:h-7 flex items-center justify-center rounded-full border border-gray-200 text-gray-500 hover:text-lang hover:border-lang/40 text-sm md:text-xs leading-none"
      >
        ?
      </button>
      {showTour && <Walkthrough onClose={() => setShowTour(false)} />}
      {showWhatsNew && <WhatsNewPanel onClose={() => setShowWhatsNew(false)} />}
      {showStaff && <StaffNotifications onClose={() => setShowStaff(false)} />}
    </>
  )
}
