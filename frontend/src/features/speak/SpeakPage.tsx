import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Check, Loader2, Send } from 'lucide-react'
import {
  endSpeakSession,
  getSpeakStatus,
  sendSpeakTurn,
  startSpeakSession,
} from '../../api/speak'
import type { SpeakSummary } from '../../api/speak'
import type { TutorAllowance } from '../../api/tutor'
import { createPersonalCard } from '../../api/notes'
import { getLanguages } from '../../api/profile'
import { usePrefsStore } from '../../stores/prefsStore'
import LanguageWrapper from '../../components/LanguageWrapper'
import SectionHeader from '../../components/SectionHeader'
import UsageMeter from '../../components/UsageMeter'

interface Exchange {
  learner: string
  partner: string
}

/**
 * Speak (docs/plans/speak.md) — conversation practice.
 *
 * Stage 1: typed Flow mode. They talk, the partner answers, and nothing
 * interrupts. Every mistake is noticed server-side and held back until they
 * press Done, at which point the whole session is grouped into a handful of
 * things worth understanding.
 *
 * The deliberate absence here is a score. Counting turns and minutes is
 * fine; grading the conversation would turn a place to experiment into a
 * thing to game, and the learner would stop taking risks — which is the
 * only reason to practise speaking at all.
 */
export default function SpeakPage() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  const { data: languages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
  })
  const language = languages.find((l) => l.id === activeLanguageId)

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['speak-status', activeLanguageId],
    queryFn: () => getSpeakStatus(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
  })

  const [topic, setTopic] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [exchanges, setExchanges] = useState<Exchange[]>([])
  const [draft, setDraft] = useState('')
  const [allowance, setAllowance] = useState<TutorAllowance | null>(null)
  const [summary, setSummary] = useState<SpeakSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (status?.allowance) setAllowance(status.allowance)
  }, [status?.allowance])

  useEffect(() => {
    // Optional-called: scrollIntoView is absent in jsdom and on some older
    // mobile browsers, and failing to scroll must never take the page down
    // mid-conversation.
    endRef.current?.scrollIntoView?.({ behavior: 'smooth' })
  }, [exchanges.length])

  const start = useMutation({
    mutationFn: () =>
      startSpeakSession(activeLanguageId!, language!.code, topic.trim()),
    onSuccess: (data) => {
      setSessionId(data.session_id)
      setExchanges([])
      setSummary(null)
      setError(null)
    },
    onError: () => setError(t('speak.startFailed')),
  })

  const turn = useMutation({
    mutationFn: (text: string) => sendSpeakTurn(sessionId!, text),
    onSuccess: (data, text) => {
      setExchanges((prev) => [...prev, { learner: text, partner: data.reply }])
      setAllowance(data.allowance)
      setError(null)
    },
    // The draft is put back on failure — losing what someone just typed
    // because the network hiccuped is the fastest way to end a session.
    onError: (_err, text) => {
      setDraft(text)
      setError(t('speak.turnFailed'))
    },
  })

  const finish = useMutation({
    mutationFn: () => endSpeakSession(sessionId!),
    onSuccess: (data) => {
      setSummary(data.summary)
      setSessionId(null)
    },
    onError: () => setError(t('speak.endFailed')),
  })

  function submit() {
    const text = draft.trim()
    if (!text || turn.isPending) return
    setDraft('')
    turn.mutate(text)
  }

  if (!activeLanguageId || statusLoading) {
    return (
      <Shell title={t('nav.speak')}>
        <p className="text-sm text-gray-500">{t('speak.loading')}</p>
      </Shell>
    )
  }

  // Unavailable covers both "no AI configured here" and "the migration
  // hasn't landed yet" — from the learner's side those are the same fact.
  if (!status?.available) {
    return (
      <Shell title={t('nav.speak')}>
        <p className="text-sm text-gray-600">{t('speak.unavailable')}</p>
        <button
          type="button"
          onClick={() => navigate('/practice')}
          className="mt-4 text-sm font-semibold text-lang"
        >
          {t('speak.backToPractice')}
        </button>
      </Shell>
    )
  }

  if (summary) {
    return (
      <Shell title={t('nav.speak')}>
        <SummaryView
          summary={summary}
          languageCode={language?.code ?? 'en'}
          languageId={activeLanguageId}
          onAgain={() => {
            setSummary(null)
            setExchanges([])
          }}
        />
      </Shell>
    )
  }

  if (!sessionId) {
    return (
      <Shell title={t('nav.speak')} allowance={allowance}>
        <p className="text-sm text-gray-600">{t('speak.intro')}</p>
        <label
          htmlFor="speak-topic"
          className="block mt-4 text-sm font-semibold text-gray-800"
        >
          {t('speak.topicLabel')}
        </label>
        <input
          id="speak-topic"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          maxLength={120}
          placeholder={t('speak.topicPlaceholder')}
          className="mt-1 w-full rounded-xl border border-gray-300 px-4 py-3 text-sm"
        />
        <p className="mt-1 text-xs text-gray-500">{t('speak.topicHint')}</p>
        <button
          type="button"
          data-testid="speak-start"
          onClick={() => start.mutate()}
          disabled={start.isPending || !language}
          className="mt-4 w-full rounded-xl bg-lang px-6 py-3 text-sm font-bold text-white disabled:opacity-50"
          style={{ minHeight: '44px' }}
        >
          {start.isPending ? t('speak.starting') : t('speak.startButton')}
        </button>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </Shell>
    )
  }

  return (
    <Shell title={t('nav.speak')} allowance={allowance}>
      <div className="space-y-3" data-testid="speak-transcript">
        {exchanges.length === 0 && !turn.isPending && (
          <p className="text-sm text-gray-500">{t('speak.yourMove')}</p>
        )}
        {exchanges.map((x, i) => (
          <div key={i} className="space-y-2">
            <p className="ms-auto max-w-[85%] rounded-2xl bg-lang-soft/60 px-4 py-2 text-sm text-gray-900 w-fit">
              {x.learner}
            </p>
            <LanguageWrapper languageCode={language?.code ?? 'en'}>
              <p className="max-w-[85%] rounded-2xl bg-white border border-gray-200 px-4 py-2 text-sm text-gray-900 w-fit">
                {x.partner}
              </p>
            </LanguageWrapper>
          </div>
        ))}
        {turn.isPending && (
          <p className="flex items-center gap-2 text-sm text-gray-500">
            <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
            {t('speak.thinking')}
          </p>
        )}
        <div ref={endRef} />
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      <div className="mt-4 flex items-end gap-2">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          rows={2}
          maxLength={2000}
          aria-label={t('speak.inputLabel')}
          placeholder={t('speak.inputPlaceholder')}
          data-testid="speak-input"
          className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 text-sm"
        />
        <button
          type="button"
          onClick={submit}
          disabled={!draft.trim() || turn.isPending}
          aria-label={t('speak.send')}
          data-testid="speak-send"
          className="rounded-xl bg-lang p-3 text-white disabled:opacity-50"
          style={{ minHeight: '44px', minWidth: '44px' }}
        >
          <Send aria-hidden className="h-5 w-5" />
        </button>
      </div>

      <button
        type="button"
        onClick={() => finish.mutate()}
        disabled={finish.isPending}
        data-testid="speak-done"
        className="mt-4 w-full rounded-xl border border-gray-300 bg-white px-6 py-3 text-sm font-semibold text-gray-800 disabled:opacity-50"
        style={{ minHeight: '44px' }}
      >
        {finish.isPending ? t('speak.ending') : t('speak.done')}
      </button>
    </Shell>
  )
}

function Shell({
  title,
  allowance,
  children,
}: {
  title: string
  allowance?: TutorAllowance | null
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-4 pb-24 md:pb-6">
        <SectionHeader title={title} />
        {allowance && <UsageMeter allowance={allowance} />}
        {children}
      </div>
    </div>
  )
}

function SummaryView({
  summary,
  languageCode,
  languageId,
  onAgain,
}: {
  summary: SpeakSummary
  languageCode: string
  languageId: string | null
  onAgain: () => void
}) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  // Nothing is added on its own. These track what the learner chose, so a
  // second tap can't duplicate a card and the button can say it worked.
  const [added, setAdded] = useState<Record<string, boolean>>({})
  const [failed, setFailed] = useState<Record<string, boolean>>({})

  const add = useMutation({
    mutationFn: async ({
      key, sentence, answer, translation, gloss,
    }: {
      key: string
      sentence: string
      answer: string
      translation?: string
      gloss?: string
    }) => {
      await createPersonalCard({
        languageId: languageId!,
        languageCode,
        sentence,
        answer,
        translation,
        gloss,
        source: 'speak',
      })
      return key
    },
    onSuccess: (key) => {
      setAdded((prev) => ({ ...prev, [key]: true }))
      setFailed((prev) => ({ ...prev, [key]: false }))
    },
    onError: (_e, vars) => setFailed((prev) => ({ ...prev, [vars.key]: true })),
  })

  const anyAdded = Object.values(added).some(Boolean)

  return (
    <div data-testid="speak-summary">
      <p className="text-sm text-gray-600">
        {t('speak.summaryStats', { count: summary.stats?.turns ?? 0 })}
      </p>

      {summary.groups.length === 0 ? (
        <p className="mt-4 rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-700">
          {t('speak.nothingCameUp')}
        </p>
      ) : (
        <>
          <h2 className="mt-5 text-sm font-bold text-gray-900">
            {t('speak.whatCameUp')}
          </h2>
          <ul className="mt-2 space-y-2">
            {summary.groups.map((g, i) => (
              <li
                key={i}
                className="rounded-xl border border-gray-200 bg-white p-4"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-sm font-bold text-gray-900">
                    {g.label}
                  </span>
                  <span className="text-xs text-gray-500">
                    {t('speak.timesCount', { count: g.count })}
                  </span>
                </div>
                <p className="mt-1 text-sm text-gray-700">{g.note}</p>
                {g.examples.length > 0 && (
                  <LanguageWrapper languageCode={languageCode}>
                    <ul className="mt-2 space-y-0.5">
                      {g.examples.map((ex, j) => (
                        <li key={j} className="text-sm text-gray-600">
                          {ex}
                        </li>
                      ))}
                    </ul>
                  </LanguageWrapper>
                )}
                {/* Absent when the session produced nothing a card could be
                    built from — better than a button that fails on tap. */}
                {g.card && (
                  <AddButton
                    testId={`speak-add-group-${i}`}
                    added={!!added[`g${i}`]}
                    failed={!!failed[`g${i}`]}
                    disabled={add.isPending || !languageId}
                    onClick={() =>
                      add.mutate({
                        key: `g${i}`,
                        sentence: g.card!.sentence,
                        answer: g.card!.answer,
                        translation: g.card!.translation,
                      })
                    }
                  />
                )}
              </li>
            ))}
          </ul>
        </>
      )}

      {summary.vocabulary.length > 0 && (
        <>
          <h2 className="mt-5 text-sm font-bold text-gray-900">
            {t('speak.wordsYouReachedFor')}
          </h2>
          <ul className="mt-2 rounded-xl border border-gray-200 bg-white p-4 space-y-2">
            {summary.vocabulary.map((v, i) => (
              <li
                key={i}
                className="flex items-baseline justify-between gap-3 text-sm text-gray-700"
              >
                <span>
                  <LanguageWrapper languageCode={languageCode}>
                    <span className="font-semibold">{v.term}</span>
                  </LanguageWrapper>
                  <span className="text-gray-500"> — {v.meaning}</span>
                </span>
                <AddButton
                  testId={`speak-add-word-${i}`}
                  added={!!added[`v${i}`]}
                  failed={!!failed[`v${i}`]}
                  disabled={add.isPending || !languageId}
                  onClick={() =>
                    add.mutate({
                      key: `v${i}`,
                      // Prefer the sentence they met it in; the server falls
                      // back to a type-the-word card from the gloss when the
                      // term isn't a whole word there.
                      sentence: v.example || v.term,
                      answer: v.term,
                      gloss: v.meaning,
                    })
                  }
                />
              </li>
            ))}
          </ul>
        </>
      )}

      {anyAdded && (
        <button
          type="button"
          onClick={() => navigate('/review')}
          data-testid="speak-practise"
          className="mt-5 w-full rounded-xl bg-lang px-6 py-3 text-sm font-bold text-white"
          style={{ minHeight: '44px' }}
        >
          {t('speak.practiseThese')}
        </button>
      )}

      <button
        type="button"
        onClick={onAgain}
        data-testid="speak-again"
        className={`mt-3 w-full rounded-xl px-6 py-3 text-sm font-bold ${
          anyAdded
            ? 'border border-gray-300 bg-white text-gray-800'
            : 'bg-lang text-white'
        }`}
        style={{ minHeight: '44px' }}
      >
        {t('speak.talkAgain')}
      </button>
    </div>
  )
}

/** Opt-in, one tap, and honest about what happened. Nothing is ever added
 * without the learner asking — a summary that quietly filled their reviews
 * would make them wary of finishing a session at all. */
function AddButton({
  testId,
  added,
  failed,
  disabled,
  onClick,
}: {
  testId: string
  added: boolean
  failed: boolean
  disabled: boolean
  onClick: () => void
}) {
  const { t } = useTranslation()
  if (added) {
    return (
      <span
        data-testid={testId}
        className="shrink-0 inline-flex items-center gap-1 text-xs font-semibold text-green-700"
      >
        <Check aria-hidden className="h-3.5 w-3.5" />
        {t('speak.added')}
      </span>
    )
  }
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className="shrink-0 rounded-lg border border-lang/40 px-3 py-1.5 text-xs font-semibold text-lang disabled:opacity-50"
      style={{ minHeight: '32px' }}
    >
      {failed ? t('speak.addRetry') : t('speak.add')}
    </button>
  )
}
