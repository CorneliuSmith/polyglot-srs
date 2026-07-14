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

export interface PlanPrices {
  single: PlanPrice | null
  all: PlanPrice | null
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
