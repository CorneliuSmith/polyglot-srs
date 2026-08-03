import { describe, it, expect, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import i18n from '../i18n'
import DirArrow from '../components/DirArrow'

async function reset() {
  await i18n.changeLanguage('en')
}

describe('DirArrow', () => {
  afterEach(reset)

  it('forward points right in LTR, left in RTL', async () => {
    await i18n.changeLanguage('en')
    const { rerender } = render(<DirArrow />)
    expect(screen.getByText('→')).toBeDefined()

    await i18n.changeLanguage('ar')
    rerender(<DirArrow />)
    expect(screen.getByText('←')).toBeDefined()
  })

  it('back points left in LTR, right in RTL — the opposite of forward', async () => {
    await i18n.changeLanguage('en')
    const { rerender } = render(<DirArrow dir="back" />)
    expect(screen.getByText('←')).toBeDefined()

    await i18n.changeLanguage('ar')
    rerender(<DirArrow dir="back" />)
    expect(screen.getByText('→')).toBeDefined()
  })

  it('is decorative — hidden from assistive tech', () => {
    render(<DirArrow />)
    const el = screen.getByText('→')
    expect(el.getAttribute('aria-hidden')).toBe('true')
  })

  it('forwards the className', () => {
    render(<DirArrow className="text-lang" />)
    expect(screen.getByText('→').className).toBe('text-lang')
  })
})
