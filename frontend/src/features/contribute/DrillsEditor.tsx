import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { addDrill, deleteDrill, getDrills } from '../../api/contribute'

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
export default function DrillsEditor({ pointId }: { pointId: string }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [sentence, setSentence] = useState('')
  const [answer, setAnswer] = useState('')
  const [translation, setTranslation] = useState('')

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

  return (
    <div className="border-t border-gray-100 pt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-xs text-indigo-600 hover:underline"
      >
        {open ? 'Hide sentences' : 'Edit sentences'}
      </button>

      {open && (
        <div className="mt-2 space-y-2" data-testid="drills-editor">
          {isLoading && <p className="text-xs text-gray-400">Loading…</p>}

          {drills.map((d) => (
            <div key={d.id} className="flex items-start justify-between gap-2 text-sm">
              <div>
                <span className="font-mono">{d.sentence}</span>
                <span className="text-gray-500"> → {d.answer}</span>
                {d.translation && (
                  <span className="block text-xs text-gray-400">{d.translation}</span>
                )}
              </div>
              <button
                type="button"
                onClick={() => deleteMutation.mutate(d.id)}
                className="text-xs text-red-500 hover:underline shrink-0"
              >
                Delete
              </button>
            </div>
          ))}

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
                className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded px-3 py-1 text-sm"
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
