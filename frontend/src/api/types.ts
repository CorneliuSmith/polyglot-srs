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
}

export interface SubmitReviewResponse {
  next_review: string
  interval: number
  stability: number
  difficulty: number
  state: string
  quality: number
}

export interface LearnResponse {
  added: number
  items: string[]
}

export interface CEFRLevelProgress {
  learned: number
  total: number
}

export interface DashboardStats {
  due_count: number
  streak_days: number
  cefr_progress: Record<string, CEFRLevelProgress>
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
