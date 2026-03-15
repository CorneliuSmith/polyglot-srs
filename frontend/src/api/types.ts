export interface Language {
  id: string
  code: string
  name: string
  rtl: boolean
}

export interface DueCard {
  id: string
  card_type: 'grammar' | 'vocabulary'
  card_id: string
  sentence: string
  correct_answer: string
  hint?: string
  translation?: string
  morphology: Record<string, unknown>
  alternatives: string[]
  language_code: string
  ease_factor: number
  interval: number
  repetitions: number
  streak: number
  lapses: number
  next_review: string
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
  ease_factor: number
  interval: number
  quality: number
}

export interface LearnResponse {
  added: number
  items: string[]
}

export interface DashboardStats {
  due_count: number
  streak_days: number
  cefr_progress: Record<string, number>
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
