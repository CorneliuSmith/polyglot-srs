import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createPersonalDeck,
  deletePersonalDeck,
  filePersonalCard,
  getPersonalCards,
  getPersonalDecks,
  renamePersonalDeck,
} from '../../api/personalDecks'

/**
 * Personal decks (owner request): learner-named folders over the cards
 * minted from the Tutor and the Reader. Organization only — creating
 * cards by hand stays off for now. Deleting a deck never deletes cards;
 * they fall back to "Unfiled".
 */
export default function PersonalDecksSection({ languageId }: { languageId: string }) {
  const queryClient = useQueryClient()
  const [newName, setNewName] = useState('')
  const [openDeckId, setOpenDeckId] = useState<string | null>(null)

  const { data: decks = [] } = useQuery({
    queryKey: ['personal-decks', languageId],
    queryFn: () => getPersonalDecks(languageId),
  })
  const { data: cards = [] } = useQuery({
    queryKey: ['personal-cards', languageId],
    queryFn: () => getPersonalCards(languageId),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['personal-decks', languageId] })
    queryClient.invalidateQueries({ queryKey: ['personal-cards', languageId] })
  }

  const createMutation = useMutation({
    mutationFn: (name: string) => createPersonalDeck(languageId, name),
    onSuccess: () => {
      setNewName('')
      invalidate()
    },
  })
  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      renamePersonalDeck(id, name),
    onSuccess: invalidate,
  })
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deletePersonalDeck(id),
    onSuccess: invalidate,
  })
  const fileMutation = useMutation({
    mutationFn: ({ cardId, deckId }: { cardId: string; deckId: string | null }) =>
      filePersonalCard(cardId, deckId),
    onSuccess: invalidate,
  })

  // Personal decks only matter once the learner HAS personal cards.
  if (cards.length === 0 && decks.length === 0) return null

  const unfiled = cards.filter((c) => !c.deck_id)
  const groups: { id: string | null; name: string; cards: typeof cards }[] = [
    ...decks.map((d) => ({
      id: d.id as string | null,
      name: d.name,
      cards: cards.filter((c) => c.deck_id === d.id),
    })),
    { id: null, name: 'Unfiled', cards: unfiled },
  ]

  const handleRename = (id: string, current: string) => {
    const name = window.prompt('Rename deck', current)?.trim()
    if (name && name !== current) renameMutation.mutate({ id, name })
  }

  const handleDelete = (id: string, name: string) => {
    if (
      window.confirm(
        `Delete "${name}"? Its cards are kept — they just move back to Unfiled.`,
      )
    ) {
      deleteMutation.mutate(id)
    }
  }

  return (
    <section className="space-y-3" data-testid="personal-decks">
      <h2 className="font-semibold text-gray-800">
        Personal decks
        <span className="ml-2 text-xs font-normal text-gray-400">
          your words from the Tutor and the Reader
        </span>
      </h2>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          const name = newName.trim()
          if (name) createMutation.mutate(name)
        }}
        className="flex items-center gap-2"
      >
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New deck name…"
          maxLength={60}
          className="flex-1 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-lang/50"
        />
        <button
          type="submit"
          disabled={!newName.trim() || createMutation.isPending}
          className="rounded-xl bg-lang hover:bg-lang-dark disabled:opacity-40 text-lang-on text-sm font-semibold px-4 py-2"
        >
          Create
        </button>
      </form>

      <div className="space-y-2">
        {groups.map((g) => {
          if (g.id === null && g.cards.length === 0) return null
          const open = openDeckId === (g.id ?? 'unfiled')
          return (
            <div
              key={g.id ?? 'unfiled'}
              className="bg-white rounded-2xl border border-gray-100 shadow-sm"
            >
              <div className="flex items-center gap-2 px-4 py-3">
                <button
                  type="button"
                  onClick={() => setOpenDeckId(open ? null : (g.id ?? 'unfiled'))}
                  aria-expanded={open}
                  className="flex-1 text-left text-sm font-semibold text-gray-800"
                >
                  {g.name}
                  <span className="ml-2 text-xs font-normal text-gray-400">
                    {g.cards.length} {g.cards.length === 1 ? 'card' : 'cards'}
                  </span>
                </button>
                {g.id !== null && (
                  <>
                    <button
                      type="button"
                      onClick={() => handleRename(g.id!, g.name)}
                      className="text-xs text-gray-400 hover:text-lang"
                    >
                      Rename
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(g.id!, g.name)}
                      className="text-xs text-gray-400 hover:text-red-600"
                    >
                      Delete
                    </button>
                  </>
                )}
              </div>
              {open && (
                <ul className="border-t border-gray-100 px-4 py-2 divide-y divide-gray-50">
                  {g.cards.length === 0 && (
                    <li className="py-2 text-xs text-gray-400">
                      Empty — file cards here from Unfiled.
                    </li>
                  )}
                  {g.cards.map((c) => (
                    <li key={c.id} className="py-2 flex items-center gap-3">
                      <span className="flex-1 min-w-0">
                        <span className="block text-sm font-medium text-gray-800">
                          {c.answer}
                        </span>
                        <span className="block text-xs text-gray-400 truncate">
                          {(c.sentence ?? '').replace('{{answer}}', '___')}
                        </span>
                      </span>
                      <select
                        value={c.deck_id ?? ''}
                        onChange={(e) =>
                          fileMutation.mutate({
                            cardId: c.id,
                            deckId: e.target.value || null,
                          })
                        }
                        aria-label={`Deck for ${c.answer}`}
                        className="text-xs rounded-lg border border-gray-200 bg-white px-2 py-1 text-gray-600"
                      >
                        <option value="">Unfiled</option>
                        {decks.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name}
                          </option>
                        ))}
                      </select>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
