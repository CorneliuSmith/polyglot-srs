import { useQuery } from '@tanstack/react-query'
import { getPlanPrices, type PlanPrices } from '../../api/billing'

/**
 * The monetization master switch, as one hook every money surface shares.
 *
 * Money features are OFF until the owner flips the switch in the admin
 * panel (employer conflict-of-interest hold) — and while off, nothing
 * payment-shaped may render: no prices, upgrade buttons, top-ups, tip
 * jar, or billing links. The flag rides on /plan/prices, which Settings
 * and Onboarding already fetch, so every consumer shares one cached
 * request under the same query key.
 *
 * Fails CLOSED: while loading, on error, and against an older server
 * that doesn't send the flag, `monetization` is false. A late flip from
 * false → true after load is fine (a button appears); the reverse never
 * happens mid-session because the value is cached for the session.
 */
export function useMonetization(): {
  monetization: boolean
  prices: PlanPrices | undefined
} {
  const { data } = useQuery({
    queryKey: ['plan-prices'],
    queryFn: getPlanPrices,
    staleTime: Infinity,
    retry: false,
  })
  return { monetization: data?.monetization === true, prices: data }
}
