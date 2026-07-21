import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  canSuggestForLanguage,
  createChangeRequest,
  getMyRoles,
} from '../../api/contribute'

const FIELDS = [
  { value: 'sentence', label: 'the sentence' },
  { value: 'hint', label: 'the hint' },
  { value: 'translation', label: 'the translation' },
  { value: 'answer', label: 'the answer' },
  { value: 'explanation', label: 'the explanation' },
  { value: 'other', label: 'something else' },
]

/**
 * Inline, low-friction change request for STAFF (reviewer / contributor /
 * admin). Shown on any card in Learn or Review; a learner sees nothing (they
 * use "Report an issue"). Names the field, says what's wrong, optionally
 * suggests a fix — the request lands on the review board for voting.
 */
export default function SuggestChange({
  languageId,
  targetType,
  targetId = null,
  targetLabel = null,
  defaultField = 'sentence',
}: {
  languageId: string | null
  targetType: 'grammar_point' | 'drill' | 'vocabulary' | 'example_sentence' | 'other'
  targetId?: string | null
  targetLabel?: string | null
  defaultField?: string
}) {
  const { data: rolesData } = useQuery({
    queryKey: ['my-roles'],
    queryFn: getMyRoles,
    staleTime: 5 * 60 * 1000,
  })
  const [open, setOpen] = useState(false)
  const [done, setDone] = useState(false)
  const [field, setField] = useState(defaultField)
  const [issue, setIssue] = useState('')
  const [suggestion, setSuggestion] = useState('')

  const mutation = useMutation({
    mutationFn: () =>
      createChangeRequest({
        language_id: languageId!,
        target_type: targetType,
        target_id: targetId,
        target_label: targetLabel,
        field,
        issue: issue.trim(),
        suggestion: suggestion.trim() || null,
      }),
    onSuccess: () => {
      setDone(true)
      setOpen(false)
      setIssue('')
      setSuggestion('')
    },
  })

  const staff =
    !!languageId &&
    !!rolesData &&
    canSuggestForLanguage(rolesData.roles, languageId)
  if (!staff) return null

  if (done) {
    return (
      <p className="text-xs text-gray-400 text-center mt-2" role="status">
        ✓ Sent to the review board
      </p>
    )
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="block mx-auto mt-2 text-xs text-gray-400 hover:text-lang"
      >
        ✎ Suggest a change (reviewer)
      </button>
    )
  }

  return (
    <div
      className="mt-3 rounded-xl border border-gray-200 bg-white p-3 text-left space-y-2"
      data-testid="suggest-change"
    >
      <label className="block text-xs text-gray-500">
        What needs fixing?
        <select
          value={field}
          onChange={(e) => setField(e.target.value)}
          className="mt-1 w-full rounded-lg border border-gray-200 px-2 py-1.5 text-sm"
        >
          {FIELDS.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </select>
      </label>
      <textarea
        value={issue}
        onChange={(e) => setIssue(e.target.value)}
        placeholder="What's wrong?"
        rows={2}
        maxLength={2000}
        className="w-full rounded-lg border border-gray-200 px-2 py-1.5 text-sm"
      />
      <textarea
        value={suggestion}
        onChange={(e) => setSuggestion(e.target.value)}
        placeholder="Suggested fix (optional) — e.g. an alternate sentence"
        rows={2}
        maxLength={2000}
        className="w-full rounded-lg border border-gray-200 px-2 py-1.5 text-sm"
      />
      {mutation.isError && (
        <p className="text-xs text-red-600" role="alert">
          Couldn't send — try again.
        </p>
      )}
      <div className="flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-xs text-gray-400 hover:text-gray-600"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={!issue.trim() || mutation.isPending}
          className="rounded-lg bg-lang hover:bg-lang-dark disabled:opacity-40 text-lang-on text-xs font-semibold px-3 py-1.5"
        >
          {mutation.isPending ? 'Sending…' : 'Send to review board'}
        </button>
      </div>
    </div>
  )
}
