import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  explainSentence,
  generateReading,
  getReading,
  getReadings,
} from '../../api/reader'
import type { Reading, ReaderSentence } from '../../api/reader'
import { createPersonalCard } from '../../api/notes'
import { getLanguages } from '../../api/profile'
import { usePrefsStore } from '../../stores/prefsStore'
import LanguageWrapper from '../../components/LanguageWrapper'
import SpeakButton from '../../components/SpeakButton'
import ExplanationView from '../../components/ExplanationView'

type Stage = 'guess' | 'assisted'

/**
 * WP21 — The Reader. The learner names a topic; the app writes a text at
 * exactly their level with a few new words seeded in guessable contexts.
 * Three-stage disclosure: guess first (tap a marked word, commit a guess,
 * then see the gloss), then hover/tap translations for everything, then
 * per-sentence grammar explanations on demand.
 */
export default function ReaderPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  const { data: languages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
  })
  const language = languages.find((l) => l.id === activeLanguageId)

  const [topic, setTopic] = useState('')
  const [reading, setReading] = useState<Reading | null>(null)
  const [stage, setStage] = useState<Stage>('guess')
  // Guess flow: which token is being guessed, and what's been revealed.
  const [guessing, setGuessing] = useState<{ s: number; t: number } | null>(null)
  const [guessText, setGuessText] = useState('')
  const [revealed, setRevealed] = useState<Set<string>>(new Set())
  // Assisted stage: tapped word gloss + shown translations/explanations.
  const [peeked, setPeeked] = useState<{ s: number; t: number } | null>(null)
  const [openTranslations, setOpenTranslations] = useState<Set<number>>(new Set())
  // Fetched once (it costs allowance), then freely shown/hidden.
  const [explanations, setExplanations] = useState<Record<number, string>>({})
  const [shownExplanations, setShownExplanations] = useState<Set<number>>(
    new Set(),
  )
  const [addedWords, setAddedWords] = useState<Set<string>>(new Set())

  const { data: shelf = [] } = useQuery({
    queryKey: ['readings', activeLanguageId],
    queryFn: () => getReadings(activeLanguageId!),
    enabled: !!activeLanguageId && !reading,
  })

  const resetReadingState = () => {
    setStage('guess')
    setGuessing(null)
    setGuessText('')
    setRevealed(new Set())
    setPeeked(null)
    setOpenTranslations(new Set())
    setExplanations({})
    setShownExplanations(new Set())
    setAddedWords(new Set())
  }

  const generateMutation = useMutation({
    mutationFn: () =>
      generateReading(activeLanguageId!, language!.code, topic.trim()),
    onSuccess: (res) => {
      resetReadingState()
      setReading({ ...res.reading, id: res.id, topic: topic.trim() } as Reading)
      queryClient.invalidateQueries({ queryKey: ['readings'] })
    },
  })

  const openMutation = useMutation({
    mutationFn: (id: string) => getReading(id),
    onSuccess: (res) => {
      resetReadingState()
      setStage('assisted') // re-reads start with help unlocked
      setReading(res)
    },
  })

  const explainMutation = useMutation({
    mutationFn: (sentenceIndex: number) =>
      explainSentence(reading!.id, sentenceIndex).then(
        (explanation) => ({ sentenceIndex, explanation }),
      ),
    onSuccess: ({ sentenceIndex, explanation }) => {
      setExplanations((prev) => ({ ...prev, [sentenceIndex]: explanation }))
      setShownExplanations((prev) => new Set(prev).add(sentenceIndex))
    },
  })

  const addWordMutation = useMutation({
    mutationFn: (w: { word: string; sentence: string; translation: string }) =>
      createPersonalCard({
        languageId: activeLanguageId!,
        languageCode: language!.code,
        sentence: w.sentence,
        answer: w.word,
        translation: w.translation,
      }),
    onSuccess: (_res, w) => {
      setAddedWords((prev) => new Set(prev).add(w.word))
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const key = (s: number, t: number) => `${s}:${t}`

  const commitGuess = () => {
    if (!guessing) return
    setRevealed((prev) => new Set(prev).add(key(guessing.s, guessing.t)))
    setGuessing(null)
    setGuessText('')
  }

  const renderToken = (
    sentence: ReaderSentence, sIdx: number, tIdx: number,
  ) => {
    const token = sentence.tokens[tIdx]
    const k = key(sIdx, tIdx)
    const isNew = !!token.new
    const isRevealed = revealed.has(k)
    const isPeeked = peeked?.s === sIdx && peeked?.t === tIdx

    if (stage === 'guess') {
      if (!isNew) return <span key={tIdx}>{token.t} </span>
      return (
        <span key={tIdx}>
          <button
            type="button"
            onClick={() => {
              if (!isRevealed) {
                setGuessing({ s: sIdx, t: tIdx })
                setGuessText('')
              }
            }}
            className={`border-b-2 border-dotted ${
              isRevealed
                ? 'border-green-400 text-green-800'
                : 'border-amber-400 hover:bg-amber-50'
            } rounded-sm`}
            title={isRevealed ? token.gloss : 'New word — tap to guess it'}
          >
            {token.t}
          </button>
          {isRevealed && (
            <span className="text-xs text-green-700"> ({token.gloss})</span>
          )}{' '}
        </span>
      )
    }

    // Assisted stage: every word peeks its gloss.
    return (
      <span key={tIdx}>
        <button
          type="button"
          onClick={() => setPeeked(isPeeked ? null : { s: sIdx, t: tIdx })}
          className={`rounded-sm ${
            isNew ? 'border-b-2 border-dotted border-amber-400' : ''
          } ${isPeeked ? 'bg-lang-soft text-lang-dark' : 'hover:bg-gray-100'}`}
          title={token.gloss}
        >
          {token.t}
        </button>
        {isPeeked && (
          <span className="text-xs text-lang"> ({token.gloss})</span>
        )}{' '}
      </span>
    )
  }

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
            <h1 className="text-xl font-bold text-gray-900">
              Read {language.name}
            </h1>
            <p className="text-xs text-gray-500">
              A text written at exactly your level — with a few new words to
              figure out
            </p>
          </div>
          <button
            type="button"
            onClick={() => (reading ? setReading(null) : navigate('/'))}
            className="text-sm text-lang hover:underline"
          >
            {reading ? '← My readings' : '← Dashboard'}
          </button>
        </div>

        {!reading && (
          <>
            <form
              onSubmit={(e) => {
                e.preventDefault()
                if (topic.trim() && !generateMutation.isPending) {
                  generateMutation.mutate()
                }
              }}
              className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
            >
              <label className="block text-sm font-medium text-gray-700">
                What do you want to read about?
              </label>
              <div className="flex gap-2">
                <input
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  maxLength={120}
                  placeholder="e.g. street food in Mexico City, the history of chess…"
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lang bg-white"
                />
                <button
                  type="submit"
                  disabled={!topic.trim() || generateMutation.isPending}
                  className="rounded-lg bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on px-4 py-2 text-sm font-semibold"
                  style={{ minHeight: '44px' }}
                >
                  {generateMutation.isPending ? 'Writing…' : 'Write it'}
                </button>
              </div>
              {generateMutation.isError && (
                <p className="text-xs text-red-600" role="alert">
                  Couldn't write that one — try again, or a different topic.
                </p>
              )}
              <p className="text-[11px] text-gray-400">
                Uses one tutor message per text.
              </p>
            </form>

            {shelf.length > 0 && (
              <div
                className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden"
                data-testid="reading-shelf"
              >
                {shelf.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => openMutation.mutate(r.id)}
                    className="w-full text-left px-4 py-3 border-t border-gray-100 first:border-t-0 hover:bg-gray-50"
                  >
                    <span className="text-sm font-medium text-gray-800 block">
                      {r.title}
                    </span>
                    <span className="text-xs text-gray-400">
                      {r.topic} · {r.level ?? ''} · {r.new_word_count} new words
                    </span>
                  </button>
                ))}
              </div>
            )}
          </>
        )}

        {reading && (
          <div className="space-y-3">
            {stage === 'guess' && (
              <div
                className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900"
                data-testid="guess-banner"
              >
                <span className="font-semibold">First pass: no translations.</span>{' '}
                Words with a dotted underline are new — tap one, commit a
                guess from the context, and only then see what it means. A
                guess (even a wrong one) makes the word stick far better than
                looking it up.
              </div>
            )}

            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
              <LanguageWrapper languageCode={language.code}>
                <h2 className="text-xl font-bold text-gray-900">
                  {reading.title}
                </h2>
              </LanguageWrapper>

              <LanguageWrapper languageCode={language.code}>
                <div className="text-lg leading-loose text-gray-900 space-y-3">
                  {reading.sentences.map((sentence, sIdx) => (
                    <div key={sIdx}>
                      <span>
                        {sentence.tokens.map((_tok, tIdx) =>
                          renderToken(sentence, sIdx, tIdx),
                        )}
                        {stage === 'assisted' && (
                          <SpeakButton
                            text={sentence.text}
                            languageCode={language.code}
                          />
                        )}
                      </span>
                      {stage === 'assisted' && (
                        <div className="text-xs text-gray-400 space-x-3">
                          <button
                            type="button"
                            onClick={() =>
                              setOpenTranslations((prev) => {
                                const next = new Set(prev)
                                if (next.has(sIdx)) next.delete(sIdx)
                                else next.add(sIdx)
                                return next
                              })
                            }
                            className="hover:text-lang"
                          >
                            {openTranslations.has(sIdx)
                              ? 'Hide translation'
                              : 'Translation'}
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              if (!explanations[sIdx]) {
                                explainMutation.mutate(sIdx)
                                return // fetched once; shown by onSuccess
                              }
                              setShownExplanations((prev) => {
                                const next = new Set(prev)
                                if (next.has(sIdx)) next.delete(sIdx)
                                else next.add(sIdx)
                                return next
                              })
                            }}
                            disabled={explainMutation.isPending}
                            className="hover:text-lang disabled:opacity-50"
                          >
                            {!explanations[sIdx]
                              ? 'Explain the grammar'
                              : shownExplanations.has(sIdx)
                                ? 'Hide explanation'
                                : 'Show explanation'}
                          </button>
                        </div>
                      )}
                      {stage === 'assisted' && openTranslations.has(sIdx) && (
                        <p className="text-sm text-gray-500">
                          {sentence.translation}
                        </p>
                      )}
                      {explanations[sIdx] && shownExplanations.has(sIdx) && (
                        <div
                          className="bg-gray-50 border border-gray-100 rounded-lg p-3 mt-1"
                          data-testid="sentence-explanation"
                        >
                          <ExplanationView
                            text={explanations[sIdx]}
                            className="text-sm text-gray-600"
                          />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </LanguageWrapper>
            </div>

            {guessing && (
              <div
                className="bg-white rounded-2xl shadow-sm border border-amber-200 p-4 space-y-2"
                data-testid="guess-panel"
              >
                <p className="text-sm text-gray-700">
                  What do you think{' '}
                  <span className="font-semibold">
                    {reading.sentences[guessing.s].tokens[guessing.t].t.replace(/[.,;:!?¿¡«»""]+$/u, '')}
                  </span>{' '}
                  means here?
                </p>
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    commitGuess()
                  }}
                  className="flex gap-2"
                >
                  <input
                    value={guessText}
                    onChange={(e) => setGuessText(e.target.value)}
                    placeholder="Your guess — from the context"
                    autoFocus
                    className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lang bg-white"
                  />
                  <button
                    type="submit"
                    className="rounded-lg bg-lang hover:bg-lang-dark text-lang-on px-4 py-2 text-sm font-semibold"
                    style={{ minHeight: '44px' }}
                  >
                    Reveal
                  </button>
                </form>
                <p className="text-[11px] text-gray-400">
                  No idea? Guess anyway — that's the exercise.
                </p>
              </div>
            )}

            {stage === 'guess' && (
              <button
                type="button"
                onClick={() => setStage('assisted')}
                className="w-full rounded-xl border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 font-semibold px-6 py-3 text-sm"
                style={{ minHeight: '44px' }}
              >
                I've read it once — unlock translations
              </button>
            )}

            {stage === 'assisted' && reading.new_words.length > 0 && (
              <div
                className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 space-y-2"
                data-testid="new-words"
              >
                <p className="text-xs uppercase tracking-wide text-gray-400">
                  New words from this text
                </p>
                {reading.new_words.map((w) => (
                  <div
                    key={w.word}
                    className="flex items-center justify-between gap-2 text-sm"
                  >
                    <span>
                      <span className="font-medium text-gray-900">{w.word}</span>
                      <span className="text-gray-500"> — {w.gloss}</span>
                    </span>
                    {addedWords.has(w.word) ? (
                      <span className="text-xs text-green-700">✓ In your reviews</span>
                    ) : (
                      <button
                        type="button"
                        onClick={() =>
                          addWordMutation.mutate({
                            word: w.word,
                            sentence:
                              reading.sentences[w.sentence_index]?.text ?? '',
                            translation:
                              reading.sentences[w.sentence_index]?.translation ??
                              '',
                          })
                        }
                        disabled={addWordMutation.isPending}
                        className="text-xs rounded-lg bg-lang hover:bg-lang-dark text-lang-on px-2.5 py-1.5 font-semibold disabled:opacity-50"
                      >
                        Add to reviews
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
