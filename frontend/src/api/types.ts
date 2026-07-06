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
  url: string
}

export interface CardDetail {
  card_type: 'grammar' | 'vocabulary' | 'personal'
  title: string | null
  // the can-do line shown under the title (grammar only)
  function_note?: string | null
  // pronunciation aid: transliteration, vowelled form, etc. (vocabulary only)
  reading?: string | null
  part_of_speech: string | null
  definition: string | null
  usage_note: string | null
  morphology: Record<string, unknown> | string | null
  explanation: string | null
  culture_note: string | null
  reviewed: boolean | null
  references: ReferenceLink[]
  examples: CardDetailExample[]
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
  created_at: string
  updated_at: string
}

export interface ProfileUpdate {
  batch_size?: number
  ui_language?: string
  active_language_id?: string
}
