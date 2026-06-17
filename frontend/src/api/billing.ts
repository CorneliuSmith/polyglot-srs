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
