/**
 * The in-app changelog (beta request: "notifications to tell users about
 * these new features"). The walkthrough only fires once for NEW users —
 * this is how EXISTING users hear about what shipped since.
 *
 * Add new entries at the TOP. Ids are permanent (they're what "seen" is
 * recorded against). All copy — date, title, body, link label — lives in
 * the i18n catalogs under `whatsNew.entries.<id>.*`; `linkLabel` is a
 * GETTER that resolves through the i18n singleton at access time, so it
 * follows the site language instead of baking English in at import.
 */
import i18n from '../../i18n'

export interface WhatsNewEntry {
  id: string
  link?: string
  /** Localized label for the try-it link, resolved at access time. */
  readonly linkLabel?: string
}

// Object-literal getter (NOT a spread — spreading would invoke the getter
// once at module load and freeze the English rendering).
const linked = (id: string, link: string): WhatsNewEntry => ({
  id,
  link,
  get linkLabel() {
    return i18n.t(`whatsNew.entries.${id}.linkLabel`)
  },
})

export const WHATS_NEW: WhatsNewEntry[] = [
  linked('placement-retake-2026-07', '/settings'),
  linked('language-facts-2026-07', '/about'),
  linked('gym-adaptive-2026-07', '/gym'),
  linked('learning-tips-2026-07', '/account'),
  { id: 'review-audio-2026-07' },
  linked('korean-2026-07', '/account'),
  linked('gym-2026-07', '/gym'),
  { id: 'listening-gap-2026-07' },
  linked('daily-learn-goal-2026-07', '/account'),
  linked('email-reminders-2026-07', '/account'),
]

/** Ids the learner has not opened the panel over yet. */
export function unseenWhatsNew(seen: string[] | undefined): WhatsNewEntry[] {
  const s = seen ?? []
  return WHATS_NEW.filter((e) => !s.includes(e.id))
}
