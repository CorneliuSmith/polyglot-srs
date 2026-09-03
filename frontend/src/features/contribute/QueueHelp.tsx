import { useEffect, useRef, useState } from 'react'

/**
 * The "what am I looking at, and what does this button DO" hover for a
 * review queue (owner: "I also do not know what resolve means in these
 * contexts. These areas need info hovers to explain what is happening in
 * each section").
 *
 * Every queue's help is written to the same three beats, because those are
 * the three questions that actually get asked:
 *   what  — where these items come from, and what they are.
 *   who   — who can act on them, when that is narrower than "you".
 *   does  — what each action DOES, in the irreversible sense: "Resolve"
 *            reads as "mark it done" but in half these panels it deletes
 *            the row, and nowhere on screen said so.
 *
 * Click, not CSS :hover — a tooltip that needs a mouse is unreadable on the
 * handset half of this app's staff traffic, and a `title` attribute can't
 * hold three sentences. Escape and an outside click both close it.
 */
export interface QueueHelpText {
  what: string
  who?: string
  does: { action: string; means: string }[]
}

export default function QueueHelp({
  title,
  help,
  testId,
}: {
  title: string
  help: QueueHelpText
  testId?: string
}) {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onDown(e: MouseEvent) {
      if (!box.current?.contains(e.target as Node)) setOpen(false)
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <span className="relative inline-block" ref={box}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={`What is ${title}?`}
        data-testid={testId ?? 'queue-help'}
        className="ms-1.5 inline-flex h-4 w-4 items-center justify-center rounded-full border border-gray-300 align-middle text-[10px] font-semibold text-gray-500 hover:border-lang hover:text-lang"
      >
        i
      </button>
      {open && (
        <div
          role="tooltip"
          data-testid={`${testId ?? 'queue-help'}-body`}
          className="absolute start-0 top-6 z-20 w-72 rounded-lg border border-gray-200 bg-white p-3 text-start shadow-lg"
        >
          <p className="text-xs font-semibold text-gray-800">{title}</p>
          <p className="mt-1 text-[11px] leading-relaxed text-gray-600">
            {help.what}
          </p>
          {help.who && (
            <p className="mt-1.5 text-[11px] leading-relaxed text-gray-600">
              <span className="font-medium text-gray-700">Who acts: </span>
              {help.who}
            </p>
          )}
          {help.does.length > 0 && (
            <dl className="mt-2 space-y-1 border-t border-gray-100 pt-2">
              {help.does.map((d) => (
                <div key={d.action} className="text-[11px] leading-relaxed">
                  <dt className="inline font-semibold text-gray-800">
                    {d.action}
                  </dt>
                  <dd className="inline text-gray-600"> — {d.means}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      )}
    </span>
  )
}

/**
 * The help text for every queue, in one table for the same reason the
 * taxonomy is: two panels describing "Resolve" differently is how a
 * reviewer learns to distrust the descriptions.
 *
 * Where an action DELETES rather than files something away, the text says
 * "deleted" in those words. That is the whole point of this table.
 */
export const QUEUE_HELP: Record<string, QueueHelpText> = {
  'change-requests': {
    what:
      'Problems staff and testers flagged on live content from inside Learn ' +
      'and Review — "this hint gives the answer away", "this translation is ' +
      'wrong". Votes rank them, they do not decide them.',
    who:
      'Contributors, reviewers and admins vote. Only an admin accepts or ' +
      'rejects. Testers may raise and read, and their rows are marked ' +
      'advisory.',
    does: [
      {
        action: 'Accept',
        means:
          'agrees the content is wrong and closes the request. It records ' +
          'the decision — it does NOT edit the card for you. Use "Edit ' +
          'card" first if the card needs changing, then accept.',
      },
      {
        action: 'Edit card',
        means:
          'changes the content itself, here, and logs the change so it can ' +
          'be rolled back. This is the only action on this board that ' +
          'touches what learners see.',
      },
      {
        action: 'Reject',
        means: 'closes the request as not a problem. The content is untouched.',
      },
      {
        action: '▲ / ▼',
        means:
          'your opinion on priority. It only sorts the board; it never ' +
          'publishes or resolves anything.',
      },
    ],
  },
  feedback: {
    what:
      'What learners reported on a specific card while studying it — the ' +
      '"something wrong with this card?" box. One line of complaint, in ' +
      'their words.',
    who: 'Reviewers and admins.',
    does: [
      {
        action: 'Resolve',
        means:
          'marks the report as dealt with and removes it from this queue. ' +
          'It does not change the card — use "Edit card" first if it needs ' +
          'it, then resolve the report.',
      },
      {
        action: 'Edit card',
        means:
          'changes the card the learner is complaining about, here. The ' +
          'edit is logged and can be rolled back.',
      },
    ],
  },
  issues: {
    what:
      'Review notes parked on a grammar point or word by someone who saw a ' +
      'problem but was not the person to fix it — "this gloss is regional", ' +
      '"the B1 level looks high".',
    who: 'Reviewers and admins.',
    does: [
      {
        action: 'Resolve',
        means:
          'closes the note. Use it once the thing it describes is fixed, or ' +
          'once you have decided it is not a problem.',
      },
    ],
  },
  'tester-recommendations': {
    what:
      'Advisory ✓/✗ and written notes from testers on items that are still ' +
      'waiting for a decision. This is the tester channel — read it before ' +
      'you approve the item itself, because approving deletes the pending ' +
      'row and this note with it.',
    who: 'Anyone who can review the language, testers included.',
    does: [
      {
        action: 'Nothing here publishes',
        means:
          'this panel is read-only input. Act on the item in its own queue ' +
          '(Generated drills, Word examples).',
      },
    ],
  },
  'generated-drills': {
    what:
      'Grammar drills the AI wrote. They are hidden from learners until a ' +
      'human approves them.',
    who:
      'Full reviewers and admins approve or reject. Testers recommend ' +
      'instead — their call is advisory.',
    does: [
      {
        action: 'Approve',
        means:
          'makes it permanent corpus and shows it to learners from the next ' +
          'review onward.',
      },
      {
        action: 'Reject',
        means: 'DELETES the drill. It is not archived and cannot be undone here.',
      },
      {
        action: 'Recommend ✓ / ✗',
        means:
          'records your opinion for the reviewer who decides. Nothing is ' +
          'published or deleted.',
      },
    ],
  },
  'ai-levels': {
    what:
      'CEFR levels the model guessed for words that had none. The level sets ' +
      'which deck the word lands in, so a wrong one puts C1 vocabulary in ' +
      'front of a beginner.',
    who: 'Anyone who can review the language.',
    does: [
      {
        action: 'Confirm',
        means:
          'accepts the level as final and moves the word into that deck. The ' +
          'word stops being marked as AI-levelled.',
      },
      {
        action: 'Change the level',
        means: 'overrides the model and confirms in one step.',
      },
    ],
  },
  'ai-topics': {
    what:
      'Topic buckets the classifier assigned to words ("food & drink", ' +
      '"travel"). They drive the By-topic view learners can switch to.',
    who: 'Anyone who can review the language.',
    does: [
      {
        action: 'Confirm',
        means: 'accepts the bucket and makes it visible to learners.',
      },
      {
        action: 'Reject',
        means:
          'clears the bucket. The word keeps its level and stays in its deck ' +
          '— it just has no topic until something assigns one again.',
      },
    ],
  },
  'translation-reviews': {
    what:
      'Text the AI translated into a support locale that the automatic ' +
      'checker would not pass on its own — word glosses, and since ' +
      'September also drill lines and hints, grammar explanations, titles ' +
      'and notes, and example-sentence meanings, grouped by kind. Learners ' +
      'studying in that locale see English until one of these is approved.',
    who: 'Admins only.',
    does: [
      {
        action: 'Approve',
        means:
          'publishes the proposed text to learners using that support ' +
          'locale, marked reviewed.',
      },
      {
        action: 'Reject',
        means:
          'discards it. The field falls back to English and will be offered ' +
          'for translation again on a later sweep.',
      },
      {
        action: 'Dismiss (rows with no Approve)',
        means:
          'the checker rejected the AI gloss without proposing a ' +
          'replacement, so there is nothing to publish — clearing the row ' +
          'is the only action it has. If the ENGLISH text is what is wrong, ' +
          'use "Edit card" on the row instead; every locale is translated ' +
          'from it.',
      },
      {
        action: 'Edit card',
        means:
          'changes the word\'s English definition or reading, here. Logged ' +
          'and revertible.',
      },
    ],
  },
  suggestions: {
    what:
      'Proposed edits to a definition or usage note, written by a ' +
      'contributor rather than generated.',
    who: 'Reviewers and admins.',
    does: [
      {
        action: 'Approve',
        means: 'writes the suggested text onto the live card, replacing what is there.',
      },
      { action: 'Reject', means: 'discards the suggestion. The card is untouched.' },
    ],
  },
  'feedback-queue': {
    what:
      'Feedback about the app as a whole, sent from the home-page button — ' +
      'bugs, confusing screens, ideas. Not about any one card, which is why ' +
      'it has its own queue.',
    who: 'Admins.',
    does: [
      {
        action: 'Resolve',
        means:
          'marks the report handled and clears it from the queue. Nothing is ' +
          'sent back to the person who wrote it.',
      },
    ],
  },
}
