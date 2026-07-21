import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getLearnDecks } from '../../api/review'
import { usePrefsStore } from '../../stores/prefsStore'
import LanguagePicker from '../../components/LanguagePicker'
import PersonalDecksSection from './PersonalDecksSection'
import type { LearnDeck } from '../../api/types'

/**
 * The deck library (Bunpro's Decks page): every deck for the active
 * language as a browsable card — progress, queue state, and a click
 * through to the full item listing.
 */
export default function DecksPage() {
  const navigate = useNavigate()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  const { data: decks = [], isLoading } = useQuery({
    queryKey: ['learn-decks', activeLanguageId],
    queryFn: () => getLearnDecks(activeLanguageId!),
    enabled: !!activeLanguageId,
  })

  const visible = decks.filter((d) => d.total > 0)
  const grammar = visible.filter((d) => d.list_type === 'grammar')
  const vocab = visible.filter((d) => d.list_type === 'vocabulary')

  const DeckCard = ({ deck }: { deck: LearnDeck }) => {
    const pct = deck.total > 0 ? Math.round((deck.learned / deck.total) * 100) : 0
    return (
      <button
        type="button"
        onClick={() => navigate(`/decks/${deck.id}`)}
        className="text-left bg-white rounded-2xl shadow-sm border border-gray-100 p-4 hover:border-lang/40 transition-colors"
      >
        <div className="flex items-center justify-between">
          <span className="inline-block rounded bg-lang text-lang-on text-xs font-bold px-2 py-1">
            {deck.level ?? 'All'} ·{' '}
            {deck.list_type === 'grammar' ? 'Grammar' : 'Vocab'}
          </span>
          {deck.subscribed && (
            <span className="text-[10px] uppercase tracking-wide bg-lang-soft text-lang rounded px-1.5 py-0.5">
              In queue
            </span>
          )}
        </div>
        <p className="mt-3 text-sm font-semibold text-gray-800">{deck.title}</p>
        <p className="text-xs text-gray-500 mt-0.5">
          {deck.learned} / {deck.total} learned
        </p>
        <div className="mt-2 w-full bg-gray-100 rounded-full h-1.5">
          <div
            className="h-1.5 rounded-full bg-lang"
            style={{ width: `${pct}%` }}
          />
        </div>
      </button>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Decks</h1>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-sm text-lang hover:underline"
          >
            ← Dashboard
          </button>
        </div>

        <LanguagePicker />

        {isLoading && <p className="text-sm text-gray-400">Loading decks…</p>}

        {grammar.length > 0 && (
          <section className="space-y-3">
            <h2 className="font-semibold text-gray-800">Grammar decks</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {grammar.map((d) => (
                <DeckCard key={d.id} deck={d} />
              ))}
            </div>
          </section>
        )}

        {vocab.length > 0 && (
          <section className="space-y-3">
            <h2 className="font-semibold text-gray-800">Vocabulary decks</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {vocab.map((d) => (
                <DeckCard key={d.id} deck={d} />
              ))}
            </div>
          </section>
        )}

        {!isLoading && visible.length === 0 && (
          <p className="text-sm text-gray-500">No decks for this language yet.</p>
        )}

        {activeLanguageId && <PersonalDecksSection languageId={activeLanguageId} />}
      </div>
    </div>
  )
}
