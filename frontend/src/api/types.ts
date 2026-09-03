export interface Language {
  id: string
  code: string
  name: string
  rtl: boolean
  /** Admin-controlled (Settings > Admin): hidden languages stay out of
   * onboarding/the language picker for everyone but never lose content or
   * access — see lib/languages.ts's visibleLanguages(). */
  is_visible: boolean
  /** Admin-controlled: when on, the backend loop auto-fills missing
   * support-locale glosses for this course — but only for locales real
   * accounts actually use. Optional like is_visible's degrade story:
   * absent (older response) reads as off. */
  auto_translate_enabled?: boolean
  /** Whether a neural TTS voice exists for this language. False means
   * audio comes (only) from contributor recordings — the UI shows the
   * "we're collecting real recordings" note. Absent (older response)
   * reads as true so no note appears spuriously. */
  has_tts?: boolean
}

export interface DueCard {
  id: string
  card_type: 'grammar' | 'vocabulary' | 'personal'
  card_id: string
  // Real drill_sentences.id on Gym/cram grammar cards — lets the Gym record
  // per-drill practice history for adaptive selection. Absent elsewhere.
  drill_id?: string | null
  sentence: string
  correct_answer: string
  hint?: string | null
  translation?: string | null
  // The language `translation` is actually in, and whether that differs
  // from the locale the learner asked for. Set by the server; the card
  // labels a mismatch instead of passing another language off as theirs.
  translation_locale?: string | null
  translation_pending?: boolean | null
  // language-aware hint layers (present when authored for this sentence)
  gloss?: string | null
  transliteration?: string | null
  // null for grammar cards — the backend only populates these for vocabulary.
  // Exception: cram/Gym cards may carry the chart of the word the drill
  // exercises (WP25c), resolved by lemmatizing the answer server-side.
  morphology: Record<string, unknown> | null
  chart_word?: string | null
  chart_usage_note?: string | null
  // Gym/cram only: the paradigm cell this drill exercises, and the server-built
  // standardized baseline — "word (form)", native-language word where known.
  cell?: string | null
  baseline?: string | null
  alternatives: string[] | null
  // Vocabulary only; 'letter' marks an alphabet-deck card (single-glyph
  // answer), absent on grammar/personal cards.
  part_of_speech?: string | null
  language_code: string
  ease_factor: number
  interval: number
  repetitions: number
  streak: number
  lapses: number
  next_review: string
}

export interface CardDetailExample {
  sentence: string
  translation: string | null
  hint: string | null
}

export interface ReferenceLink {
  title: string
  /** online resources link out; offline ones cite a book instead */
  url?: string
  book?: string
  page?: string
}

/** Named SRS stage — same bands as the dashboard tiles. */
export interface CardProgress {
  stage: StageName
  first_studied: string | null
  times_studied: number
  accuracy: number | null
  streak: number
  misses: number
  next_review: string | null
}

/** An authored Related entry, resolved to a live point + the learner's stage. */
export interface RelatedPoint {
  id: string
  title: string
  level: string | null
  function_note: string | null
  contrast: string | null
  stage: StageName | null
}

export interface CardDetail {
  card_type: 'grammar' | 'vocabulary' | 'personal'
  title: string | null
  // the grammar point id (grammar only) — read-tracking keys on it
  point_id?: string
  // the can-do line shown under the title (grammar only)
  function_note?: string | null
  // pronunciation aid: transliteration, vowelled form, etc. (vocabulary only)
  reading?: string | null
  /** which locale the hints/definitions are rendered in ('en' unless
   * studying English with a support language set) */
  hint_locale?: string
  part_of_speech: string | null
  definition: string | null
  usage_note: string | null
  morphology: Record<string, unknown> | string | null
  explanation: string | null
  culture_note: string | null
  reviewed: boolean | null
  references: ReferenceLink[]
  // reference keys (url, or title for books) this user marked read (grammar only)
  read_refs?: string[]
  related?: RelatedPoint[]
  examples: CardDetailExample[]
  // the learner's own sentences using this word (vocabulary only)
  your_sentences?: { sentence: string; translation: string | null }[]
  progress?: CardProgress
  /** Personal cards only: how this card was made. source null = created
   * before tracking (displayed as such, never guessed). */
  provenance?: {
    source: 'reading' | 'tutor' | 'notes' | 'speak' | 'manual' | null
    created_at: string | null
    note_title: string | null
    deck_name: string | null
  } | null
}

export interface ValidateAnswerRequest {
  language_code: string
  user_input: string
  correct_answer: string
  card_context?: Record<string, unknown>
}

export interface ValidateAnswerResponse {
  answer_result: 'correct' | 'correct_sloppy' | 'wrong_form' | 'wrong'
  feedback: string | null
}

export interface SubmitReviewRequest {
  card_id: string
  answer_result: string
  time_taken_ms: number | null
  // the exact sentence shown (sentences rotate) — logged for analysis
  prompt_sentence?: string | null
}

export interface SubmitReviewResponse {
  next_review: string
  interval: number
  stability: number
  difficulty: number
  state: string
  quality: number
}

/** Teachable content for one newly added item — shown BEFORE the first quiz. */
export interface LessonQuiz {
  sentence: string
  answer: string
  translation: string | null
  gloss?: string | null
  transliteration?: string | null
  hint: string | null
  morphology: Record<string, unknown> | null
  alternatives: string[]
}

export interface Lesson extends CardDetail {
  card_id: string
  // The first-check drill: answering it correctly is what moves the card
  // from "taught" into the review queue.
  quiz?: LessonQuiz | null
}

export interface LearnResponse {
  added: number
  items: string[]
  lessons: Lesson[]
}

/** One lane of session readiness: how much already reads in the learner's
 * support language. `ready_enough` is what the UI acts on. */
export interface ReadinessLane {
  total: number
  ready: number
  pct: number
  /** Cards in the upcoming batch. */
  cards: number
  /** Cards whose first-read text (gloss, explanation) is already there. */
  cards_ready: number
  /** How many of those it takes to start — the gate the learner feels. */
  start_cards: number
  ready_enough: boolean
}

export interface SessionReadiness {
  locale: string | null
  /** New to this course: no active card, nothing ever answered. Only a new
   * learner is ever asked to wait — and only until the first card lands.
   * Everyone else starts at once and the rest fills in while they work. */
  new_here: boolean
  /** The server could not score the session and answered "just start".
   * Never a reason to hold anyone; surfaced so a stuck fill has a name. */
  degraded?: boolean
  learn: ReadinessLane
  review: ReadinessLane
  /** Already-translated words of the upcoming batch — the wait game's pool. */
  pairs: { word: string; gloss: string }[]
  /** What the server's own inline fill is doing for this session — the
   * reason behind a bar that isn't moving. Null when it has never run on
   * the process that answered. */
  fill?: SessionFill | null
}

export interface SessionFill {
  /** `no_provider` is the one a learner can't do anything about and the
   * owner can: the server has no translation key. */
  status: 'running' | 'done' | 'error' | 'no_provider'
  detail: string | null
  /** Rows translated so far by this fill. */
  landed: number
  /** Cards of the session walked so far, in reading order. */
  cards_done: number
  seconds: number
}

export interface LearnDeck {
  id: string
  list_type: 'vocabulary' | 'grammar'
  level: string | null
  title: string
  subscribed: boolean
  total: number
  learned: number
}

export interface CEFRLevelProgress {
  learned: number
  total: number
}

export interface ForecastDay {
  date: string
  count: number
}

export interface ActivityDay {
  date: string
  vocab: number
  grammar: number
}

export type StageName =
  | 'beginner'
  | 'adept'
  | 'seasoned'
  | 'expert'
  | 'master'
  | 'self_study'
  | 'ghost'

export interface DashboardProfile {
  days_studied: number
  items_studied: number
  last_session_accuracy: number | null
  week: { date: string; studied: boolean }[]
}

export interface DashboardStats {
  due_count: number
  /** grammar + vocab always sum to due_count (personal cards count as vocab) */
  due_grammar: number
  due_vocab: number
  /** new cards started since UTC midnight — drives the daily learn goal */
  learned_today: number
  streak_days: number
  cefr_progress: Record<string, CEFRLevelProgress>
  forecast: ForecastDay[]
  activity: ActivityDay[]
  stages: Record<'vocab' | 'grammar', Record<StageName, number>>
  profile: DashboardProfile
}

export interface UserProfile {
  id: string
  batch_size: number
  ui_language: string
  active_language_id: string | null
  /** "learning English from X" — locale English hints render in (null = English) */
  support_locale: string | null
  /** 'single' = one licensed language (lower price), 'all' = every language */
  plan_scope: 'single' | 'all'
  /** the licensed language when plan_scope is 'single' */
  plan_language_id: string | null
  /** The plan includes the monthly AI pool (the "+ AI" half of the four
   * options). Written by billing, never by a settings save; absent on a
   * server whose migration hasn't landed, which reads as false. */
  plan_ai?: boolean
  /** opt-in daily email when reviews are due */
  reminder_opt_in: boolean
  /** hour of the daily reminder, in UTC (client converts to local) */
  reminder_hour_utc: number
  /** opt-in weekly round-up email, which carries that week's picks */
  weekly_digest_opt_in: boolean
  /** day to send it, 0 = Sunday … 6 = Saturday */
  weekly_digest_dow: number
  /** Show explicit vocabulary and sentences (slurs, strong profanity).
   *  Off by default: the frequency lists come from subtitle corpora and
   *  put Spanish *puta* at rank 505, so it reached a beginner unasked. */
  allow_explicit_content: boolean
  /** Read the full sentence aloud when an answer grades correct. Account-
   *  level so every device behaves the same; absent (migration 20261001
   *  not applied) reads as on. */
  sentence_audio_on_correct?: boolean
  /** Settings this server cannot store yet, because the migration adding
   * their column has not been applied. A control listed here saves
   * nothing, so it is shown disabled and labelled rather than left to flip
   * back on its own. */
  unavailable_settings?: string[]
  /** Offer the word-by-word gloss as a hint layer. Absent reads as OFF —
   * the layer is opt-in, so a deploy running ahead of migration 20261012
   * withholds it rather than showing unfamiliar notation unasked. */
  show_glosses?: boolean
  /** Which rollouts this account is in, {experiment_key: variant}. Absent
   *  when the server has no experiments running (or hasn't been migrated),
   *  which every reader must treat as "the default", never as "unknown". */
  experiments?: Record<string, string>
  created_at: string
  updated_at: string
}

export interface ProfileUpdate {
  batch_size?: number
  ui_language?: string
  active_language_id?: string
  /** send 'en' to reset to English definitions */
  support_locale?: string
  reminder_opt_in?: boolean
  reminder_hour_utc?: number
  weekly_digest_opt_in?: boolean
  weekly_digest_dow?: number
  allow_explicit_content?: boolean
}
