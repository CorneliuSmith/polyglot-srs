import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { allTipsSeen } from '../features/tips/tips'

export type Theme = 'system' | 'light' | 'dark'

/**
 * How Speak should behave as a conversation (owner: "create options that
 * provide users real convo situations").
 *
 * Four independent switches rather than one "hands-free" mode, because they
 * fail differently: a learner in a quiet room may want the partner to speak
 * without wanting the microphone armed, and someone practising listening
 * wants the text hidden whether or not anything is automatic.
 *
 * Every one defaults OFF, so the conversation behaves exactly as it does
 * today until somebody asks for more.
 */
export interface SpeakConversationPrefs {
  /** Play the partner's line as it arrives instead of waiting for a tap. */
  autoSpeak: boolean
  /** Hide the partner's words — listen first, reveal if you need to. */
  hideText: boolean
  /** Start listening as soon as the partner has finished. */
  autoListen: boolean
  /** Send when the learner stops talking, without a tap. */
  autoSend: boolean
}

const SPEAK_CONVERSATION_DEFAULTS: SpeakConversationPrefs = {
  autoSpeak: false,
  hideText: false,
  autoListen: false,
  autoSend: false,
}

interface PrefsState {
  activeLanguageId: string | null
  setActiveLanguageId: (id: string) => void
  // Theme switcher (WP13h): 'system' follows the OS. Applied by ThemeApplier
  // (and pre-applied by the inline script in index.html to avoid a flash).
  theme: Theme
  setTheme: (theme: Theme) => void
  // Which visual direction this account was served, cached from the last
  // profile load. The SERVER decides (see lib/uiSkin.ts) — this copy exists
  // only so the inline script in index.html can paint the first frame in
  // the right skin instead of flashing Classic and swapping.
  uiSkin: string | null
  setUiSkin: (variant: string | null) => void
  // How many cards a review session pulls (the server clamps to 1–100).
  sessionSize: number
  setSessionSize: (n: number) => void
  // Hint disclosure level during reviews (0 = nothing revealed). Persisted:
  // the level the learner chose last time carries over to the next card and
  // the next session. Defaults to ALL layers revealed (beta report: a bare
  // "Tengo tres ___." is unanswerable — nobody found the hint dots); the
  // dots cycle back to fewer for learners who want the harder mode.
  hintLevel: number
  setHintLevel: (level: number) => void
  // QWERTY transliteration input per language code (ru/ar/el). Absent =
  // enabled — typing Latin and getting the target script is the baseline;
  // learners with a real native keyboard opt out.
  qwertyTranslit: Record<string, boolean>
  setQwertyTranslit: (code: string, on: boolean) => void
  // Arabic short vowels (tashkeel): show the fully vocalized form (كَتَبَ)
  // under new words. Default ON — learners meet every word vocalized first;
  // turning it off practises reading bare script like native materials.
  showTashkeel: boolean
  setShowTashkeel: (on: boolean) => void
  // Listening mode (WP19a): cloze drills play the audio and hide the
  // sentence — the learner types the missing word by ear. Persisted like
  // hintLevel: the chosen mode carries across cards and sessions.
  listeningMode: boolean
  setListeningMode: (on: boolean) => void
  // Accents optional (beta request): when on, a diacritic-only miss
  // ("quien" for "quién") counts as fully correct instead of "Almost —
  // check the accents". Applied client-side by remapping correct_sloppy →
  // correct before it drives feedback and the SRS grade.
  accentsOptional: boolean
  setAccentsOptional: (on: boolean) => void
  // First-run feature tour. Undefined until the learner finishes or dismisses
  // it with "don't show again"; the dashboard auto-opens it once while unset.
  walkthroughDone: boolean
  setWalkthroughDone: (done: boolean) => void
  // Which EDITION of the tour they have seen (features/onboarding/tour.ts
  // TOUR_VERSION). "Done" only ever meant "done with the tour that existed
  // then", so a tour that gains Speak and the level dial has to be offered
  // again — the owner: "force all to see the new walkthrough". 0 = never
  // seen this scheme; the dashboard reopens the tour whenever this trails
  // the current version, and finishing writes the current one.
  walkthroughVersion: number
  setWalkthroughVersion: (version: number) => void
  // "Install the app" banner (PWA): once dismissed, stays gone.
  installPromptDismissed: boolean
  setInstallPromptDismissed: (done: boolean) => void
  // Daily learn goal (beta request): the Learn tile shows progress toward a
  // small daily target instead of the whole queue count ("538 queued" was
  // overwhelming). 0 = no goal, show the full queue.
  dailyLearnGoal: number
  setDailyLearnGoal: (n: number) => void
  // What's-new entry ids the learner has already opened the panel over.
  // Drives the unseen-count badge on the dashboard.
  whatsNewSeen: string[]
  markWhatsNewSeen: (ids: string[]) => void
  // Learning tips (evidence-based study nudges). Default ON. seenTipIds avoids
  // repeats until the whole set has been seen (then it resets and cycles);
  // lastTipShownAt throttles them to ~once a day regardless of how often the
  // learner opens the app.
  learningTipsEnabled: boolean
  setLearningTipsEnabled: (on: boolean) => void
  seenTipIds: string[]
  lastTipShownAt: number
  recordTipShown: (id: string) => void
  // Day number (see tips.dayNumber) the learner last closed the Study page's
  // tip of the day. That tip is always present rather than throttled, so
  // closing it needs to mean "not today" — otherwise the only way to be rid
  // of it for an afternoon is to switch tips off entirely.
  tipDismissedDay: number
  dismissTipForToday: (day: number) => void
  // Language ids where the learner has waved off the first-time placement
  // offer. Server-side attempt history says whether they've EVER placed;
  // this says whether they've already said "not now" to being asked. Kept
  // client-side on purpose — declining an offer isn't account state, and it
  // shouldn't cost a write.
  placementOfferDismissed: string[]
  dismissPlacementOffer: (languageId: string) => void
  // Newest feedback timestamp the staff member has already been shown a
  // prompt for. Client-side like the walkthrough and the what's-new badge:
  // "have I looked at this yet" is a per-person, per-device question, and
  // making it account state would mean a write on every dashboard load and a
  // migration for something a dismissed banner already answers.
  feedbackSeenAt: string | null
  markFeedbackSeen: (isoTimestamp: string | null) => void
  // Learner-chosen stat widgets under the Study bar (owner: iPhone-style
  // slots). Ordered widget ids, at most two; empty slots offer "+ Add".
  // Device-local like the theme — which chart you like glancing at is not
  // account state.
  dashboardWidgets: string[]
  setDashboardWidgets: (ids: string[]) => void
  // Speak's conversation options (see SpeakConversationPrefs). Device-local
  // like listeningMode: whether your phone talks out loud in a quiet office
  // is a fact about the room you're in, not about your account.
  speakConversation: SpeakConversationPrefs
  setSpeakConversation: (patch: Partial<SpeakConversationPrefs>) => void
}

export const usePrefsStore = create<PrefsState>()(
  persist(
    (set) => ({
      activeLanguageId: null,
      setActiveLanguageId: (id) => set({ activeLanguageId: id }),
      theme: 'system' as Theme,
      setTheme: (theme) => set({ theme }),
      uiSkin: null,
      setUiSkin: (uiSkin) => set({ uiSkin }),
      sessionSize: 20,
      setSessionSize: (n) => set({ sessionSize: n }),
      // 9 = "everything this card has" (clamped to the card's layer count).
      hintLevel: 9,
      setHintLevel: (level) => set({ hintLevel: level }),
      qwertyTranslit: {},
      setQwertyTranslit: (code, on) =>
        set((s) => ({ qwertyTranslit: { ...s.qwertyTranslit, [code]: on } })),
      showTashkeel: true,
      setShowTashkeel: (on) => set({ showTashkeel: on }),
      listeningMode: false,
      setListeningMode: (on) => set({ listeningMode: on }),
      accentsOptional: false,
      setAccentsOptional: (on) => set({ accentsOptional: on }),
      walkthroughDone: false,
      setWalkthroughDone: (done) => set({ walkthroughDone: done }),
      walkthroughVersion: 0,
      setWalkthroughVersion: (version) => set({ walkthroughVersion: version }),
      installPromptDismissed: false,
      setInstallPromptDismissed: (done) => set({ installPromptDismissed: done }),
      dailyLearnGoal: 20,
      setDailyLearnGoal: (n) => set({ dailyLearnGoal: n }),
      whatsNewSeen: [],
      markWhatsNewSeen: (ids) =>
        set((s) => ({
          whatsNewSeen: Array.from(new Set([...s.whatsNewSeen, ...ids])),
        })),
      learningTipsEnabled: true,
      setLearningTipsEnabled: (on) => set({ learningTipsEnabled: on }),
      seenTipIds: [],
      lastTipShownAt: 0,
      recordTipShown: (id) =>
        set((s) => {
          const seen = s.seenTipIds.includes(id)
            ? s.seenTipIds
            : [...s.seenTipIds, id]
          // Once every tip has been seen, clear the list so the rotation starts
          // fresh instead of repeating at random forever.
          return {
            seenTipIds: allTipsSeen(seen) ? [] : seen,
            lastTipShownAt: Date.now(),
          }
        }),
      tipDismissedDay: 0,
      dismissTipForToday: (day) => set({ tipDismissedDay: day }),
      placementOfferDismissed: [],
      dismissPlacementOffer: (languageId) =>
        set((s) => ({
          placementOfferDismissed: s.placementOfferDismissed.includes(languageId)
            ? s.placementOfferDismissed
            : [...s.placementOfferDismissed, languageId],
        })),
      feedbackSeenAt: null,
      markFeedbackSeen: (isoTimestamp) => set({ feedbackSeenAt: isoTimestamp }),
      dashboardWidgets: [],
      setDashboardWidgets: (ids) => set({ dashboardWidgets: ids.slice(0, 2) }),
      speakConversation: { ...SPEAK_CONVERSATION_DEFAULTS },
      setSpeakConversation: (patch) =>
        set((s) => ({
          // Spread over the defaults, not just over the stored value: a
          // profile persisted before this existed has no object at all, and
          // an older one may be missing a switch added later.
          speakConversation: {
            ...SPEAK_CONVERSATION_DEFAULTS,
            ...s.speakConversation,
            ...patch,
          },
        })),
    }),
    {
      name: 'polyglot-prefs',
      // v1: hints default ON. One-time bump for existing accounts whose
      // persisted level is the old hidden default — learners who prefer
      // the hard mode cycle the dots back to 0 once.
      version: 1,
      migrate: (persisted, version) => {
        const state = persisted as Partial<PrefsState>
        if (version < 1 && (state.hintLevel ?? 0) === 0) {
          state.hintLevel = 9
        }
        return state as PrefsState
      },
    },
  ),
)
