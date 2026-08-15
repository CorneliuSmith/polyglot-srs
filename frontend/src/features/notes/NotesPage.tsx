import { useEffect, useState } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import UiLanguageSwitcher from '../../components/UiLanguageSwitcher'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import { createPersonalCard, extractText, saveNote } from '../../api/notes'
import type { ExtractedSentence } from '../../api/notes'
import { usePrefsStore } from '../../stores/prefsStore'
import { languageDisplayName } from '../../lib/languages'
import LanguageWrapper from '../../components/LanguageWrapper'
import SpeakButton from '../../components/SpeakButton'
import { prefetchTTSMany } from '../../api/audio'

interface Selection {
  sentence: string
  answer: string
}

export default function NotesPage() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
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

  // Unlike curriculum text, a pasted passage is nobody else's cache hit — each
  // sentence is a real synth against the learner's own rate limit. Still worth
  // warming: this page exists to be read aloud sentence by sentence, and the
  // queue backs off on its own if the passage is long enough to push back.
  const languageCode = language?.code
  useEffect(() => {
    if (!sentences || !languageCode) return
    return prefetchTTSMany(
      languageCode,
      sentences.map((s) => s.sentence),
    )
  }, [sentences, languageCode])

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
        <p className="text-gray-500">{t('notes.pickLanguageFirst')}</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{t('dashboard.ownTextTitle')}</h1>
            <p className="text-xs text-gray-500">
              {t('notes.subtitle', { language: languageDisplayName(language.code, language.name, i18n.language) })}
            </p>
          </div>
          <span className="flex items-center gap-3">
            <UiLanguageSwitcher />
            <button type="button" onClick={() => navigate('/')} className="text-sm text-lang hover:underline">
              {t('nav.dashboard')}
            </button>
          </span>
        </div>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          placeholder={t('notes.pastePlaceholder', { language: languageDisplayName(language.code, language.name, i18n.language) })}
          className="w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lang"
        />
        <button
          type="button"
          onClick={() => extractMutation.mutate()}
          disabled={!text.trim() || extractMutation.isPending}
          className="bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-xl px-5 py-2.5 text-sm"
        >
          {extractMutation.isPending ? t('notes.analyzing') : t('notes.analyze')}
        </button>

        {addedCount > 0 && (
          <p className="text-sm text-green-700">
            {t('notes.addedCards', { count: addedCount })}
          </p>
        )}

        {sentences && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
            <p className="text-xs text-gray-500">
              {t('notes.highlightHint')}
            </p>
            {sentences.map((s, i) => (
              <div key={i} className="leading-loose flex items-start gap-1">
                <SpeakButton text={s.sentence} languageCode={language.code} />
                <LanguageWrapper languageCode={language.code}>
                  <span>
                    {s.words.length === 0 && s.sentence}
                    {s.words.map((w, j) => (
                      <button
                        key={j}
                        type="button"
                        title={w.definition ?? (w.known ? '' : t('notes.newWord'))}
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
          <div className="bg-white rounded-2xl shadow-sm border border-lang/30 p-4 space-y-2">
            <p className="text-sm text-gray-700">
              <Trans
                i18nKey="notes.cardLine"
                values={{ sentence: selection.sentence }}
                components={{ mono: <span className="font-mono" /> }}
              />
            </p>
            <p className="text-xs text-gray-500">
              <Trans
                i18nKey="notes.blankWord"
                values={{ answer: selection.answer }}
                components={{ answer: <span className="font-semibold" /> }}
              />
            </p>
            <input
              value={translation}
              onChange={(e) => setTranslation(e.target.value)}
              placeholder={t('notes.translationPlaceholder')}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => cardMutation.mutate()}
                disabled={cardMutation.isPending}
                className="bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on rounded-lg px-4 py-2 text-sm"
              >
                {cardMutation.isPending ? t('notes.adding') : t('notes.addCard')}
              </button>
              <button type="button" onClick={() => setSelection(null)} className="text-xs text-gray-500 hover:underline">
                {t('notes.cancel')}
              </button>
              {cardMutation.isError && (
                <span className="text-xs text-red-500">
                  {t('notes.addFailed')}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
