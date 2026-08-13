import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getPersonalTranslationStatus,
  translatePersonalCards,
} from '../../api/personalDecks'

/**
 * "Not translated, just noted" — the owner's verdict on labelling alone.
 *
 * A personal card is the learner's own private sentence, so the background
 * auto-translate loop deliberately never sweeps it: filling it spends THEIR
 * allowance, and spending it without asking is not ours to do. The ask has
 * lived on the Decks page, which nobody opens in the middle of a review —
 * so a card flagged as not-in-your-language stayed that way forever.
 *
 * This puts the ask exactly where the gap is noticed. One call fills every
 * pending personal card, not just this one, so a single unit buys the whole
 * backlog — and the cost is stated before it is spent, never after.
 */
export default function TranslateMyCards({ languageId }: { languageId: string }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [done, setDone] = useState<number | null>(null)

  // Costs nothing to ask; this is what lets the button quote the count.
  const { data: status } = useQuery({
    queryKey: ['personal-translation-status', languageId],
    queryFn: () => getPersonalTranslationStatus(languageId),
    enabled: !!languageId,
    retry: false,
  })

  const translate = useMutation({
    mutationFn: () => translatePersonalCards(languageId),
    onSuccess: (r) => {
      setDone(r.translated)
      // The card in front of the learner is re-fetched with it.
      queryClient.invalidateQueries({ queryKey: ['due-cards'] })
      queryClient.invalidateQueries({ queryKey: ['personal-translation-status'] })
    },
  })

  if (done !== null) {
    return (
      <span className="ms-2 text-[11px] text-green-600" data-testid="translate-mine-done">
        {done > 0 ? t('review.translateMineDone', { count: done }) : t('review.translateMineNone')}
      </span>
    )
  }
  // Nothing to offer when the feature is off or nothing is pending —
  // a button that cannot work is worse than no button.
  if (!status?.available || !status.pending) return null

  return (
    <>
      <button
        type="button"
        onClick={() => translate.mutate()}
        disabled={translate.isPending}
        data-testid="translate-mine"
        className="ms-2 rounded-full border border-lang/30 px-2 py-0.5 text-[11px] text-lang hover:bg-lang-soft disabled:opacity-50"
      >
        {translate.isPending
          ? t('review.translateMineWorking')
          : t('review.translateMine', { count: status.pending })}
      </button>
      {translate.isError && (
        <span className="ms-2 text-[11px] text-red-600">
          {t('review.translateMineFailed')}
        </span>
      )}
    </>
  )
}
