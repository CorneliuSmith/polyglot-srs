/**
 * The publish policy, mirrored from backend/services/visibility.py.
 *
 * Kept in one place on this side too: the admin panel is the only screen
 * that explains to a human where the line between "reviewers can see it"
 * and "learners can see it" actually sits, and getting that wording wrong
 * is how an owner ends up flipping a switch and seeing nothing happen.
 */
export const PUBLISH_POLICIES = ['human_only', 'ai_ok', 'both', 'all'] as const

export type PublishPolicy = (typeof PUBLISH_POLICIES)[number]

/** 'strict' is the stored legacy spelling of human_only. */
export function normalizePolicy(value: string | null | undefined): PublishPolicy {
  if (value === 'strict' || !value) return 'human_only'
  return (PUBLISH_POLICIES as readonly string[]).includes(value)
    ? (value as PublishPolicy)
    : 'human_only'
}

export const POLICY_LABELS: Record<PublishPolicy, string> = {
  human_only: 'Human-reviewed only',
  ai_ok: 'Human-reviewed or AI-verified',
  both: 'Human-reviewed and AI-verified',
  all: 'Everything, including unchecked',
}

export const POLICY_HELP: Record<PublishPolicy, string> = {
  human_only:
    'Learners see only what a person has approved. Safest, and the slowest way to fill out a new language.',
  ai_ok:
    'Learners also see content the automated check has passed. Never-checked content stays hidden.',
  both:
    'Learners see only content that has passed the automated check and been approved by a person.',
  all:
    'Learners see everything, including content nothing has checked yet. Use while building a language out.',
}
