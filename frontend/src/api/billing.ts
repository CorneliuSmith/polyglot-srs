import apiClient from './client'

export interface CheckoutResponse {
  granted: boolean
  url: string | null
}

/**
 * Start a tutor subscription. In production this returns a Stripe Checkout URL
 * to redirect to; in dev-mock mode the server grants access directly and
 * returns { granted: true, url: null }.
 */
export async function createCheckout(languageId: string): Promise<CheckoutResponse> {
  const response = await apiClient.post<CheckoutResponse>('/api/billing/checkout', {
    language_id: languageId,
  })
  return response.data
}

export interface PlanPrice {
  amount_cents: number | null
  currency: string | null
  interval: string | null
}

export interface TopupPrice {
  amount_cents: number
  currency: string
  /** How many messages one purchase adds to the CURRENT month's pool. */
  messages: number
}

/** A plan option: which languages, and whether the monthly AI pool is
 *  included. The four options are the four combinations. */
export interface PlanOption {
  scope: 'single' | 'all'
  ai: boolean
}

/** Messages a month per tier, as the admin has them set — what an option
 *  INCLUDES. An option with AI gets its scope's pool plus `plus`. */
export interface PlanPools {
  free: number
  single: number
  all: number
  plus: number
}

export interface PlanPrices {
  single: PlanPrice | null
  all: PlanPrice | null
  /** The AI add-on's monthly price. An option with AI costs its scope's
   * price plus this; null until the add-on is priced on the server. */
  ai_addon?: PlanPrice | null
  pools?: PlanPools | null
  /** Admin-set monthly charge for THIS account. When present the server
   * already mirrors it onto both scopes, so price displays need no special
   * casing — this field just names the fact for UIs that want to. */
  custom?: PlanPrice | null
  /** The one-time AI top-up's price, or null when it can't be bought. */
  topup?: TopupPrice | null
  /** The master switch. False (or absent, on an older server) means NO
   * money surface renders anywhere: no prices, upgrade buttons, top-ups,
   * or the tip jar. Flipped from the admin panel. */
  monetization?: boolean
}

/** Live Stripe prices for the two plans; null until billing is configured. */
export async function getPlanPrices(): Promise<PlanPrices> {
  const response = await apiClient.get<PlanPrices>('/api/billing/plan/prices')
  return response.data
}

/** Start a subscription to one of the four plan options — also every
 *  upgrade path: a different option replaces the current plan on webhook
 *  completion, and the server cancels the subscription it replaced. */
export async function startPlanCheckout(
  planScope: 'single' | 'all',
  planLanguageId?: string | null,
  ai = false,
): Promise<CheckoutResponse> {
  const response = await apiClient.post<CheckoutResponse>(
    '/api/billing/plan/checkout',
    { plan_scope: planScope, plan_language_id: planLanguageId ?? null, ai },
  )
  return response.data
}

/** The monthly price of an option: its scope's price plus the AI add-on's
 *  when AI is included. Null when either half is unpriced, so the UI shows
 *  its unpriced copy rather than half a number. */
export function optionPrice(
  prices: PlanPrices | undefined,
  option: PlanOption,
): PlanPrice | null {
  const base = prices?.[option.scope] ?? null
  if (!base || base.amount_cents == null) return null
  if (!option.ai) return base
  // An admin-set charge is the whole price of whichever option the account
  // picks — the server mirrors it onto both scopes and sends no add-on.
  if (prices?.custom) return base
  const addon = prices?.ai_addon ?? null
  if (!addon || addon.amount_cents == null) return null
  if (addon.currency !== base.currency) return null
  return {
    amount_cents: base.amount_cents + addon.amount_cents,
    currency: base.currency,
    interval: base.interval,
  }
}

/** Whether an option can be bought right now: no-AI options need the plan
 *  priced, AI options need the add-on priced too (or an admin charge). */
export function optionPurchasable(
  prices: PlanPrices | undefined,
  option: PlanOption,
): boolean {
  if (!prices?.monetization) return false
  if (prices.custom) return true
  if (!prices[option.scope]) return false
  return !option.ai || !!prices.ai_addon
}

/** Buy a one-time AI top-up — messages added to the CURRENT month's pool. */
export async function createTopupCheckout(): Promise<CheckoutResponse> {
  const response = await apiClient.post<CheckoutResponse>('/api/billing/topup')
  return response.data
}

/** Stripe Billing Portal — plan changes and cancellations prorate there. */
export async function openBillingPortal(): Promise<string> {
  const response = await apiClient.post<{ url: string }>('/api/billing/portal')
  return response.data.url
}

export function formatPrice(price: PlanPrice | null): string | null {
  if (!price || price.amount_cents == null || !price.currency) return null
  const amount = (price.amount_cents / 100).toLocaleString(undefined, {
    style: 'currency',
    currency: price.currency.toUpperCase(),
  })
  return price.interval ? `${amount}/${price.interval}` : amount
}
