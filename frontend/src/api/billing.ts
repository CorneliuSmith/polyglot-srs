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

export interface PlanPrices {
  single: PlanPrice | null
  all: PlanPrice | null
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

/** Start a plan subscription (also the single → all upgrade path). */
export async function startPlanCheckout(
  planScope: 'single' | 'all',
  planLanguageId?: string | null,
): Promise<CheckoutResponse> {
  const response = await apiClient.post<CheckoutResponse>(
    '/api/billing/plan/checkout',
    { plan_scope: planScope, plan_language_id: planLanguageId ?? null },
  )
  return response.data
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
