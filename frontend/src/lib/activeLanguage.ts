import { updateProfile } from '../api/profile'
import { usePrefsStore } from '../stores/prefsStore'

/**
 * The study language follows the account, exactly like ui_language does
 * (see i18n/index.ts). The prefs store's activeLanguageId is a device
 * cache of profile.active_language_id — the picker already WROTE every
 * change to the profile, but nothing ever read it back once this device
 * had any value at all, so two devices could study different courses
 * forever. Owner: "What the user is studying and the language should
 * follow once the device reloads the page."
 *
 * Same two-piece design as the UI language: every explicit switch goes
 * through chooseActiveLanguage (device + account in one call), and the
 * profile heartbeat calls syncActiveLanguageFromProfile to pull other
 * devices' decisions in.
 */

/** When the user last switched course ON THIS DEVICE. A profile read that
 * started before the switch may resolve after it — and must not bounce
 * them back to the course they just left. */
let lastExplicitChangeAt = 0
const EXPLICIT_GRACE_MS = 15_000

/** Test-only: a switch in one test must not hold the grace window open
 * for the next. */
export function __resetActiveLanguageSyncForTests() {
  lastExplicitChangeAt = 0
}

/** The user decided to study this language: apply it here, save it to the
 * account so every other device follows. The profile write failing is
 * non-fatal — this device is right either way, and the next successful
 * write wins. */
export function chooseActiveLanguage(id: string) {
  lastExplicitChangeAt = Date.now()
  usePrefsStore.getState().setActiveLanguageId(id)
  updateProfile({ active_language_id: id }).catch(() => {
    // Non-fatal
  })
}

/** Follow the account. Called with each profile read (ProfileLanguageSync's
 * focus + heartbeat refetches); adopts the account's course when it differs
 * from this device's. Null/absent means the account never chose — never
 * un-choose locally over that. */
export function syncActiveLanguageFromProfile(
  activeLanguageId: string | null | undefined,
) {
  if (!activeLanguageId) return
  // A switch made seconds ago on THIS device outranks a profile read that
  // may predate it; the switch's own save then makes the two agree.
  if (Date.now() - lastExplicitChangeAt < EXPLICIT_GRACE_MS) return
  const store = usePrefsStore.getState()
  if (store.activeLanguageId !== activeLanguageId) {
    store.setActiveLanguageId(activeLanguageId)
  }
}
