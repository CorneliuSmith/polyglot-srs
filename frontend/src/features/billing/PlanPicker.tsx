import { useTranslation } from 'react-i18next'
import {
  formatPrice,
  optionPrice,
  optionPurchasable,
  type PlanOption,
  type PlanPrices,
} from '../../api/billing'

/**
 * The four plan options, as one choice.
 *
 * A plan is two decisions — which languages, and whether AI is included —
 * and the app used to sell them as two separate purchases on two different
 * pages (a scope at signup, an add-on from the tutor). The owner's ask:
 * "Make the 4 options … Single language with AI should be the default but
 * provide options to upgrade." So every combination is a card, the
 * recommended one is preselected, and each card says the two things that
 * decide it: what you can study, and how much AI a month that includes.
 *
 * Prices are never hardcoded: an option with AI costs its scope's price
 * plus the add-on's, both read live from Stripe (`optionPrice`). Pool
 * sizes come from the server too — an admin can change them — so the card
 * never claims a number the account won't get.
 */

export const DEFAULT_OPTION: PlanOption = { scope: 'single', ai: true }

/** Display order: the recommended option first, then its no-AI sibling,
 *  then the two all-languages options — cheapest to dearest within each. */
const ORDER: PlanOption[] = [
  { scope: 'single', ai: true },
  { scope: 'single', ai: false },
  { scope: 'all', ai: true },
  { scope: 'all', ai: false },
]

export function optionKey(o: PlanOption): string {
  return `${o.scope}${o.ai ? '_ai' : ''}`
}

export function sameOption(a: PlanOption, b: PlanOption): boolean {
  return a.scope === b.scope && a.ai === b.ai
}

/** The option's name — "Spanish + AI", "All languages" — for headings and
 *  buttons. Exported so Settings can name the CURRENT plan the same way. */
export function useOptionName() {
  const { t } = useTranslation()
  return (o: PlanOption, languageName: string) =>
    o.scope === 'single'
      ? o.ai
        ? t('plans.singleAi', { language: languageName })
        : t('plans.single', { language: languageName })
      : o.ai
        ? t('plans.allAi')
        : t('plans.all')
}

export default function PlanPicker({
  languageName,
  prices,
  value,
  onChange,
  current,
}: {
  /** The language a single-language option is for. */
  languageName: string
  prices: PlanPrices | undefined
  value: PlanOption
  onChange: (o: PlanOption) => void
  /** The plan the account is on now, when changing rather than choosing —
   *  marked, and not offered as a "change". */
  current?: PlanOption | null
}) {
  const { t } = useTranslation()
  const name = useOptionName()
  const monetization = prices?.monetization === true
  const pools = prices?.pools ?? null

  return (
    <div className="space-y-2" data-testid="plan-picker">
      {ORDER.map((o) => {
        const selected = sameOption(o, value)
        const isCurrent = !!current && sameOption(o, current)
        const recommended = sameOption(o, DEFAULT_OPTION)
        const price = formatPrice(optionPrice(prices, o))
        // An AI option that cannot be bought yet (the add-on isn't priced
        // on this server) is shown, greyed, with the reason — hiding it
        // would make the four options look like two.
        const blocked = monetization && !!prices?.[o.scope] && o.ai &&
          !optionPurchasable(prices, o)
        const messages = pools
          ? (o.scope === 'all' ? pools.all : pools.single) + (o.ai ? pools.plus : 0)
          : null
        return (
          <button
            key={optionKey(o)}
            type="button"
            onClick={() => !blocked && onChange(o)}
            aria-pressed={selected}
            aria-disabled={blocked || undefined}
            data-testid={`plan-option-${optionKey(o)}`}
            className={
              'w-full rounded-xl border px-4 py-3 text-start active:bg-lang-soft ' +
              (selected
                ? 'border-lang bg-lang-soft'
                : 'border-gray-200 bg-white hover:border-lang/50') +
              (blocked ? ' opacity-60 cursor-not-allowed' : '')
            }
          >
            <span className="flex items-start justify-between gap-3">
              <span className="block">
                <span className="block text-sm font-semibold text-gray-800">
                  {name(o, languageName)}
                  {recommended && !isCurrent && (
                    <span className="ms-2 rounded-full bg-lang px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-lang-on">
                      {t('plans.recommended')}
                    </span>
                  )}
                  {isCurrent && (
                    <span className="ms-2 rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-gray-600">
                      {t('plans.current')}
                    </span>
                  )}
                </span>
                <span className="block text-xs text-gray-600">
                  {o.scope === 'single'
                    ? t('plans.scopeSingle', { language: languageName })
                    : t('plans.scopeAll')}
                </span>
                <span className="block text-xs text-gray-500">
                  {o.ai
                    ? messages != null
                      ? t('plans.aiIncluded', { count: messages })
                      : t('plans.aiIncluded', { count: '' }).replace(/^\s*/, '')
                    : t('plans.aiNone')}
                </span>
                {blocked && (
                  <span className="block text-xs text-amber-700">
                    {t('plans.aiUnavailable')}
                  </span>
                )}
              </span>
              {/* Monetization off: no price anywhere on the screen. */}
              {monetization && (
                <span className="shrink-0 text-sm font-semibold text-gray-800">
                  {price ? t('plans.perMonth', { price }) : (
                    <span className="text-xs font-normal text-gray-500">
                      {t('plans.unpriced')}
                    </span>
                  )}
                </span>
              )}
            </span>
          </button>
        )
      })}
    </div>
  )
}
