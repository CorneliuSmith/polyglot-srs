import { useState } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createPersonalDeck,
  deletePersonalDeck,
  filePersonalCard,
  getPersonalCards,
  getPersonalDecks,
  renamePersonalDeck,
  getPersonalTranslationStatus,
  translatePersonalCards,
} from '../../api/personalDecks'

/**
 * Personal decks (owner request): learner-named folders over the cards
 * minted from the Tutor and the Reader. Organization only — creating
 * cards by hand stays off for now. Deleting a deck never deletes cards;
 * they fall back to "Unfiled".
 */
export default function PersonalDecksSection({ languageId }: { languageId: string }) {
  const { t } = useTranslation()
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

  // Personal cards are private, so the background loop never touches them
  // (it would spend the operator's key on text only one person sees). They
  // are translated on request from the learner's own allowance — so the
  // offer states the count and the cost before anything is spent.
  const { data: tstatus } = useQuery({
    queryKey: ['personal-translation-status', languageId],
    queryFn: () => getPersonalTranslationStatus(languageId),
    retry: false,
  })
  const translateMutation = useMutation({
    mutationFn: () => translatePersonalCards(languageId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['personal-translation-status', languageId],
      })
      queryClient.invalidateQueries({ queryKey: ['personal-cards', languageId] })
      queryClient.invalidateQueries({ queryKey: ['due-cards'] })
    },
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

  // Empty used to render NOTHING — no heading, no explanation. Someone
  // looking for their saved words found a Decks page with no sign the
  // feature existed, which reads as "it's broken" rather than "you haven't
  // saved anything yet". Say where these come from instead.
  if (cards.length === 0 && decks.length === 0) {
    return (
      <section
        data-testid="personal-decks-empty"
        className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-1"
      >
        <h2 className="font-semibold text-gray-800">{t('decks.savedWordsTitle')}</h2>
        <p className="text-sm text-gray-600">
          {t('decks.savedWordsExplain')}
        </p>
        <p className="text-xs text-gray-500">
          <Trans
            i18nKey="decks.savedWordsHint"
            components={{ read: <span className="font-medium" /> }}
          />
        </p>
      </section>
    )
  }

  const unfiled = cards.filter((c) => !c.deck_id)
  const groups: { id: string | null; name: string; cards: typeof cards }[] = [
    ...decks.map((d) => ({
      id: d.id as string | null,
      name: d.name,
      cards: cards.filter((c) => c.deck_id === d.id),
    })),
    { id: null, name: t('decks.unfiled'), cards: unfiled },
  ]

  const handleRename = (id: string, current: string) => {
    const name = window.prompt(t('decks.renamePrompt'), current)?.trim()
    if (name && name !== current) renameMutation.mutate({ id, name })
  }

  const handleDelete = (id: string, name: string) => {
    if (window.confirm(t('decks.deleteDeckConfirm', { name }))) {
      deleteMutation.mutate(id)
    }
  }

  return (
    <section className="space-y-3" data-testid="personal-decks">
      <h2 className="font-semibold text-gray-800">
        {t('decks.personalDecks')}
        <span className="ms-2 text-xs font-normal text-gray-400">
          {t('decks.personalDecksSub')}
        </span>
      </h2>

      {tstatus && tstatus.available && tstatus.pending > 0 && (
        <div
          data-testid="personal-translate-offer"
          className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 space-y-2"
        >
          <p className="text-sm text-gray-700">
            {t('decks.translateOffer', { count: tstatus.pending })}
          </p>
          <p className="text-xs text-gray-500">{t('decks.translateCost')}</p>
          <button
            type="button"
            onClick={() => translateMutation.mutate()}
            disabled={translateMutation.isPending}
            className="rounded-xl bg-lang hover:bg-lang-dark disabled:opacity-40 text-lang-on text-sm font-semibold px-4 py-2"
          >
            {translateMutation.isPending
              ? t('decks.translating')
              : t('decks.translateAction')}
          </button>
          {translateMutation.isError && (
            <p className="text-xs text-red-600">{t('decks.translateFailed')}</p>
          )}
        </div>
      )}
      {translateMutation.isSuccess && translateMutation.data.translated > 0 && (
        <p className="text-xs text-green-700" data-testid="personal-translate-done">
          {t('decks.translateDone', { count: translateMutation.data.translated })}
        </p>
      )}

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
          placeholder={t('decks.newDeckPlaceholder')}
          maxLength={60}
          className="flex-1 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-lang/50"
        />
        <button
          type="submit"
          disabled={!newName.trim() || createMutation.isPending}
          className="rounded-xl bg-lang hover:bg-lang-dark disabled:opacity-40 text-lang-on text-sm font-semibold px-4 py-2"
        >
          {t('decks.create')}
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
                  className="flex-1 text-start text-sm font-semibold text-gray-800"
                >
                  {g.name}
                  <span className="ms-2 text-xs font-normal text-gray-400">
                    {t('decks.cardCount', { count: g.cards.length })}
                  </span>
                </button>
                {g.id !== null && (
                  <>
                    <button
                      type="button"
                      onClick={() => handleRename(g.id!, g.name)}
                      className="text-xs text-gray-400 hover:text-lang"
                    >
                      {t('decks.rename')}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(g.id!, g.name)}
                      className="text-xs text-gray-400 hover:text-red-600"
                    >
                      {t('decks.delete')}
                    </button>
                  </>
                )}
              </div>
              {open && (
                <ul className="border-t border-gray-100 px-4 py-2 divide-y divide-gray-50">
                  {g.cards.length === 0 && (
                    <li className="py-2 text-xs text-gray-400">
                      {t('decks.emptyDeckHint')}
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
                        aria-label={t('decks.deckFor', { answer: c.answer })}
                        className="text-xs rounded-lg border border-gray-200 bg-white px-2 py-1 text-gray-600"
                      >
                        <option value="">{t('decks.unfiled')}</option>
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
