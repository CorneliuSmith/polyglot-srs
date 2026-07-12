import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getDeckItems,
  getVocabItem,
  setDeckSubscription,
} from '../../api/review'
import { getCurriculumPoint } from '../../api/curriculum'
import { getMyRoles, flagPointIssue } from '../../api/contribute'
import ExplanationView from '../../components/ExplanationView'
import FormsPanel from '../../components/FormsPanel'
import LanguageWrapper from '../../components/LanguageWrapper'
import SpeakButton from '../../components/SpeakButton'
import { usePrefsStore } from '../../stores/prefsStore'
import { getLanguages } from '../../api/profile'
import type { DeckItem } from '../../api/review'

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
        className="text-xs text-gray-400 hover:underline"
      >
        Cancel
      </button>
    </span>
  )
}

function GrammarRow({
  item,
  languageCode,
  canContribute,
}: {
  item: DeckItem
  languageCode: string
  canContribute: boolean
}) {
  const navigate = useNavigate()
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
        className="w-full px-4 py-3 text-left flex items-center justify-between gap-3 hover:bg-gray-50"
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
              Draft
            </span>
          )}
          <span className="text-gray-300">{open ? '▴' : '▾'}</span>
        </span>
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-3">
          {isLoading && <p className="text-xs text-gray-400">Loading…</p>}
          {detail?.explanation && <ExplanationView text={detail.explanation} />}
          <div className="flex items-center gap-4 text-xs">
            <button
              type="button"
              onClick={() => navigate(`/grammar?point=${item.id}`)}
              className="text-lang hover:underline"
            >
              Open in grammar path
            </button>
            {canContribute && (
              <>
                <button
                  type="button"
                  onClick={() => navigate(`/contribute?point=${item.id}`)}
                  className="text-lang hover:underline"
                >
                  Edit in Contribute
                </button>
                <FlagBox pointId={item.id} />
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function VocabRow({
  item,
  languageCode,
}: {
  item: DeckItem
  languageCode: string
}) {
  const [open, setOpen] = useState(false)
  const { data: detail, isLoading } = useQuery({
    queryKey: ['vocab-item', item.id],
    queryFn: () => getVocabItem(item.id),
    enabled: open,
  })
  return (
    <div className="border-t border-gray-100 first:border-t-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="w-full px-4 py-3 text-left flex items-center justify-between gap-3 hover:bg-gray-50"
      >
        <span>
          <LanguageWrapper languageCode={languageCode}>
            <span className="text-sm font-medium text-gray-800">{item.item}</span>
          </LanguageWrapper>
          {item.detail && (
            <span className="block text-xs text-gray-500">{item.detail}</span>
          )}
        </span>
        <span className="text-gray-300 shrink-0">{open ? '▴' : '▾'}</span>
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-3">
          {isLoading && <p className="text-xs text-gray-400">Loading…</p>}
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
    queryKey: ['my-roles'],
    queryFn: getMyRoles,
    retry: false,
  })
  const canContribute = (roleInfo?.roles?.length ?? 0) > 0

  const subMutation = useMutation({
    mutationFn: (subscribed: boolean) => setDeckSubscription(deckId!, subscribed),
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
            {listing?.title ?? 'Deck'}
          </h1>
          <button
            type="button"
            onClick={() => navigate('/decks')}
            className="text-sm text-lang hover:underline"
          >
            ← All decks
          </button>
        </div>
        {listing && (
          <p className="text-sm text-gray-500">
            {listing.level ?? 'All levels'} ·{' '}
            {listing.list_type === 'grammar' ? 'Grammar' : 'Vocabulary'} ·{' '}
            {listing.items.length} items
          </p>
        )}

        <div className="flex items-center gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search this deck"
            aria-label="Search this deck"
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lang bg-white"
          />
          <button
            type="button"
            onClick={() => subMutation.mutate(true)}
            disabled={subMutation.isPending}
            className="rounded-lg bg-lang hover:bg-lang-dark text-lang-on px-4 py-2 text-sm font-semibold disabled:opacity-50"
          >
            Add to queue
          </button>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          {isLoading && (
            <p className="px-4 py-3 text-sm text-gray-400">Loading items…</p>
          )}
          {filtered.map((item) =>
            item.kind === 'grammar' ? (
              <GrammarRow
                key={item.id}
                item={item}
                languageCode={languageCode}
                canContribute={canContribute}
              />
            ) : (
              <VocabRow key={item.id} item={item} languageCode={languageCode} />
            ),
          )}
          {!isLoading && filtered.length === 0 && (
            <p className="px-4 py-3 text-sm text-gray-500">No items match.</p>
          )}
        </div>
      </div>
    </div>
  )
}
