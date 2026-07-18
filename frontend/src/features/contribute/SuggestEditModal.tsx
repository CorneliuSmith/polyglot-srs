import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { submitSuggestion } from '../../api/contribute'
import type { SuggestEntity, SuggestionFields } from '../../api/contribute'
import LanguageWrapper from '../../components/LanguageWrapper'

/** Contributor editor for a vocabulary card: edit the text fields, see a live
 * preview of how the card will read, and submit the change for review. Nothing
 * goes live until a reviewer approves it. */
export default function SuggestEditModal(props: {
  entityType: SuggestEntity
  entityId: string
  word: string
  languageCode: string
  current: SuggestionFields
  onClose: () => void
}) {
  const { entityType, entityId, word, languageCode, current, onClose } = props
  const [definition, setDefinition] = useState(current.definition ?? '')
  const [pos, setPos] = useState(current.part_of_speech ?? '')
  const [usageNote, setUsageNote] = useState(current.usage_note ?? '')
  const [note, setNote] = useState('')
  const [done, setDone] = useState(false)

  const changed: SuggestionFields = {}
  if (definition.trim() !== (current.definition ?? '')) changed.definition = definition.trim()
  if (pos.trim() !== (current.part_of_speech ?? '')) changed.part_of_speech = pos.trim()
  if (usageNote.trim() !== (current.usage_note ?? '')) changed.usage_note = usageNote.trim()
  const nChanged = Object.keys(changed).length

  const mutation = useMutation({
    mutationFn: () =>
      submitSuggestion({ entity_type: entityType, entity_id: entityId, proposed: changed, note }),
    onSuccess: () => setDone(true),
  })

  const field = (
    label: string,
    value: string,
    set: (v: string) => void,
    textarea = false,
  ) => (
    <label className="block">
      <span className="text-xs font-medium text-gray-500">{label}</span>
      {textarea ? (
        <textarea
          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-lang focus:outline-none"
          rows={2}
          value={value}
          onChange={(e) => set(e.target.value)}
        />
      ) : (
        <input
          className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-lang focus:outline-none"
          value={value}
          onChange={(e) => set(e.target.value)}
        />
      )}
    </label>
  )

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl bg-white p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">Suggest an edit</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>

        {done ? (
          <div className="py-8 text-center">
            <p className="text-gray-800 font-medium">Thanks — sent for review.</p>
            <p className="text-sm text-gray-500 mt-1">
              A reviewer will approve or decline it. Nothing changes on the card
              until then.
            </p>
            <button
              onClick={onClose}
              className="mt-4 rounded-lg bg-lang px-4 py-2 text-sm font-semibold text-white"
            >
              Done
            </button>
          </div>
        ) : (
          <>
            <div className="mt-3 space-y-3">
              {field('Definition', definition, setDefinition)}
              {field('Part of speech', pos, setPos)}
              {field('Usage note', usageNote, setUsageNote, true)}
              {field('Why this change? (optional)', note, setNote, true)}
            </div>

            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-1">
                Preview
              </p>
              <div className="rounded-xl border border-gray-100 bg-gray-50 p-3" data-testid="card-preview">
                <LanguageWrapper languageCode={languageCode}>
                  <span className="text-lg font-bold text-gray-900">{word}</span>
                </LanguageWrapper>
                <p className="text-gray-800">
                  <span className="font-semibold">{word}</span>
                  {pos.trim() ? ` (${pos.trim()})` : ''}
                  {definition.trim() ? ` — ${definition.trim()}` : ''}
                </p>
                {usageNote.trim() && (
                  <p className="mt-1 text-sm text-gray-600 whitespace-pre-wrap">
                    {usageNote.trim()}
                  </p>
                )}
              </div>
            </div>

            {mutation.isError && (
              <p className="mt-2 text-sm text-red-600">Couldn't send — try again.</p>
            )}
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={onClose} className="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100">
                Cancel
              </button>
              <button
                disabled={nChanged === 0 || mutation.isPending}
                onClick={() => mutation.mutate()}
                className="rounded-lg bg-lang px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
              >
                {mutation.isPending ? 'Sending…' : `Submit ${nChanged || ''} change${nChanged === 1 ? '' : 's'}`}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
