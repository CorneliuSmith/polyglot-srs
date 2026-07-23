/**
 * The in-app changelog (beta request: "notifications to tell users about
 * these new features"). The walkthrough only fires once for NEW users —
 * this is how EXISTING users hear about what shipped since.
 *
 * Add new entries at the TOP. Ids are permanent (they're what "seen" is
 * recorded against); dates are display-only.
 */
export interface WhatsNewEntry {
  id: string
  date: string
  title: string
  body: string
  link?: string
  linkLabel?: string
}

export const WHATS_NEW: WhatsNewEntry[] = [
  {
    id: 'language-facts-2026-07',
    date: 'July 2026',
    title: 'Things to know about this language 🌍',
    body:
      'A one-minute primer on the language you’re studying — its family, ' +
      'where it’s spoken, how its sentences are built, a short history, and ' +
      'what makes it distinctive. Right next to Letters & Sounds on your ' +
      'dashboard.',
    link: '/about',
    linkLabel: 'Read about your language',
  },
  {
    id: 'gym-adaptive-2026-07',
    date: 'July 2026',
    title: 'The Gym adapts to you 🎯',
    body:
      'The Gym now learns from how you answer: forms you keep missing (and ' +
      'irregulars) come back more often, forms you’ve nailed fade. Opt into ' +
      'fresh sentences and it drafts brand-new drills in the background and ' +
      'weaves them into your set — no waiting.',
    link: '/gym',
    linkLabel: 'Open the Gym',
  },
  {
    id: 'learning-tips-2026-07',
    date: 'July 2026',
    title: 'Learning tips 💡',
    body:
      'Occasional, evidence-based nudges on how to study — read aloud, trust ' +
      'the spacing, mix it up — shown at most about once a day. Not for you? ' +
      'One switch in Settings turns them off.',
    link: '/account',
    linkLabel: 'Manage tips',
  },
  {
    id: 'review-audio-2026-07',
    date: 'July 2026',
    title: 'Clearer, faster review audio 🔊',
    body:
      'After you answer, the “word” and “full sentence” buttons are now ' +
      'labelled apart, and both clips are pre-loaded so they play the instant ' +
      'you tap — no more waiting on the sound.',
  },
  {
    id: 'korean-2026-07',
    date: 'July 2026',
    title: 'Korean 🇰🇷',
    body:
      'Language #20 is live: 7,000 words, a 40-point grammar path from ' +
      'particles to honorifics, Hangul in Letters & Sounds, neural audio, ' +
      'the tutor, the Reader, and its own Gym. 한국어를 배워요!',
    link: '/account',
    linkLabel: 'Add Korean',
  },
  {
    id: 'gym-2026-07',
    date: 'July 2026',
    title: 'The Gym 🏋️',
    body:
      'Pick the forms you want to train — past tense, accusative, ' +
      'whatever your language has — and drill them in a mixed bag. ' +
      'Stuck mid-question? Peek at the full conjugation chart. ' +
      'Russian first; more languages are on the way.',
    link: '/gym',
    linkLabel: 'Open the Gym',
  },
  {
    id: 'listening-gap-2026-07',
    date: 'July 2026',
    title: 'Listening mode marks the gap',
    body:
      'The audio now pauses where the missing word belongs, and the ' +
      'sentence shape shows the blank — no more guessing where the ' +
      'word fell out.',
  },
  {
    id: 'daily-learn-goal-2026-07',
    date: 'July 2026',
    title: 'A daily Learn goal',
    body:
      'The Learn tile now counts toward a small daily target instead ' +
      'of showing the whole queue. Set it to 20, 50, or the full queue ' +
      'in Settings.',
    link: '/account',
    linkLabel: 'Change my goal',
  },
  {
    id: 'email-reminders-2026-07',
    date: 'July 2026',
    title: 'Email review reminders',
    body:
      'Opt in to a daily digest of what is waiting for you — reviews ' +
      'due, streak status, one click back into the app.',
    link: '/account',
    linkLabel: 'Turn on reminders',
  },
]

/** Ids the learner has not opened the panel over yet. */
export function unseenWhatsNew(seen: string[] | undefined): WhatsNewEntry[] {
  const s = seen ?? []
  return WHATS_NEW.filter((e) => !s.includes(e.id))
}
