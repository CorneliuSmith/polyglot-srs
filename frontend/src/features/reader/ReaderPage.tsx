import { useEffect, useState } from 'react'
import { Headphones } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  explainSentence,
  generateReading,
  getReading,
  getReadings,
} from '../../api/reader'
import type { Reading, ReaderSentence, ReadingOptions } from '../../api/reader'
import { createPersonalCard } from '../../api/notes'
import { getLanguages } from '../../api/profile'
import { getUsageAllowance } from '../../api/tutor'
import { usePrefsStore } from '../../stores/prefsStore'
import LanguageWrapper from '../../components/LanguageWrapper'
import SpeakButton from '../../components/SpeakButton'
import UsageMeter from '../../components/UsageMeter'
import { TTS_LANGUAGES } from '../../api/audio'
import ExplanationView from '../../components/ExplanationView'

// 'listen' (TTS languages, new texts only): the text stays hidden and the
// learner may train their ear sentence-by-sentence before reading.
type Stage = 'listen' | 'guess' | 'assisted'

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
  // Per-text options (bounded): length, narrative voice, difficulty nudge.
  const [textOptions, setTextOptions] = useState<ReadingOptions>({
    length: 'medium', voice: 'any', complexity: 'level',
  })
  const [reading, setReading] = useState<Reading | null>(null)
  const [stage, setStage] = useState<Stage>('guess')
  // Listen-first: whether they took the ear-training option before reading.
  const [earMode, setEarMode] = useState(false)
  // Guess flow: which token is being guessed, and what's been revealed.
  const [guessing, setGuessing] = useState<{ s: number; t: number } | null>(null)
  const [guessText, setGuessText] = useState('')
  // Second-chance guessing: the first committed guess is held (not revealed) so
  // the learner re-reads the context and refines it once before the meaning shows.
  const [guessAttempt, setGuessAttempt] = useState(0)
  const [firstGuess, setFirstGuess] = useState('')
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
  const [failedWords, setFailedWords] = useState<Set<string>>(new Set())

  const { data: shelf = [] } = useQuery({
    queryKey: ['readings', activeLanguageId],
    queryFn: () => getReadings(activeLanguageId!),
    enabled: !!activeLanguageId && !reading,
  })

  // Every new text and every per-sentence explanation draws the same monthly
  // usage pool the Tutor does — surface it here too (owner).
  const { data: usage } = useQuery({
    queryKey: ['usage-allowance', activeLanguageId],
    queryFn: () => getUsageAllowance(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
  })

  const resetReadingState = () => {
    setStage('guess')
    setEarMode(false)
    setGuessing(null)
    setGuessText('')
    setRevealed(new Set())
    setPeeked(null)
    setOpenTranslations(new Set())
    setExplanations({})
    setShownExplanations(new Set())
    setAddedWords(new Set())
    setFailedWords(new Set())
  }

  const generateMutation = useMutation({
    mutationFn: () =>
      generateReading(activeLanguageId!, language!.code, topic.trim(), textOptions),
    onSuccess: (res) => {
      resetReadingState()
      // TTS languages: hold the text back and offer ear-first immersion.
      if (TTS_LANGUAGES.has(language!.code)) setStage('listen')
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
    mutationFn: (w: {
      word: string
      sentence: string
      translation: string
      gloss: string
    }) =>
      createPersonalCard({
        languageId: activeLanguageId!,
        languageCode: language!.code,
        sentence: w.sentence,
        answer: w.word,
        translation: w.translation,
        gloss: w.gloss,
      }),
    onSuccess: (_res, w) => {
      setAddedWords((prev) => new Set(prev).add(w.word))
      setFailedWords((prev) => {
        const next = new Set(prev)
        next.delete(w.word)
        return next
      })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['personal-cards'] })
    },
    onError: (_err, w) => {
      setFailedWords((prev) => new Set(prev).add(w.word))
    },
  })

  const key = (s: number, t: number) => `${s}:${t}`

  // Switching to a different word mid-guess starts its two tries fresh.
  useEffect(() => {
    setGuessAttempt(0)
    setFirstGuess('')
  }, [guessing?.s, guessing?.t])

  const revealGuess = () => {
    if (!guessing) return
    setRevealed((prev) => new Set(prev).add(key(guessing.s, guessing.t)))
    setGuessing(null)
    setGuessText('')
    setGuessAttempt(0)
    setFirstGuess('')
  }

  const commitGuess = () => {
    if (!guessing) return
    // First real guess never auto-reveals: hold it, send the learner back to
    // the sentence for one more read, then the second submit shows the meaning.
    if (guessAttempt === 0 && guessText.trim()) {
      setFirstGuess(guessText.trim())
      setGuessText('')
      setGuessAttempt(1)
      return
    }
    revealGuess()
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
              {/* Shape the text: three bounded choices, one pill row each. */}
              <div className="space-y-1.5" data-testid="text-options">
                {(
                  [
                    {
                      name: 'length' as const,
                      label: 'Length',
                      choices: [
                        ['short', 'Short'],
                        ['medium', 'Medium'],
                        ['long', 'Long'],
                      ],
                    },
                    {
                      name: 'voice' as const,
                      label: 'Style',
                      choices: [
                        ['any', 'Any'],
                        ['first', 'I-narrator'],
                        ['third', 'Third person'],
                        ['dialogue', 'Dialogue'],
                      ],
                    },
                    {
                      name: 'complexity' as const,
                      label: 'Challenge',
                      choices: [
                        ['easier', 'Easier'],
                        ['level', 'My level'],
                        ['stretch', 'Stretch'],
                      ],
                    },
                  ]
                ).map((group) => (
                  <div key={group.name} className="flex flex-wrap items-center gap-1.5">
                    <span className="w-16 text-[11px] uppercase tracking-wide text-gray-400">
                      {group.label}
                    </span>
                    {group.choices.map(([value, label]) => (
                      <button
                        key={value}
                        type="button"
                        aria-pressed={textOptions[group.name] === value}
                        onClick={() =>
                          setTextOptions((prev) => ({ ...prev, [group.name]: value }))
                        }
                        className={`rounded-full border px-2.5 py-1 text-[11px] transition-colors ${
                          textOptions[group.name] === value
                            ? 'border-lang/40 bg-lang-soft text-lang font-medium'
                            : 'border-gray-200 text-gray-500 hover:border-lang/50 hover:text-lang'
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                ))}
              </div>
              {generateMutation.isError && (
                <p className="text-xs text-red-600" role="alert">
                  Couldn't write that one — try again, or a different topic.
                </p>
              )}
              <p className="text-[11px] text-gray-400">
                Each new text counts toward your monthly usage.
              </p>
              <UsageMeter allowance={usage?.allowance} />
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

            {/* Listen-first (TTS languages): the text is HELD BACK — ear
                training before eyes is the closest thing to immersion. */}
            {stage === 'listen' && (
              <div
                className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4"
                data-testid="listen-first"
              >
                {!earMode ? (
                  <>
                    <h2 className="text-lg font-bold text-gray-900">
                      Your text is ready — ears first?
                    </h2>
                    <p className="text-sm text-gray-600">
                      Listening before you see the words trains real
                      comprehension. You can reveal the text at any point.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => setEarMode(true)}
                        className="rounded-xl bg-lang hover:bg-lang-dark text-lang-on font-semibold px-5 py-2.5 text-sm"
                        style={{ minHeight: '44px' }}
                      >
                        <Headphones aria-hidden className="mr-1.5 inline h-4 w-4 align-[-2px]" />Listen first
                      </button>
                      <button
                        type="button"
                        onClick={() => setStage('guess')}
                        className="rounded-xl border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 font-semibold px-5 py-2.5 text-sm"
                        style={{ minHeight: '44px' }}
                      >
                        Show me the text
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="text-sm text-gray-600">
                      Play each line and picture what's happening. When
                      you've had a listen, reveal the text and read for real.
                    </p>
                    <ol className="space-y-2" data-testid="listen-lines">
                      {reading.sentences.map((sentence, sIdx) => (
                        <li
                          key={sIdx}
                          className="flex items-center gap-3 rounded-xl border border-gray-100 bg-gray-50 px-3 py-2"
                        >
                          <span className="text-xs tabular-nums text-gray-400 w-6">
                            {sIdx + 1}.
                          </span>
                          <SpeakButton
                            text={sentence.text}
                            languageCode={language.code}
                          />
                          <span className="text-xs text-gray-300 select-none">
                            ································
                          </span>
                        </li>
                      ))}
                    </ol>
                    <button
                      type="button"
                      onClick={() => setStage('guess')}
                      className="w-full rounded-xl bg-lang hover:bg-lang-dark text-lang-on font-semibold px-6 py-3 text-sm"
                      style={{ minHeight: '44px' }}
                    >
                      Show the text →
                    </button>
                  </>
                )}
              </div>
            )}

            {stage !== 'listen' && (
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
                        <SpeakButton
                          text={sentence.text}
                          languageCode={language.code}
                        />
                      </span>
                      {/* Per-sentence help: two stable toggle pills, and ONE
                          combined panel underneath — labelled sections instead
                          of loose links and scattered boxes. */}
                      {stage === 'assisted' && (
                        <div
                          className="mt-1 flex items-center gap-1.5"
                          data-testid="sentence-actions"
                        >
                          <button
                            type="button"
                            aria-pressed={openTranslations.has(sIdx)}
                            onClick={() =>
                              setOpenTranslations((prev) => {
                                const next = new Set(prev)
                                if (next.has(sIdx)) next.delete(sIdx)
                                else next.add(sIdx)
                                return next
                              })
                            }
                            className={`rounded-full border px-2.5 py-1 text-[11px] transition-colors ${
                              openTranslations.has(sIdx)
                                ? 'border-lang/40 bg-lang-soft text-lang'
                                : 'border-gray-200 text-gray-500 hover:border-lang/50 hover:text-lang'
                            }`}
                          >
                            Translation
                          </button>
                          <button
                            type="button"
                            aria-pressed={
                              !!explanations[sIdx] && shownExplanations.has(sIdx)
                            }
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
                            className={`rounded-full border px-2.5 py-1 text-[11px] transition-colors disabled:opacity-50 ${
                              explanations[sIdx] && shownExplanations.has(sIdx)
                                ? 'border-lang/40 bg-lang-soft text-lang'
                                : 'border-gray-200 text-gray-500 hover:border-lang/50 hover:text-lang'
                            }`}
                          >
                            {explainMutation.isPending &&
                            explainMutation.variables === sIdx
                              ? 'Explaining…'
                              : 'Grammar'}
                          </button>
                        </div>
                      )}
                      {((stage === 'assisted' && openTranslations.has(sIdx)) ||
                        (explanations[sIdx] && shownExplanations.has(sIdx))) && (
                        <div
                          className="mt-1.5 rounded-xl bg-gray-50 border border-gray-100 p-3 space-y-2"
                          data-testid="sentence-help"
                        >
                          {stage === 'assisted' && openTranslations.has(sIdx) && (
                            <p className="text-sm text-gray-600">
                              <span className="mr-2 text-[10px] uppercase tracking-wide text-gray-400">
                                Translation
                              </span>
                              {sentence.translation}
                            </p>
                          )}
                          {explanations[sIdx] && shownExplanations.has(sIdx) && (
                            <div data-testid="sentence-explanation">
                              <span className="block text-[10px] uppercase tracking-wide text-gray-400 mb-1">
                                Grammar
                              </span>
                              <ExplanationView
                                text={explanations[sIdx]}
                                className="text-sm text-gray-600"
                              />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </LanguageWrapper>
            </div>
            )}

            {guessing && (
              <div
                className="bg-white rounded-2xl shadow-sm border border-amber-200 p-4 space-y-2"
                data-testid="guess-panel"
              >
                {guessAttempt === 0 ? (
                  <p className="text-sm text-gray-700">
                    What do you think{' '}
                    <span className="font-semibold">
                      {reading.sentences[guessing.s].tokens[guessing.t].t.replace(/[.,;:!?¿¡«»""]+$/u, '')}
                    </span>{' '}
                    means here?
                  </p>
                ) : (
                  <p className="text-sm text-gray-700" data-testid="second-chance">
                    You said <span className="font-semibold">“{firstGuess}”</span>.
                    Read the sentence once more — does it still fit? One more
                    guess, then the meaning.
                  </p>
                )}
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
                    placeholder={
                      guessAttempt === 0
                        ? 'Your guess — from the context'
                        : 'Refine it — or stand by your first guess'
                    }
                    autoFocus
                    className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lang bg-white"
                  />
                  <button
                    type="submit"
                    className="rounded-lg bg-lang hover:bg-lang-dark text-lang-on px-4 py-2 text-sm font-semibold"
                    style={{ minHeight: '44px' }}
                  >
                    {guessAttempt === 0 && guessText.trim() ? 'Lock it in' : 'Reveal'}
                  </button>
                </form>
                <p className="text-[11px] text-gray-400">
                  {guessAttempt === 0 ? (
                    <>
                      No idea? Guess anyway — that&apos;s the exercise. Two tries,
                      then the meaning shows.
                    </>
                  ) : (
                    <button
                      type="button"
                      onClick={revealGuess}
                      className="underline hover:text-gray-600"
                    >
                      Standing by my first guess — show the meaning
                    </button>
                  )}
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
                      <span
                        className="inline-flex items-center gap-1 text-xs font-semibold text-green-700"
                        data-testid="word-added"
                      >
                        ✓ Added
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        {failedWords.has(w.word) && (
                          <span className="text-xs text-red-600" role="alert">
                            Couldn't add
                          </span>
                        )}
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
                              gloss: w.gloss,
                            })
                          }
                          disabled={
                            addWordMutation.isPending &&
                            addWordMutation.variables?.word === w.word
                          }
                          className="text-xs rounded-lg bg-lang hover:bg-lang-dark text-lang-on px-2.5 py-1.5 font-semibold disabled:opacity-50"
                        >
                          {addWordMutation.isPending &&
                          addWordMutation.variables?.word === w.word
                            ? 'Adding…'
                            : failedWords.has(w.word)
                              ? 'Retry'
                              : 'Add to reviews'}
                        </button>
                      </span>
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
