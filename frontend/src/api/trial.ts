import apiClient from './client'

/**
 * Ask for trial access (public — no session needed). The server answers
 * identically whether the email is new, already queued, or already an
 * account, so callers can only show a generic "request received".
 */
export async function requestTrial(
  email: string,
  name: string,
  note: string,
): Promise<void> {
  await apiClient.post('/api/auth/trial-request', {
    email,
    name: name.trim() || null,
    note: note.trim() || null,
  })
}
