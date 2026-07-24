import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getVocabExamples,
  editExampleSentence,
  deleteExampleSentence,
  type VocabExample,
} from '../../api/contribute'
import LanguageWrapper from '../../components/LanguageWrapper'

function ExampleRow({
  ex,
  languageCode,
  onChanged,
}: {
  ex: VocabExample
  languageCode: string
  onChanged: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [sentence, setSentence] = useState(ex.sentence)
  const [translation, setTranslation] = useState(ex.translation ?? '')

  const save = useMutation({
    mutationFn: () =>
      editExampleSentence(ex.id, sentence.trim(), translation.trim() || null),
    onSuccess: () => {
      setEditing(false)
      onChanged()
    },
  })
  const del = useMutation({
    mutationFn: () => deleteExampleSentence(ex.id),
    onSuccess: onChanged,
  })

  if (editing) {
    return (
      <li className="py-2 space-y-2">
        <textarea
          value={sentence}
          onChange={(e) => setSentence(e.target.value)}
          rows={2}
          aria-label="Sentence"
          className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-lang"
        />
        <input
          value={translation}
          onChange={(e) => setTranslation(e.target.value)}
          placeholder="Translation"
          aria-label="Translation"
          className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-lang"
        />
        <div className="flex items-center gap-3 text-xs">
          <button
            type="button"
            onClick={() => save.mutate()}
            disabled={!sentence.trim() || save.isPending}
            className="bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-lg px-3 py-1.5"
          >
            {save.isPending ? 'Saving…' : 'Save'}
          </button>
          <button
            type="button"
            onClick={() => {
              setSentence(ex.sentence)
              setTranslation(ex.translation ?? '')
              setEditing(false)
            }}
            className="text-gray-500 hover:text-gray-700"
          >
            Cancel
          </button>
          {save.isError && <span className="text-red-500">Save failed.</span>}
        </div>
      </li>
    )
  }

  return (
    <li className="py-2 flex items-start justify-between gap-3">
      <div className="min-w-0">
        <LanguageWrapper languageCode={languageCode}>
          <span className="text-sm text-gray-800">{ex.sentence}</span>
        </LanguageWrapper>
        {ex.translation && (
          <span className="block text-xs text-gray-500">{ex.translation}</span>
        )}
        <span className="mt-0.5 flex items-center gap-1.5 text-[10px] uppercase tracking-wide">
          {!ex.reviewed && (
            <span className="rounded bg-amber-50 text-amber-600 px-1.5 py-0.5">
              pending review
            </span>
          )}
          {ex.is_modified && (
            <span className="rounded bg-gray-100 text-gray-500 px-1.5 py-0.5">
              edited
            </span>
          )}
          <span className="text-gray-400">{ex.source}</span>
        </span>
      </div>
      <div className="flex items-center gap-2 shrink-0 text-xs">
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="text-lang hover:underline"
        >
          Edit
        </button>
        <button
          type="button"
          onClick={() => {
            if (window.confirm('Delete this example sentence?')) del.mutate()
          }}
          disabled={del.isPending}
          className="text-gray-400 hover:text-red-600"
        >
          Delete
        </button>
      </div>
    </li>
  )
}

/**
 * Reviewer's inline editor for a word's example sentences — view them, fix a
 * translation or wording, or delete a bad one, right where the word is browsed.
 * Reads through the reviewer-gated endpoint, so it's only mounted for reviewers.
 */
export default function ExamplesEditor({
  vocabularyId,
  languageCode,
}: {
  vocabularyId: string
  languageCode: string
}) {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['vocab-examples', vocabularyId],
    queryFn: () => getVocabExamples(vocabularyId),
    enabled: !!vocabularyId,
    retry: false,
  })
  const onChanged = () =>
    queryClient.invalidateQueries({ queryKey: ['vocab-examples', vocabularyId] })

  if (isLoading) return <p className="text-xs text-gray-400">Loading examples…</p>
  if (!data || data.length === 0) {
    return <p className="text-xs text-gray-400">No example sentences yet.</p>
  }

  return (
    <ul className="divide-y divide-gray-50" data-testid="examples-editor">
      {data.map((ex) => (
        <ExampleRow
          key={ex.id}
          ex={ex}
          languageCode={languageCode}
          onChanged={onChanged}
        />
      ))}
    </ul>
  )
}
