import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import { createPersonalCard, extractText, saveNote } from '../../api/notes'
import type { ExtractedSentence } from '../../api/notes'
import { usePrefsStore } from '../../stores/prefsStore'
import LanguageWrapper from '../../components/LanguageWrapper'

interface Selection {
  sentence: string
  answer: string
}

export default function NotesPage() {
  const navigate = useNavigate()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const [text, setText] = useState('')
  const [sentences, setSentences] = useState<ExtractedSentence[] | null>(null)
  const [selection, setSelection] = useState<Selection | null>(null)
  const [translation, setTranslation] = useState('')
  const [addedCount, setAddedCount] = useState(0)
  // The pasted text is saved once as a note (lazily, on the first card) so the
  // cards made from it link back to the passage they came from.
  const [noteId, setNoteId] = useState<string | null>(null)

  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })
  const language = languages.find((l) => l.id === activeLanguageId)

  const extractMutation = useMutation({
    mutationFn: () => extractText(activeLanguageId!, language!.code, text),
    onSuccess: (result) => {
      setSentences(result)
      // A fresh analysis is a new source passage — start a new note.
      setNoteId(null)
      setAddedCount(0)
    },
  })

  const cardMutation = useMutation({
    mutationFn: async () => {
      let nid = noteId
      if (!nid) {
        const title = text.trim().split(/\s+/).slice(0, 6).join(' ')
        const note = await saveNote(activeLanguageId!, text, title)
        nid = note.id
        setNoteId(nid)
      }
      return createPersonalCard({
        languageId: activeLanguageId!,
        languageCode: language!.code,
        sentence: selection!.sentence,
        answer: selection!.answer,
        translation,
        noteId: nid,
      })
    },
    onSuccess: () => {
      setAddedCount((n) => n + 1)
      setSelection(null)
      setTranslation('')
    },
  })

  if (!language) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Pick a language on the dashboard first.</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Learn from your own text</h1>
            <p className="text-xs text-gray-500">
              Paste {language.name} text, then tap a word to turn its sentence into a card.
            </p>
          </div>
          <button type="button" onClick={() => navigate('/')} className="text-sm text-indigo-600 hover:underline">
            Dashboard
          </button>
        </div>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          placeholder={`Paste ${language.name} text here…`}
          className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          type="button"
          onClick={() => extractMutation.mutate()}
          disabled={!text.trim() || extractMutation.isPending}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl px-5 py-2.5 text-sm"
        >
          {extractMutation.isPending ? 'Analyzing…' : 'Analyze'}
        </button>

        {addedCount > 0 && (
          <p className="text-sm text-green-700">
            Added {addedCount} card{addedCount > 1 ? 's' : ''} to your reviews.
          </p>
        )}

        {sentences && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
            <p className="text-xs text-gray-400">
              New words are highlighted. Tap any word to make a fill-in-the-blank card.
            </p>
            {sentences.map((s, i) => (
              <div key={i} className="leading-loose">
                <LanguageWrapper languageCode={language.code}>
                  <span>
                    {s.words.length === 0 && s.sentence}
                    {s.words.map((w, j) => (
                      <button
                        key={j}
                        type="button"
                        title={w.definition ?? (w.known ? '' : 'new word')}
                        onClick={() => {
                          setSelection({ sentence: s.sentence, answer: w.word })
                          setTranslation('')
                        }}
                        className={
                          'mx-0.5 rounded px-0.5 ' +
                          (w.known
                            ? 'text-gray-800 underline decoration-dotted decoration-gray-300 hover:bg-gray-100'
                            : 'bg-amber-100 text-amber-900 hover:bg-amber-200')
                        }
                      >
                        {w.word}
                      </button>
                    ))}
                  </span>
                </LanguageWrapper>
              </div>
            ))}
          </div>
        )}

        {selection && (
          <div className="bg-white rounded-2xl shadow-sm border border-indigo-200 p-4 space-y-2">
            <p className="text-sm text-gray-700">
              Card: <span className="font-mono">{selection.sentence}</span>
            </p>
            <p className="text-xs text-gray-500">
              Blank the word <span className="font-semibold">{selection.answer}</span>.
            </p>
            <input
              value={translation}
              onChange={(e) => setTranslation(e.target.value)}
              placeholder="Translation / note (optional)"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => cardMutation.mutate()}
                disabled={cardMutation.isPending}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg px-4 py-2 text-sm"
              >
                {cardMutation.isPending ? 'Adding…' : 'Add card'}
              </button>
              <button type="button" onClick={() => setSelection(null)} className="text-xs text-gray-400 hover:underline">
                Cancel
              </button>
              {cardMutation.isError && (
                <span className="text-xs text-red-500">
                  Couldn’t add — pick a different word.
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
