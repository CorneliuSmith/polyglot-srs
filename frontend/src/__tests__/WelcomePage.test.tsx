import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import WelcomePage from '../features/onboarding/WelcomePage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <WelcomePage />
    </MemoryRouter>,
  )
}

describe('WelcomePage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows one card per area of the app', () => {
    renderPage()
    for (const name of [
      'Reviews',
      'Grammar Path',
      'AI Tutor',
      'The Reader',
      'Letters & Sounds',
      'Decks & Search',
    ]) {
      expect(screen.getByText(name)).toBeDefined()
    }
  })

  it('cards navigate to their feature', () => {
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: /AI Tutor/ }))
    expect(mockNavigate).toHaveBeenCalledWith('/tutor')
    fireEvent.click(screen.getByRole('button', { name: /Letters & Sounds/ }))
    expect(mockNavigate).toHaveBeenCalledWith('/letters')
  })

  it('the main button goes to the dashboard', () => {
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: 'Go to your dashboard' }))
    expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true })
  })
})
