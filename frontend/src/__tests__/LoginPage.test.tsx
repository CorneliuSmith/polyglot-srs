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

vi.mock('../api/trial', () => ({ requestTrial: vi.fn() }))

import { requestTrial } from '../api/trial'
import { supabase } from '../lib/supabase'

const mockReset = supabase.auth.resetPasswordForEmail as ReturnType<typeof vi.fn>
const mockOAuth = supabase.auth.signInWithOAuth as ReturnType<typeof vi.fn>
const mockTrial = requestTrial as ReturnType<typeof vi.fn>

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

  it('requests a trial from the login page (the invite-only front door)', async () => {
    mockTrial.mockResolvedValue(undefined)
    render(<LoginPage />)

    fireEvent.click(
      screen.getByRole('button', { name: /request trial access/i }),
    )
    // No password in trial mode — nothing to type before approval.
    expect(screen.queryByLabelText(/^password$/i)).toBeNull()

    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'kate@example.com' },
    })
    fireEvent.change(screen.getByLabelText(/name \(optional\)/i), {
      target: { value: 'Kate' },
    })
    fireEvent.click(
      screen.getByRole('button', { name: /^request trial access$/i }),
    )

    await waitFor(() =>
      expect(mockTrial).toHaveBeenCalledWith('kate@example.com', 'Kate', ''))
    expect(await screen.findByText(/request received/i)).toBeDefined()
  })

  it('surfaces the server detail when trial signup is unavailable', async () => {
    mockTrial.mockRejectedValue({
      response: { data: { detail: 'Trial signup isn’t available on this server yet' } },
    })
    render(<LoginPage />)
    fireEvent.click(
      screen.getByRole('button', { name: /request trial access/i }),
    )
    fireEvent.change(screen.getByLabelText(/email/i), {
      target: { value: 'kate@example.com' },
    })
    fireEvent.click(
      screen.getByRole('button', { name: /^request trial access$/i }),
    )
    expect(
      await screen.findByText(/isn’t available on this server/i),
    ).toBeDefined()
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
