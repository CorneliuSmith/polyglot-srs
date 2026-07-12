import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { addDrill, deleteDrill, getDrills, updateDrill } from '../../api/contribute'

function errorMessage(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  return detail ?? 'Could not save the sentence.'
}

/**
 * Lazy-loaded editor for a grammar point's fill-in-the-blank drill sentences.
 * Adding a drill is NLP-validated server-side, so the error message surfaces
 * when a sentence is missing its {{answer}} blank or the answer doesn't
 * validate in the language.
 */
export default function DrillsEditor({
  pointId,
  canEdit = false,
}: {
  pointId: string
  /** reviewer/admin: unlocks in-place editing of live drills */
  canEdit?: boolean
}) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [sentence, setSentence] = useState('')
  const [answer, setAnswer] = useState('')
  const [translation, setTranslation] = useState('')
  // In-place edit state: which drill, the edited fields, and the REQUIRED
  // change note (the submit friction — server rejects notes under 10 chars).
  const [editingId, setEditingId] = useState<string | null>(null)
  const [edit, setEdit] = useState({ sentence: '', answer: '', translation: '', hint: '' })
  const [changeNote, setChangeNote] = useState('')

  const { data: drills = [], isLoading } = useQuery({
    queryKey: ['drills', pointId],
    queryFn: () => getDrills(pointId),
    enabled: open,
  })

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['drills', pointId] })

  const addMutation = useMutation({
    mutationFn: () => addDrill(pointId, { sentence, answer, translation }),
    onSuccess: () => {
      setSentence('')
      setAnswer('')
      setTranslation('')
      invalidate()
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (drillId: string) => deleteDrill(pointId, drillId),
    onSuccess: invalidate,
  })

  const editMutation = useMutation({
    mutationFn: () =>
      updateDrill(pointId, editingId!, { ...edit, change_note: changeNote.trim() }),
    onSuccess: () => {
      setEditingId(null)
      setChangeNote('')
      invalidate()
      queryClient.invalidateQueries({ queryKey: ['contribute-grammar'] })
    },
  })

  const startEdit = (d: { id: string; sentence: string; answer: string; translation: string | null; hint: string | null }) => {
    setEditingId(d.id)
    setEdit({
      sentence: d.sentence,
      answer: d.answer,
      translation: d.translation ?? '',
      hint: d.hint ?? '',
    })
    setChangeNote('')
    editMutation.reset()
  }

  const submitEdit = () => {
    if (
      window.confirm(
        'Save this edit? The point goes back to "pending review" and a different reviewer must approve it before learners see the change.',
      )
    ) {
      editMutation.mutate()
    }
  }

  return (
    <div className="border-t border-gray-100 pt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-xs text-lang hover:underline"
      >
        {open ? 'Hide sentences' : 'Edit sentences'}
      </button>

      {open && (
        <div className="mt-2 space-y-2" data-testid="drills-editor">
          {isLoading && <p className="text-xs text-gray-400">Loading…</p>}

          {drills.map((d) =>
            editingId === d.id ? (
              <div key={d.id} className="rounded-lg border border-lang/40 bg-lang-soft p-2 space-y-1" data-testid="drill-edit-form">
                <input
                  value={edit.sentence}
                  onChange={(e) => setEdit((v) => ({ ...v, sentence: e.target.value }))}
                  aria-label="Edit sentence"
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm font-mono"
                />
                <div className="flex gap-2">
                  <input
                    value={edit.answer}
                    onChange={(e) => setEdit((v) => ({ ...v, answer: e.target.value }))}
                    aria-label="Edit answer"
                    className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                  <input
                    value={edit.translation}
                    onChange={(e) => setEdit((v) => ({ ...v, translation: e.target.value }))}
                    aria-label="Edit translation"
                    placeholder="Translation"
                    className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                  <input
                    value={edit.hint}
                    onChange={(e) => setEdit((v) => ({ ...v, hint: e.target.value }))}
                    aria-label="Edit hint"
                    placeholder="Hint"
                    className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                </div>
                <input
                  value={changeNote}
                  onChange={(e) => setChangeNote(e.target.value)}
                  aria-label="Why this change?"
                  placeholder="Why this change? (required, min 10 characters — filed for re-review)"
                  className="w-full rounded border border-amber-300 bg-amber-50 px-2 py-1 text-sm"
                />
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={submitEdit}
                    disabled={
                      changeNote.trim().length < 10 ||
                      !edit.sentence.trim() ||
                      !edit.answer.trim() ||
                      editMutation.isPending
                    }
                    className="bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on rounded px-3 py-1 text-xs font-semibold"
                  >
                    {editMutation.isPending ? 'Saving…' : 'Save edit (needs re-approval)'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditingId(null)}
                    className="text-xs text-gray-500 hover:underline"
                  >
                    Cancel
                  </button>
                </div>
                {editMutation.isError && (
                  <p className="text-xs text-red-500">{errorMessage(editMutation.error)}</p>
                )}
              </div>
            ) : (
              <div key={d.id} className="flex items-start justify-between gap-2 text-sm">
                <div>
                  <span className="font-mono">{d.sentence}</span>
                  <span className="text-gray-500"> → {d.answer}</span>
                  {d.translation && (
                    <span className="block text-xs text-gray-400">{d.translation}</span>
                  )}
                </div>
                <span className="flex gap-2 shrink-0">
                  {canEdit && (
                    <button
                      type="button"
                      onClick={() => startEdit(d)}
                      className="text-xs text-lang hover:underline"
                    >
                      Edit
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => deleteMutation.mutate(d.id)}
                    className="text-xs text-red-500 hover:underline"
                  >
                    Delete
                  </button>
                </span>
              </div>
            ),
          )}

          <div className="space-y-1 pt-1">
            <input
              value={sentence}
              onChange={(e) => setSentence(e.target.value)}
              placeholder="Sentence with {{answer}} blank, e.g. Kitap {{answer}}."
              className="w-full rounded border border-gray-300 px-2 py-1 text-sm font-mono"
            />
            <div className="flex gap-2">
              <input
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Answer (e.g. masada)"
                className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm"
              />
              <input
                value={translation}
                onChange={(e) => setTranslation(e.target.value)}
                placeholder="Translation"
                className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm"
              />
              <button
                type="button"
                onClick={() => addMutation.mutate()}
                disabled={!sentence.trim() || !answer.trim() || addMutation.isPending}
                className="bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on rounded px-3 py-1 text-sm"
              >
                Add
              </button>
            </div>
            {addMutation.isError && (
              <p className="text-xs text-red-500">{errorMessage(addMutation.error)}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
