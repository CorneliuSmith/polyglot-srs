import { useState } from 'react'
import { BookOpen, ChevronDown, ChevronRight } from 'lucide-react'

/**
 * "What am I supposed to do here?" — the directions panel for each staff role.
 *
 * Contributors and reviewers are volunteers. Until now the only description
 * of the workflow lived in docs/review-workflow.md, in the repository, which
 * a volunteer has no reason to have ever seen: they were handed a role and a
 * tab full of controls with no statement of what the controls are FOR, what
 * happens after they press one, or whether they can break anything.
 *
 * So each staff tab opens with this. Expanded the first time, collapsed once
 * dismissed (per role — learning the contributor flow doesn't mean you know
 * the reviewer one), and it stays available rather than being a one-shot
 * tour, because the question comes back after a month away.
 */

export type GuideRole =
  | 'contribute'
  | 'review'
  | 'trial_review'
  | 'ambassador'
  | 'admin'

interface Guide {
  title: string
  /** The one thing to understand before anything else. */
  lede: string
  steps: { what: string; detail: string }[]
  /** Reassurance, last. Volunteers hesitate when they fear breaking things. */
  safety: string
}

const GUIDES: Record<GuideRole, Guide> = {
  contribute: {
    title: 'How contributing works',
    lede:
      'You draft; a reviewer publishes. Nothing you write reaches a learner ' +
      'until a reviewer approves it, so you can never accidentally push a ' +
      'wrong explanation live.',
    steps: [
      {
        what: 'Fix something you can see',
        detail:
          'Turn on Review mode in the bar at the top of any page, then tap a ' +
          'sentence — on a card, a tutor reply, or a reading — to quote it and ' +
          'suggest a correction. This is the fastest route and needs no setup.',
      },
      {
        what: 'Edit the curriculum directly',
        detail:
          'Open the grammar editor from this tab to write explanations, add ' +
          'culture notes and references, and add or remove drill sentences for ' +
          'a grammar point.',
      },
      {
        what: 'Flag rather than fix',
        detail:
          'If you know something is wrong but not what the right answer is, ' +
          'file a review note instead. It parks the problem for a reviewer ' +
          'with your reasoning attached — that is a genuinely useful ' +
          'contribution, not a lesser one.',
      },
    ],
    safety:
      'Every edit is logged with your name and can be rolled back in one ' +
      'click. There is nothing here you can permanently break.',
  },
  review: {
    title: 'How reviewing works',
    lede:
      'You are the human gate. Approving an item sets it live for learners — ' +
      'one approval by one reviewer, with no second sign-off behind you.',
    steps: [
      {
        what: 'Work the queue',
        detail:
          'The Review Inbox below lists everything pending for this language: ' +
          'contributor drafts, AI-generated content, and change requests ' +
          'raised from the app.',
      },
      {
        what: 'Read the advisory signals, then decide yourself',
        detail:
          'The AI check (pass / concerns) and any tester ' +
          'recommendations are inputs, not votes. They do not approve ' +
          'anything and they are not always right.',
      },
      {
        what: 'Approve, edit, or send back',
        detail:
          'Approve publishes it. You can also correct the text first and then ' +
          'approve — you do not have to bounce something back over a typo.',
      },
    ],
    safety:
      'Every approval is recorded and reversible. If you publish something ' +
      'and change your mind, roll it back from the item’s history.',
  },
  trial_review: {
    title: 'How testing works',
    lede:
      'You can see the whole queue and say what you think, but your ' +
      'recommendations do not publish anything — a full reviewer makes the ' +
      'final call.',
    steps: [
      {
        what: 'Recommend on pending items',
        detail:
          'Mark items you would approve or reject and say why. A reviewer ' +
          'sees your recommendation alongside the item.',
      },
      {
        what: 'File review notes',
        detail:
          'On any card, note what is wrong and what you would change. Notes ' +
          'carry the same weight whichever role files them.',
      },
      {
        what: 'Flag the exact words, mid-card',
        detail:
          'Turn on Review Mode in the bar at the top, then tap the phrase ' +
          'that is wrong while you study. It goes to the change-request ' +
          'board marked advisory — you can raise and read there, but voting ' +
          'and resolving stay with reviewers.',
      },
      {
        what: 'Say when you are unsure',
        detail:
          '“I think this is wrong but I am not certain” is worth filing. It ' +
          'is more useful than silence and costs a reviewer nothing to check.',
      },
    ],
    safety:
      'Nothing you do here changes what learners see, so there is no way to ' +
      'get it wrong in a way that matters.',
  },
  ambassador: {
    title: 'How inviting works',
    lede:
      'Signup is invite-only, so someone has to make each account by hand. ' +
      'That is the job — and it is the only thing this role can do.',
    steps: [
      {
        what: 'Make the account',
        detail:
          'Enter their email and pick a starting password. The account ' +
          'works immediately; there is no confirmation email to wait for.',
      },
      {
        what: 'Hand over the password yourself',
        detail:
          'It is shown once, right after you create the account, and never ' +
          'again — nothing emails it to them. Send it before you close the ' +
          'page.',
      },
      {
        what: 'Tell them to change it',
        detail:
          'You chose their password, so you know it. They can set their own ' +
          'from Settings once they have signed in.',
      },
    ],
    safety:
      'You cannot see the account list, delete anyone, change plans or grant ' +
      'roles — an admin does those. The worst you can do here is create an ' +
      'account nobody uses.',
  },
  admin: {
    title: 'What lives in Admin',
    lede:
      'Everything below affects real accounts and real learners immediately, ' +
      'without a review step.',
    steps: [
      {
        what: 'People',
        detail:
          'Accounts creates, deletes and re-plans accounts; Roles grants ' +
          'contributor, tester and reviewer — scoped to one language ' +
          'or all of them.',
      },
      {
        what: 'Content feeds',
        detail:
          'Generation runs the maker-checker feeds (vocabulary, grammar, ' +
          'definitions, translations, overlap scan, chart backfill) for this ' +
          'language.',
      },
      {
        what: 'Language settings',
        detail:
          'Visibility hides a language from learners while it is still thin. ' +
          'Review policy decides whether AI content needs human sign-off ' +
          'before it is visible.',
      },
    ],
    safety:
      'Deleting an account is permanent and cascades to all of its cards, ' +
      'history and notes. You cannot delete your own account here.',
  },
}

const storageKey = (role: GuideRole) => `polyglot-guide-open-${role}`

function initiallyOpen(role: GuideRole): boolean {
  try {
    return window.localStorage.getItem(storageKey(role)) !== 'closed'
  } catch {
    // Private mode / storage disabled: show it. A volunteer who has never
    // read the directions is worse off than one who sees them twice.
    return true
  }
}

export default function RoleGuide({ role }: { role: GuideRole }) {
  const [open, setOpen] = useState(() => initiallyOpen(role))
  const guide = GUIDES[role]

  const toggle = () => {
    const next = !open
    setOpen(next)
    try {
      window.localStorage.setItem(storageKey(role), next ? 'open' : 'closed')
    } catch {
      // Not being able to remember the preference is not worth failing over.
    }
  }

  return (
    <section
      data-testid={`role-guide-${role}`}
      className="bg-lang-soft/60 rounded-2xl border border-lang/20 p-4 space-y-3"
    >
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        className="flex w-full items-center gap-2 text-start"
        style={{ minHeight: '44px' }}
      >
        <BookOpen aria-hidden className="h-4 w-4 shrink-0 text-lang" />
        <span className="flex-1 font-semibold text-gray-800">{guide.title}</span>
        {open ? (
          <ChevronDown aria-hidden className="h-4 w-4 shrink-0 text-gray-400" />
        ) : (
          <ChevronRight aria-hidden className="h-4 w-4 shrink-0 text-gray-400" />
        )}
      </button>

      {open && (
        <div className="space-y-3 text-sm">
          <p className="text-gray-700">{guide.lede}</p>
          <ol className="space-y-2">
            {guide.steps.map((step, i) => (
              <li key={step.what} className="flex gap-2.5">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-lang text-[11px] font-semibold text-lang-on">
                  {i + 1}
                </span>
                <span>
                  <span className="font-medium text-gray-800">{step.what}</span>
                  <span className="block text-xs text-gray-600">{step.detail}</span>
                </span>
              </li>
            ))}
          </ol>
          <p className="text-xs text-gray-500 border-t border-lang/15 pt-2">
            {guide.safety}
          </p>
        </div>
      )}
    </section>
  )
}
