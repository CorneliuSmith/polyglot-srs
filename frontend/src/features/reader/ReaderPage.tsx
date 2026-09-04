import { useEffect, useState } from 'react'
import { languageDisplayName } from '../../lib/languages'
import UiLanguageSwitcher from '../../components/UiLanguageSwitcher'
import AiDisclaimer from '../../components/AiDisclaimer'
import { Trans, useTranslation } from 'react-i18next'
import { Headphones, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteReading,
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
import { usePendingReadingStore } from '../../stores/pendingReadingStore'
import ReadingWait from './ReadingWait'
import LanguageWrapper from '../../components/LanguageWrapper'
import { prefetchTTSMany } from '../../api/audio'
import Annotatable from '../contribute/Annotatable'
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
  const { t, i18n } = useTranslation()
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
  // A phrase the learner highlighted inside one sentence (owner: "hover/
  // highlight over a word/phrase to add it"). Single words go through the
  // peek instead; this is for the multi-word selection.
  const [phraseSel, setPhraseSel] = useState<{ s: number; text: string } | null>(null)
  const [openTranslations, setOpenTranslations] = useState<Set<number>>(new Set())
  // Fetched once (it costs allowance), then freely shown/hidden.
  // Warm every sentence's audio as soon as the reading arrives. A reading is
  // a page of speaker buttons and the learner reads top to bottom, so the
  // queue is fed in that order — by the time they reach sentence three it has
  // usually been synthesized already. Cancelled on unmount so navigating away
  // stops work nobody is waiting for.
  useEffect(() => {
    if (!reading || !language?.code) return
    return prefetchTTSMany(
      language.code,
      reading.sentences.map((s) => s.text),
    )
  }, [reading, language?.code])

  const [explanations, setExplanations] = useState<Record<number, string>>({})
  const [shownExplanations, setShownExplanations] = useState<Set<number>>(
    new Set(),
  )
  const [addedWords, setAddedWords] = useState<Set<string>>(new Set())
  // Which deck the last save went into, so the confirmation can say where.
  const [savedDeck, setSavedDeck] = useState<string | null>(null)
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

  // Generation is owned by the STORE, not by this page: the learner is
  // invited to go play or run reviews while the text is written (#286),
  // and a mutation dies with the component that started it — the finished
  // text would be dropped on the floor the moment they navigated away.
  const pendingJob = usePendingReadingStore((s) => s.pending)
  const readyReading = usePendingReadingStore((s) => s.ready)
  const generateFailed = usePendingReadingStore((s) => s.error)
  const startGeneration = usePendingReadingStore((s) => s.start)
  const claimReading = usePendingReadingStore((s) => s.claim)

  const showReading = (res: {
    id: string
    reading: Omit<Reading, 'id' | 'topic'>
    topic: string
  }) => {
    resetReadingState()
    // TTS languages: hold the text back and offer ear-first immersion.
    if (TTS_LANGUAGES.has(language!.code)) setStage('listen')
    setReading({ ...res.reading, id: res.id, topic: res.topic } as Reading)
    queryClient.invalidateQueries({ queryKey: ['readings'] })
  }

  // Claim whatever finished — whether the learner sat here the whole time
  // or came back by the banner after a round of reviews.
  useEffect(() => {
    if (!readyReading || !language) return
    const claimed = claimReading()
    if (claimed) showReading(claimed)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readyReading, language])

  const startWriting = () => {
    if (!activeLanguageId || !language || !topic.trim()) return
    const asked = topic.trim()
    startGeneration(
      {
        topic: asked,
        languageId: activeLanguageId,
        languageCode: language.code,
        startedAt: Date.now(),
      },
      generateReading(activeLanguageId, language.code, asked, textOptions),
    )
  }

  // Shelf housekeeping (owner request): drop an old text, keep every word
  // it taught. Nothing links a saved card to its reading, so this is purely
  // a tidy-up — the confirm dialog says as much.
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteReading(id),
    onSuccess: () => {
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
        source: 'reading',
      }),
    onSuccess: (res, w) => {
      // Name the deck. "Added to your reviews" was true but useless — the
      // learner had no way to find the word again, and nothing on the Decks
      // page showed it, so saving felt like it hadn't worked.
      if (res.deck_name) setSavedDeck(res.deck_name)
      setAddedWords((prev) => new Set(prev).add(w.word))
      setFailedWords((prev) => {
        const next = new Set(prev)
        next.delete(w.word)
        return next
      })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['personal-cards'] })
      queryClient.invalidateQueries({ queryKey: ['personal-decks'] })
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
            title={isRevealed ? token.gloss : t('reader.newWordTitle')}
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
          <span className="text-xs text-lang">
            {' '}({token.gloss})
            {/* Any word, not only the flagged ones — the learner picks what
                they want to keep (owner: "words of their choice from the
                text"). The same card the new-words list below makes. */}
            {addedWords.has(token.t) ? (
              <span className="ms-1 font-semibold text-green-700">{t('reader.added')}</span>
            ) : (
              <button
                type="button"
                onClick={() =>
                  addWordMutation.mutate({
                    word: token.t,
                    sentence: sentence.text,
                    translation: sentence.translation ?? '',
                    gloss: token.gloss ?? '',
                  })
                }
                disabled={addWordMutation.isPending}
                data-testid={`add-word-${sIdx}-${tIdx}`}
                className="ms-1 rounded bg-lang px-1.5 py-0.5 text-[10px] font-semibold text-lang-on disabled:opacity-50"
              >
                {t('reader.addWord')}
              </button>
            )}
          </span>
        )}{' '}
      </span>
    )
  }

  /** A highlighted run of words inside one sentence becomes an offer to
   * add it as a phrase card. Only in the assisted stage, only multi-word
   * (single words have the peek), and only a sensible length. */
  const captureSelection = (sIdx: number) => {
    if (stage !== 'assisted') return
    const text = window.getSelection()?.toString().trim() ?? ''
    if (!text || !/\s/.test(text) || text.length > 80) {
      setPhraseSel(null)
      return
    }
    setPhraseSel({ s: sIdx, text })
  }

  if (!language) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">{t('reader.pickLanguageFirst')}</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              {t('reader.title', { language: languageDisplayName(language.code, language.name, i18n.language) })}
            </h1>
            <p className="text-xs text-gray-500">{t('reader.subtitle')}</p>
          </div>
          <span className="flex items-center gap-3">
            <UiLanguageSwitcher />
            <button
              type="button"
              onClick={() => (reading ? setReading(null) : navigate('/'))}
              className="text-sm text-lang hover:underline"
            >
              {reading ? t('reader.myReadings') : t('common.backToDashboard')}
            </button>
          </span>
        </div>

        {!reading && (
          <>
            <form
              onSubmit={(e) => {
                e.preventDefault()
                if (topic.trim() && !pendingJob) startWriting()
              }}
              className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
            >
              <label className="block text-sm font-medium text-gray-700">
                {t('reader.promptTitle')}
              </label>
              <div className="flex gap-2">
                <input
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  maxLength={120}
                  placeholder={t('reader.promptPlaceholder')}
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lang bg-white"
                />
                <button
                  type="submit"
                  disabled={!topic.trim() || !!pendingJob}
                  className="rounded-lg bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on px-4 py-2 text-sm font-semibold"
                  style={{ minHeight: '44px' }}
                >
                  {pendingJob ? t('reader.writing') : t('reader.writeIt')}
                </button>
              </div>
              {/* Shape the text: three bounded choices, one pill row each. */}
              <div className="space-y-1.5" data-testid="text-options">
                {(
                  [
                    {
                      name: 'length' as const,
                      label: t('reader.length'),
                      choices: [
                        ['short', t('reader.short')],
                        ['medium', t('reader.medium')],
                        ['long', t('reader.long')],
                      ],
                    },
                    {
                      name: 'voice' as const,
                      label: t('reader.style'),
                      choices: [
                        ['any', t('reader.any')],
                        ['first', t('reader.firstPerson')],
                        ['third', t('reader.thirdPerson')],
                        ['dialogue', t('reader.dialogue')],
                      ],
                    },
                    {
                      name: 'complexity' as const,
                      label: t('reader.challenge'),
                      // Relative dials first, then explicit CEFR pins —
                      // the codes are level names in every locale.
                      choices: [
                        ['easier', t('reader.easier')],
                        ['level', t('reader.myLevel')],
                        ['stretch', t('reader.stretch')],
                        ['A1', 'A1'],
                        ['A2', 'A2'],
                        ['B1', 'B1'],
                        ['B2', 'B2'],
                        ['C1', 'C1'],
                        ['C2', 'C2'],
                        // Above C2 the CEFR ladder stops, so these are
                        // registers rather than levels — named, not coded,
                        // because "C3" would be a fiction.
                        ['native', t('reader.registerNative')],
                        ['academic', t('reader.registerAcademic')],
                        ['literary', t('reader.registerLiterary')],
                        ['professional', t('reader.registerProfessional')],
                      ],
                    },
                  ]
                ).map((group) => (
                  <div key={group.name} className="flex flex-wrap items-center gap-1.5">
                    <span className="w-16 text-[11px] uppercase tracking-wide text-gray-500">
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
                {/* Said once, where the choice is made: the three chips at
                    the end of the challenge row are not levels. */}
                {['native', 'academic', 'literary', 'professional'].includes(
                  textOptions.complexity,
                ) && (
                  <p
                    className="text-[11px] leading-snug text-gray-500"
                    data-testid="reader-register-hint"
                  >
                    {t('reader.registerHint')}
                  </p>
                )}
              </div>
              {generateFailed && (
                <p className="text-xs text-red-600" role="alert">
                  {t('reader.generateError')}
                </p>
              )}
              <p className="text-[11px] text-gray-500">
                {t('reader.usageNote')}
              </p>
              <UsageMeter allowance={usage?.allowance} />
            </form>

            {/* The wait is no longer dead time: play the word game over
                due words, or go run reviews — the text finds them either
                way (components/ReadingReadyBanner). */}
            {pendingJob && (
              <ReadingWait
                languageId={pendingJob.languageId}
                topic={pendingJob.topic}
              />
            )}

            {shelf.length > 0 && (
              <div
                className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden"
                data-testid="reading-shelf"
              >
                {shelf.map((r) => (
                  <div
                    key={r.id}
                    className="flex items-center border-t border-gray-100 first:border-t-0 hover:bg-gray-50"
                  >
                    <button
                      type="button"
                      onClick={() => openMutation.mutate(r.id)}
                      className="flex-1 text-start px-4 py-3"
                    >
                      <span className="text-sm font-medium text-gray-800 block">
                        {r.title}
                      </span>
                      <span className="text-xs text-gray-500">
                        {r.topic} · {r.level ?? ''} ·{' '}
                        {t('reader.shelfNewWords', { count: r.new_word_count })}
                      </span>
                    </button>
                    {/* Housekeeping only: the confirm says so out loud,
                        because "delete" next to a text you learned words
                        from reads like it takes the words too. It cannot —
                        saved words are separate cards. */}
                    <button
                      type="button"
                      onClick={() => {
                        if (
                          window.confirm(
                            t('reader.deleteConfirm', { title: r.title }),
                          )
                        ) {
                          deleteMutation.mutate(r.id)
                        }
                      }}
                      disabled={deleteMutation.isPending}
                      aria-label={t('reader.deleteAria', { title: r.title })}
                      title={t('reader.deleteAria', { title: r.title })}
                      className="me-2 shrink-0 rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
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
                <Trans
                  i18nKey="reader.guessBanner"
                  components={{ b: <span className="font-semibold" /> }}
                />
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
                      {t('reader.listenTitle')}
                    </h2>
                    <p className="text-sm text-gray-600">
                      {t('reader.listenIntro')}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => setEarMode(true)}
                        className="rounded-xl bg-lang hover:bg-lang-dark text-lang-on font-semibold px-5 py-2.5 text-sm"
                        style={{ minHeight: '44px' }}
                      >
                        <Headphones aria-hidden className="me-1.5 inline h-4 w-4 align-[-2px]" />{t('reader.listenFirst')}
                      </button>
                      <button
                        type="button"
                        onClick={() => setStage('guess')}
                        className="rounded-xl border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 font-semibold px-5 py-2.5 text-sm"
                        style={{ minHeight: '44px' }}
                      >
                        {t('reader.showMeText')}
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="text-sm text-gray-600">
                      {t('reader.listenLines')}
                    </p>
                    <ol className="space-y-2" data-testid="listen-lines">
                      {reading.sentences.map((sentence, sIdx) => (
                        <li
                          key={sIdx}
                          className="flex items-center gap-3 rounded-xl border border-gray-100 bg-gray-50 px-3 py-2"
                        >
                          <span className="text-xs tabular-nums text-gray-500 w-6">
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
                      {t('reader.showTextArrow')}
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
                {/* One region for the whole reading rather than one per
                    sentence: a reviewer can then select ACROSS sentences
                    (owner: "the sentences (of multiple)"), and the tokens
                    stay clickable instead of being buried under per-sentence
                    flag buttons. */}
                <Annotatable
                  languageId={activeLanguageId}
                  targetType="reading"
                  targetId={reading.id}
                  targetLabel={reading.title ?? null}
                  field="sentence"
                  source="reader"
                  className="text-lg leading-loose text-gray-900 space-y-3"
                >
                  {reading.sentences.map((sentence, sIdx) => (
                    <div
                      key={sIdx}
                      data-s={sIdx}
                      onMouseUp={() => captureSelection(sIdx)}
                      onTouchEnd={() => captureSelection(sIdx)}
                    >
                      <span>
                        {sentence.tokens.map((_tok, tIdx) =>
                          renderToken(sentence, sIdx, tIdx),
                        )}
                        <SpeakButton
                          text={sentence.text}
                          languageCode={language.code}
                        />
                      </span>
                      {phraseSel?.s === sIdx && (
                        <div className="mt-1" data-testid="phrase-add">
                          {addedWords.has(phraseSel.text) ? (
                            <span className="text-xs font-semibold text-green-700">
                              {t('reader.added')}
                            </span>
                          ) : (
                            <button
                              type="button"
                              onClick={() =>
                                addWordMutation.mutate({
                                  word: phraseSel.text,
                                  sentence: sentence.text,
                                  translation: sentence.translation ?? '',
                                  gloss: '',
                                })
                              }
                              disabled={addWordMutation.isPending}
                              className="rounded-lg bg-lang px-2.5 py-1 text-xs font-semibold text-lang-on disabled:opacity-50"
                            >
                              {t('reader.addPhrase', { phrase: phraseSel.text })}
                            </button>
                          )}
                        </div>
                      )}
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
                            {t('reader.translation')}
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
                              ? t('reader.explaining')
                              : t('common.grammar')}
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
                              <span className="me-2 text-[10px] uppercase tracking-wide text-gray-500">
                                {t('reader.translation')}
                              </span>
                              {sentence.translation}
                            </p>
                          )}
                          {explanations[sIdx] && shownExplanations.has(sIdx) && (
                            <div data-testid="sentence-explanation">
                              <span className="block text-[10px] uppercase tracking-wide text-gray-500 mb-1">
                                {t('common.grammar')}
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
                </Annotatable>
                <AiDisclaimer className="mt-2" />
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
                    <Trans
                      i18nKey="reader.guessQuestion"
                      values={{
                        word: reading.sentences[guessing.s].tokens[guessing.t].t.replace(/[.,;:!?¿¡«»""]+$/u, ''),
                      }}
                      components={{ w: <span className="font-semibold" /> }}
                    />
                  </p>
                ) : (
                  <p className="text-sm text-gray-700" data-testid="second-chance">
                    <Trans
                      i18nKey="reader.secondChance"
                      values={{ guess: firstGuess }}
                      components={{ g: <span className="font-semibold" /> }}
                    />
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
                        ? t('reader.guessPlaceholderFirst')
                        : t('reader.guessPlaceholderSecond')
                    }
                    autoFocus
                    className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lang bg-white"
                  />
                  <button
                    type="submit"
                    className="rounded-lg bg-lang hover:bg-lang-dark text-lang-on px-4 py-2 text-sm font-semibold"
                    style={{ minHeight: '44px' }}
                  >
                    {guessAttempt === 0 && guessText.trim() ? t('reader.lockItIn') : t('reader.reveal')}
                  </button>
                </form>
                <p className="text-[11px] text-gray-500">
                  {guessAttempt === 0 ? (
                    <>{t('reader.noIdea')}</>
                  ) : (
                    <button
                      type="button"
                      onClick={revealGuess}
                      className="underline hover:text-gray-600"
                    >
                      {t('reader.standByGuess')}
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
                {t('reader.unlockTranslations')}
              </button>
            )}

            {stage === 'assisted' && reading.new_words.length > 0 && (
              <div
                className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 space-y-2"
                data-testid="new-words"
              >
                <p className="text-xs uppercase tracking-wide text-gray-500">
                  {t('reader.newWordsTitle')}
                </p>
                {savedDeck && (
                  <p className="text-xs text-gray-500" data-testid="saved-deck">
                    <Trans
                      i18nKey="reader.savedDeckNote"
                      values={{ deck: savedDeck }}
                      components={{ d: <span className="font-medium text-gray-700" /> }}
                    />
                  </p>
                )}
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
                        {t('reader.added')}
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        {failedWords.has(w.word) && (
                          <span className="text-xs text-red-600" role="alert">
                            {t('reader.addFailed')}
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
                            ? t('reader.adding')
                            : failedWords.has(w.word)
                              ? t('reader.retry')
                              : t('reader.addToReviews')}
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
