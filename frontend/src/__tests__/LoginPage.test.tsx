import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import LoginPage from '../features/auth/LoginPage'

vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: {
      signInWithPassword: vi.fn(),
      signUp: vi.fn(),
      signInWithOAuth: vi.fn(),
      resetPasswordForEmail: vi.fn(),
    },
  },
}))

import { supabase } from '../lib/supabase'

const mockReset = supabase.auth.resetPasswordForEmail as ReturnType<typeof vi.fn>
const mockOAuth = supabase.auth.signInWithOAuth as ReturnType<typeof vi.fn>

describe('LoginPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('sends a recovery email from forgot-password mode', async () => {
    mockReset.mockResolvedValue({ error: null })
    render(<LoginPage />)

    fireEvent.click(screen.getByRole('button', { name: /forgot password/i }))
    // password field and Google button leave; the email field stays
    expect(screen.queryByLabelText(/^password$/i)).toBeNull()
    expect(screen.queryByText(/sign in with google/i)).toBeNull()

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'me@example.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send reset link/i }))

    await waitFor(() =>
      expect(mockReset).toHaveBeenCalledWith('me@example.com', {
        redirectTo: `${window.location.origin}/reset-password`,
      }),
    )
    expect(
      await screen.findByText(/reset link is on its way/i),
    ).toBeDefined()
  })

  it('returns to sign-in from reset mode', () => {
    render(<LoginPage />)
    fireEvent.click(screen.getByRole('button', { name: /forgot password/i }))
    fireEvent.click(screen.getByRole('button', { name: /back to sign in/i }))
    expect(screen.getByLabelText(/^password$/i)).toBeDefined()
    expect(screen.getByText(/sign in with google/i)).toBeDefined()
  })

  it('explains when an OAuth provider is not enabled server-side', async () => {
    mockOAuth.mockResolvedValue({
      error: { message: 'Unsupported provider: provider is not enabled' },
    })
    render(<LoginPage />)
    fireEvent.click(screen.getByText(/sign in with google/i))
    expect(
      await screen.findByText(/isn’t configured on this server/i),
    ).toBeDefined()
  })
})
