import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import PlanPicker, { DEFAULT_OPTION } from '../features/billing/PlanPicker'
import { optionPrice, optionPurchasable } from '../api/billing'

const PRICES = {
  single: { amount_cents: 700, currency: 'usd', interval: 'month' },
  all: { amount_cents: 1200, currency: 'usd', interval: 'month' },
  ai_addon: { amount_cents: 500, currency: 'usd', interval: 'month' },
  pools: { free: 20, single: 0, all: 300, plus: 200 },
  monetization: true,
}

describe('PlanPicker — the four options', () => {
  it('shows all four, with Single + AI recommended and preselected', () => {
    // Owner: "Single language with AI should be the default but provide
    // options to upgrade."
    render(
      <PlanPicker languageName="Spanish" prices={PRICES} value={DEFAULT_OPTION} onChange={vi.fn()} />,
    )
    for (const key of ['single_ai', 'single', 'all_ai', 'all']) {
      expect(screen.getByTestId(`plan-option-${key}`)).toBeDefined()
    }
    const rec = screen.getByTestId('plan-option-single_ai')
    expect(rec.getAttribute('aria-pressed')).toBe('true')
    expect(rec.textContent).toContain('Recommended')
    expect(rec.textContent).toContain('Spanish + AI')
  })

  it('prices an AI option as its scope plus the add-on, and says what it includes', () => {
    render(
      <PlanPicker languageName="Spanish" prices={PRICES} value={DEFAULT_OPTION} onChange={vi.fn()} />,
    )
    const singleAi = screen.getByTestId('plan-option-single_ai')
    expect(singleAi.textContent).toContain('$12.00/month')   // 7 + 5
    expect(singleAi.textContent).toContain('200 AI messages a month')
    const all = screen.getByTestId('plan-option-all')
    expect(all.textContent).toContain('$12.00/month')
    expect(all.textContent).toContain('No AI included')
    const allAi = screen.getByTestId('plan-option-all_ai')
    expect(allAi.textContent).toContain('$17.00/month')      // 12 + 5
    expect(allAi.textContent).toContain('500 AI messages a month')
  })

  it('selects the option that was tapped', () => {
    const onChange = vi.fn()
    render(
      <PlanPicker languageName="Spanish" prices={PRICES} value={DEFAULT_OPTION} onChange={onChange} />,
    )
    fireEvent.click(screen.getByTestId('plan-option-all'))
    expect(onChange).toHaveBeenCalledWith({ scope: 'all', ai: false })
  })

  it('keeps the AI options visible but unbuyable until the add-on is priced', () => {
    // Hiding them would make the four options look like two. Greyed, with
    // the reason, and a tap does nothing.
    const onChange = vi.fn()
    const prices = { ...PRICES, ai_addon: null }
    render(
      <PlanPicker languageName="Spanish" prices={prices} value={{ scope: 'single', ai: false }} onChange={onChange} />,
    )
    const singleAi = screen.getByTestId('plan-option-single_ai')
    expect(singleAi.getAttribute('aria-disabled')).toBe('true')
    expect(singleAi.textContent).toContain('aren’t available on this server yet')
    fireEvent.click(singleAi)
    expect(onChange).not.toHaveBeenCalled()
    expect(optionPurchasable(prices, { scope: 'single', ai: true })).toBe(false)
    expect(optionPurchasable(prices, { scope: 'single', ai: false })).toBe(true)
  })

  it('shows no price at all while monetization is off', () => {
    render(
      <PlanPicker
        languageName="Spanish"
        prices={{ single: null, all: null, monetization: false }}
        value={DEFAULT_OPTION}
        onChange={vi.fn()}
      />,
    )
    expect(screen.getByTestId('plan-picker').textContent).not.toMatch(/\$/)
    expect(optionPrice(undefined, DEFAULT_OPTION)).toBeNull()
  })

  it('an admin-set charge is the whole price of any option', () => {
    // The server mirrors the custom amount onto both scopes and sends no
    // add-on; adding one on top would double-charge the AI half.
    const custom = { amount_cents: 999, currency: 'usd', interval: 'month' }
    const prices = { single: custom, all: custom, custom, ai_addon: null, monetization: true }
    expect(optionPrice(prices, { scope: 'all', ai: true })?.amount_cents).toBe(999)
    expect(optionPurchasable(prices, { scope: 'all', ai: true })).toBe(true)
  })
})
