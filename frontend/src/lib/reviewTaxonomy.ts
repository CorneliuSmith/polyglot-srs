import type { ReviewInboxCounts } from '../api/contribute'

/**
 * The one table that says what every review stream IS: where it came from,
 * who may see it, and where it is acted on.
 *
 * Owner: "good visibility on the type of review and who sees it and where."
 * The inbox and the notification bell both render from THIS table, so the
 * grouping and the wording can never drift apart between them — the failure
 * mode of every taxonomy that lives in two components.
 *
 * `origin` is the owner's own four categories, verbatim:
 *   reports       — "reviews submitted by users": humans using or testing
 *                   the app flagged something about a piece of content.
 *   general       — "general reviews": the home-page feedback button.
 *                   About the app, not a card.
 *   ai            — "ai that needs to be reviewed": machine output waiting
 *                   for a human gate, and machine audits of existing content.
 *   contributions — "contributions by humans that need to be reviewed":
 *                   drafts and proposed edits awaiting approval.
 */
export type QueueOrigin = 'reports' | 'general' | 'ai' | 'contributions'

/** Who can actually OPEN the panel behind a tile.
 *  - 'all'     — anyone who can see the inbox (reviewers and admins)
 *  - 'publish' — full reviewers/admins (`can_publish`)
 *  - 'admin'   — admins only
 * A tile whose panel the viewer can't open is a phantom: they scroll for
 * something that 403'd silently and report the inbox as broken. */
export type QueueAudience = 'all' | 'publish' | 'admin'

export interface QueueMeta {
  key: keyof ReviewInboxCounts
  label: string
  origin: QueueOrigin
  audience: QueueAudience
  /** Where it is acted on — the panel or page behind the number. */
  hint: string
  /** Where the acting panel caps its own list, so a count of 150 against a
   * panel that shows 100 says so instead of quietly disagreeing. */
  limit?: number
}

export const ORIGIN_LABELS: Record<QueueOrigin, string> = {
  reports: 'Reports from learners & testers',
  general: 'General feedback',
  ai: 'AI content awaiting review',
  contributions: 'Contributions awaiting approval',
}

/** Rendering order: people first — a human is waiting on the top two. */
export const ORIGIN_ORDER: QueueOrigin[] = [
  'reports', 'general', 'ai', 'contributions',
]

export const QUEUE_META: QueueMeta[] = [
  // ── Reports from people ──────────────────────────────────────────────
  { key: 'feedback', label: 'Card feedback', origin: 'reports',
    audience: 'publish', hint: 'Feedback panel · Review tab', limit: 100 },
  { key: 'notes', label: 'Review notes', origin: 'reports',
    audience: 'publish', hint: 'Point review notes · Review tab', limit: 200 },
  { key: 'tester_recommendations', label: 'Tester recommendations',
    origin: 'reports', audience: 'all',
    hint: 'Tester recommendations panel · Review tab', limit: 200 },

  // ── General feedback ─────────────────────────────────────────────────
  { key: 'app_feedback', label: 'App feedback', origin: 'general',
    // GET /api/feedback triage is staff-wide to read but the queue's
    // per-language tile pairs with the panel mounted for admins.
    audience: 'admin', hint: 'General feedback queue · Review tab' },

  // ── AI awaiting a human ──────────────────────────────────────────────
  { key: 'pending_drills', label: 'Generated drills', origin: 'ai',
    audience: 'all', hint: 'Generated drills panel · Review tab' },
  { key: 'flagged_drills', label: 'Flagged drills', origin: 'ai',
    audience: 'all', hint: 'Point drills · flagged' },
  { key: 'pending_examples', label: 'Generated examples', origin: 'ai',
    audience: 'all', hint: 'Word examples · Contribute tab' },
  { key: 'flagged_examples', label: 'Flagged examples', origin: 'ai',
    audience: 'all', hint: 'Vocab · needs attention' },
  { key: 'translation_suggestions', label: 'Translation fixes', origin: 'ai',
    audience: 'all', hint: 'Vocab · needs attention' },
  { key: 'ai_translations', label: 'AI translations', origin: 'ai',
    audience: 'admin', hint: 'AI translations panel · Review tab' },
  { key: 'ai_levels', label: 'AI vocab levels', origin: 'ai',
    audience: 'all', hint: 'AI levels panel · Review tab' },
  { key: 'ai_topics', label: 'AI topic buckets', origin: 'ai',
    audience: 'all', hint: 'Topic buckets panel · Review tab' },
  { key: 'overlaps', label: 'Overlapping points', origin: 'ai',
    audience: 'all', hint: 'Overlaps panel · Review tab' },

  // ── Human contributions ──────────────────────────────────────────────
  { key: 'grammar_pending', label: 'Grammar points', origin: 'contributions',
    audience: 'all', hint: 'Contribute tab · pending review' },
  { key: 'suggestions', label: 'Content suggestions', origin: 'contributions',
    audience: 'publish', hint: 'Suggestions panel · Review tab', limit: 100 },
  { key: 'change_requests', label: 'Change requests', origin: 'contributions',
    audience: 'all', hint: 'Change requests board · Review tab' },
]

/** Whether this viewer's roles can open the panel behind a queue. */
export function queueVisible(
  meta: QueueMeta,
  viewer: { isAdmin: boolean; canPublish: boolean },
): boolean {
  if (meta.audience === 'admin') return viewer.isAdmin
  if (meta.audience === 'publish') return viewer.canPublish || viewer.isAdmin
  return true
}

/** "3 reports · 1 general · 4 AI · 2 contributions" — a language described
 * by what KIND of work is waiting, for the bell's per-language rows. Counts
 * for unknown keys are ignored rather than crashed on, so a server one
 * queue ahead of this build degrades to a smaller sentence. */
export function originSummary(counts: Record<string, number>): string {
  const byOrigin = new Map<QueueOrigin, number>()
  for (const meta of QUEUE_META) {
    const n = counts[meta.key] ?? 0
    if (n > 0) byOrigin.set(meta.origin, (byOrigin.get(meta.origin) ?? 0) + n)
  }
  const short: Record<QueueOrigin, string> = {
    reports: 'reports', general: 'general', ai: 'AI',
    contributions: 'contributions',
  }
  return ORIGIN_ORDER.filter((o) => byOrigin.has(o))
    .map((o) => `${byOrigin.get(o)} ${short[o]}`)
    .join(' · ')
}
