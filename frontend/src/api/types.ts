export interface Language {
  id: string
  code: string
  name: string
  rtl: boolean
}

export interface DueCard {
  id: string
  card_type: 'grammar' | 'vocabulary' | 'personal'
  card_id: string
  sentence: string
  correct_answer: string
  hint?: string | null
  translation?: string | null
  // language-aware hint layers (present when authored for this sentence)
  gloss?: string | null
  transliteration?: string | null
  // null for grammar cards — the backend only populates these for vocabulary
  morphology: Record<string, unknown> | null
  alternatives: string[] | null
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
  created_at: string
  updated_at: string
}

export interface ProfileUpdate {
  batch_size?: number
  ui_language?: string
  active_language_id?: string
  /** send 'en' to reset to English definitions */
  support_locale?: string
}
