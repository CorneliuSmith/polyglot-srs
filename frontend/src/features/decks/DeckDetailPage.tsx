import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getDeckItems,
  getLearnDecks,
  getVocabItem,
  resetCardProgress,
  setDeckSubscription,
} from '../../api/review'
import { getCurriculumPoint } from '../../api/curriculum'
import { getMyRoles, flagPointIssue } from '../../api/contribute'
import { deckTitle } from '../../lib/deckTitles'
import ExplanationView from '../../components/ExplanationView'
import FormsPanel from '../../components/FormsPanel'
import LanguageWrapper from '../../components/LanguageWrapper'
import SpeakButton from '../../components/SpeakButton'
import { prefetchTTSMany } from '../../api/audio'
import SuggestChange from '../contribute/SuggestChange'
import { usePrefsStore } from '../../stores/prefsStore'
import { getLanguages } from '../../api/profile'
import type { CardStatus, DeckItem } from '../../api/review'
import { useViewAsKey } from '../../stores/viewAsStore'

const STATUS_LABEL_KEY: Record<CardStatus, string> = {
  new: 'decks.statusNew',
  learning: 'decks.statusLearning',
  known: 'decks.statusKnown',
  active: 'decks.statusActive',
}
const STATUS_STYLE: Record<CardStatus, string> = {
  new: '',
  learning: 'bg-blue-50 text-blue-600',
  known: 'bg-amber-50 text-amber-700',
  active: 'bg-emerald-50 text-emerald-700',
}

/** Progress chip for the (always-visible) row header — purely informational,
 * so it can sit inside the row's own toggle button without nesting one
 * button inside another. Nothing renders for a never-learned card. */
function StatusChip({ status }: { status: CardStatus }) {
  const { t } = useTranslation()
  if (status === 'new') return null
  return (
    <span
      className={`text-[10px] uppercase tracking-wide rounded px-1.5 py-0.5 ${STATUS_STYLE[status]}`}
    >
      {t(STATUS_LABEL_KEY[status])}
    </span>
  )
}

/** Individual reset (owner: cards need to be resettable one at a time —
 * including undoing a mistaken "I already know this"). Lives in the
 * expanded panel, never in the row header (which is itself a button —
 * nesting a real button inside it would be invalid HTML). Nothing renders
 * for a never-learned card; there's no progress yet to reset. */
function ResetCardButton({ item, deckId }: { item: DeckItem; deckId: string | undefined }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const resetMutation = useMutation({
    mutationFn: () => resetCardProgress(item.user_card_id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deck-items', deckId] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['due-cards'] })
      queryClient.invalidateQueries({ queryKey: ['learn-decks'] })
    },
  })
  if (item.status === 'new' || !item.user_card_id) return null
  return (
    <button
      type="button"
      onClick={() => {
        if (window.confirm(t('decks.resetCardConfirm', { item: item.item })))
          resetMutation.mutate()
      }}
      disabled={resetMutation.isPending}
      className="text-gray-500 hover:text-red-600 disabled:opacity-50"
      title={t('decks.resetCardTitle')}
    >
      {resetMutation.isSuccess ? t('decks.resetDone') : t('dashboard.resetProgress')}
    </button>
  )
}

/** Reviewer flag box: files the issue into the point's review notes. */
function FlagBox({ pointId }: { pointId: string }) {
  const [open, setOpen] = useState(false)
  const [note, setNote] = useState('')
  const mutation = useMutation({
    mutationFn: () => flagPointIssue(pointId, note.trim()),
    onSuccess: () => {
      setOpen(false)
      setNote('')
    },
  })
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-xs text-amber-600 hover:underline"
      >
        {mutation.isSuccess ? 'Flagged ✓ — flag again' : 'Flag an issue'}
      </button>
    )
  }
  return (
    <span className="flex items-center gap-2">
      <input
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="What's wrong? (filed for review)"
        aria-label="Issue description"
        className="flex-1 rounded border border-amber-300 bg-amber-50 px-2 py-1 text-xs"
      />
      <button
        type="button"
        onClick={() => mutation.mutate()}
        disabled={note.trim().length < 3 || mutation.isPending}
        className="text-xs font-semibold text-amber-700 hover:underline disabled:opacity-50"
      >
        File it
      </button>
      <button
        type="button"
        onClick={() => setOpen(false)}
        className="text-xs text-gray-500 hover:underline"
      >
        Cancel
      </button>
    </span>
  )
}

function GrammarRow({
  item,
  languageId,
  languageCode,
  canContribute,
  deckId,
}: {
  item: DeckItem
  languageId: string | null
  languageCode: string
  canContribute: boolean
  deckId: string | undefined
}) {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const { data: detail, isLoading } = useQuery({
    queryKey: ['point-detail', item.id],
    queryFn: () => getCurriculumPoint(item.id),
    enabled: open,
  })
  return (
    <div className="border-t border-gray-100 first:border-t-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="w-full px-4 py-3 text-start flex items-center justify-between gap-3 hover:bg-gray-50"
      >
        <span>
          <LanguageWrapper languageCode={languageCode}>
            <span className="text-sm font-medium text-gray-800">{item.item}</span>
          </LanguageWrapper>
          {item.detail && (
            <span className="block text-xs text-gray-500">{item.detail}</span>
          )}
        </span>
        <span className="flex items-center gap-2 shrink-0">
          {!item.reviewed && (
            <span className="text-[10px] uppercase tracking-wide bg-amber-50 text-amber-600 rounded px-1.5 py-0.5">
              {t('decks.draft')}
            </span>
          )}
          <StatusChip status={item.status} />
          <span className="text-gray-300">{open ? '▴' : '▾'}</span>
        </span>
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-3">
          {isLoading && <p className="text-xs text-gray-500">{t('common.loading')}</p>}
          {detail?.explanation && <ExplanationView text={detail.explanation} />}
          <div className="flex items-center gap-4 text-xs">
            <button
              type="button"
              onClick={() => navigate(`/grammar?point=${item.id}`)}
              className="text-lang hover:underline"
            >
              {t('decks.openInGrammarPath')}
            </button>
            {canContribute && (
              <>
                <button
                  type="button"
                  onClick={() => navigate(`/contribute?point=${item.id}`)}
                  className="text-lang hover:underline"
                >
                  Edit in the Workshop
                </button>
                <FlagBox pointId={item.id} />
              </>
            )}
            <ResetCardButton item={item} deckId={deckId} />
          </div>
          {/* Inline votable suggestion, right on the deck (staff only). */}
          <SuggestChange
            languageId={languageId}
            targetType="grammar_point"
            targetId={item.id}
            targetLabel={item.item}
            defaultField="explanation"
          />
        </div>
      )}
    </div>
  )
}

function VocabRow({
  item,
  languageId,
  languageCode,
  deckId,
}: {
  item: DeckItem
  languageId: string | null
  languageCode: string
  deckId: string | undefined
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const { data: detail, isLoading } = useQuery({
    queryKey: ['vocab-item', item.id],
    queryFn: () => getVocabItem(item.id),
    enabled: open,
  })

  // The word first — it's the one with the speaker button next to it and the
  // one a learner expanding a deck row actually wants to hear.
  useEffect(() => {
    if (!detail) return
    return prefetchTTSMany(languageCode, [detail.word])
  }, [detail, languageCode])

  return (
    <div className="border-t border-gray-100 first:border-t-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="w-full px-4 py-3 text-start flex items-center justify-between gap-3 hover:bg-gray-50"
      >
        <span>
          <LanguageWrapper languageCode={languageCode}>
            <span className="text-sm font-medium text-gray-800">{item.item}</span>
          </LanguageWrapper>
          {item.detail && (
            <span className="block text-xs text-gray-500">{item.detail}</span>
          )}
        </span>
        <span className="flex items-center gap-2 shrink-0">
          <StatusChip status={item.status} />
          <span className="text-gray-300">{open ? '▴' : '▾'}</span>
        </span>
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-3">
          {isLoading && <p className="text-xs text-gray-500">{t('common.loading')}</p>}
          {detail && (
            <>
              <p className="text-sm text-gray-700">
                <span className="font-semibold">{detail.word}</span>
                {detail.part_of_speech ? ` (${detail.part_of_speech})` : ''}
                {detail.definition ? ` — ${detail.definition}` : ''}
                <SpeakButton text={detail.word} languageCode={languageCode} />
              </p>
              <FormsPanel morphology={detail.morphology} languageCode={languageCode} />
              {detail.examples.length > 0 && (
                <ul className="space-y-1">
                  {detail.examples.slice(0, 3).map((ex, i) => (
                    <li key={i} className="text-sm">
                      <LanguageWrapper languageCode={languageCode}>
                        <span className="text-gray-800">{ex.sentence}</span>
                      </LanguageWrapper>
                      {ex.translation && (
                        <span className="block text-xs text-gray-500">
                          {ex.translation}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
          <div className="text-xs">
            <ResetCardButton item={item} deckId={deckId} />
          </div>
          {/* Inline votable suggestion, right on the deck (staff only). */}
          <SuggestChange
            languageId={languageId}
            targetType="vocabulary"
            targetId={item.id}
            targetLabel={item.item}
            defaultField="translation"
          />
        </div>
      )}
    </div>
  )
}

/**
 * One deck, fully browsable (Bunpro's deck page): every item in path
 * order, searchable, each row expanding into its real content — grammar
 * points show their explanation with links into the grammar path and (for
 * role-holders) Contribute + issue flagging; words show definition, Forms
 * panel, and sample sentences.
 */
export default function DeckDetailPage() {
  const { deckId } = useParams<{ deckId: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  const { data: languages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
    staleTime: Infinity,
  })
  const languageCode =
    languages.find((l) => l.id === activeLanguageId)?.code ?? 'en'

  const { data: listing, isLoading } = useQuery({
    queryKey: ['deck-items', deckId],
    queryFn: () => getDeckItems(deckId!),
    enabled: !!deckId,
  })

  const { data: roleInfo } = useQuery({
    queryKey: ['my-roles', useViewAsKey()],
    queryFn: getMyRoles,
    retry: false,
  })
  const canContribute = (roleInfo?.roles?.length ?? 0) > 0

  // The queue button must reflect reality: a deck already in the learn
  // queue shows as such (and offers removal), not a phantom "Add".
  const { data: decks = [] } = useQuery({
    queryKey: ['learn-decks', activeLanguageId],
    queryFn: () => getLearnDecks(activeLanguageId!),
    enabled: !!activeLanguageId,
  })
  const subscribed = decks.find((d) => d.id === deckId)?.subscribed ?? false

  const subMutation = useMutation({
    mutationFn: (next: boolean) => setDeckSubscription(deckId!, next),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['learn-decks'] }),
  })

  const filtered = useMemo(() => {
    const items = listing?.items ?? []
    const q = search.trim().toLowerCase()
    if (!q) return items
    return items.filter(
      (it) =>
        it.item.toLowerCase().includes(q) ||
        (it.detail ?? '').toLowerCase().includes(q),
    )
  }, [listing, search])

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">
            {listing ? deckTitle(listing, t) : t('decks.deckFallback')}
          </h1>
          <button
            type="button"
            onClick={() => navigate('/decks')}
            className="text-sm text-lang hover:underline"
          >
            {t('decks.allDecks')}
          </button>
        </div>
        {listing && (
          <p className="text-sm text-gray-500">
            {listing.level ?? t('decks.allLevels')} ·{' '}
            {listing.list_type === 'grammar' ? t('common.grammar') : t('decks.vocabulary')} ·{' '}
            {t('decks.itemCount', { count: listing.items.length })}
          </p>
        )}

        <div className="flex items-center gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('decks.searchThisDeck')}
            aria-label={t('decks.searchThisDeck')}
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lang bg-white"
          />
          {subscribed ? (
            <button
              type="button"
              onClick={() => subMutation.mutate(false)}
              disabled={subMutation.isPending}
              title={t('decks.inQueueTitle')}
              className="rounded-lg border border-lang/40 bg-lang-soft text-lang px-4 py-2 text-sm font-semibold disabled:opacity-50 hover:border-red-300 hover:bg-red-50 hover:text-red-700"
            >
              {t('decks.inQueueButton')}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => subMutation.mutate(true)}
              disabled={subMutation.isPending}
              className="rounded-lg bg-lang hover:bg-lang-dark text-lang-on px-4 py-2 text-sm font-semibold disabled:opacity-50"
            >
              {t('dashboard.addToQueue')}
            </button>
          )}
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          {isLoading && (
            <p className="px-4 py-3 text-sm text-gray-500">{t('decks.loadingItems')}</p>
          )}
          {filtered.map((item) =>
            item.kind === 'grammar' ? (
              <GrammarRow
                key={item.id}
                item={item}
                languageId={activeLanguageId}
                languageCode={languageCode}
                canContribute={canContribute}
                deckId={deckId}
              />
            ) : (
              <VocabRow
                key={item.id}
                item={item}
                languageId={activeLanguageId}
                languageCode={languageCode}
                deckId={deckId}
              />
            ),
          )}
          {!isLoading && filtered.length === 0 && (
            <p className="px-4 py-3 text-sm text-gray-500">{t('decks.noItemsMatch')}</p>
          )}
        </div>
      </div>
    </div>
  )
}
