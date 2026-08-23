import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  __resetActiveLanguageSyncForTests,
  chooseActiveLanguage,
  syncActiveLanguageFromProfile,
} from '../lib/activeLanguage'
import { usePrefsStore } from '../stores/prefsStore'

vi.mock('../api/profile', () => ({
  updateProfile: vi.fn(() => Promise.resolve({})),
}))

import { updateProfile } from '../api/profile'

const mockUpdateProfile = updateProfile as ReturnType<typeof vi.fn>

// The study language follows the account the same way ui_language does:
// every explicit switch writes the profile, every profile read is allowed
// to overrule the device. These pin the ordering rules — who wins when.
describe('the study language and the account', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    __resetActiveLanguageSyncForTests()
    usePrefsStore.setState({ activeLanguageId: null })
  })

  it('an explicit switch sets this device AND the account', () => {
    chooseActiveLanguage('lang-es')
    expect(usePrefsStore.getState().activeLanguageId).toBe('lang-es')
    expect(mockUpdateProfile).toHaveBeenCalledWith({
      active_language_id: 'lang-es',
    })
  })

  it('the account course wins over a stale device value', () => {
    // The write side always existed; this read side is what was missing.
    // A device that once studied Spanish kept Spanish forever, whatever
    // the account said — the exact two-device split the owner reported
    // for the UI language, one layer down.
    usePrefsStore.setState({ activeLanguageId: 'lang-es' })
    syncActiveLanguageFromProfile('lang-ru')
    expect(usePrefsStore.getState().activeLanguageId).toBe('lang-ru')
  })

  it('a switch made seconds ago is not bounced by a stale profile read', () => {
    // The switch saves to the profile asynchronously; a profile response
    // from BEFORE it can land after it. The fresh local decision holds
    // through the grace window — then its own save makes the two agree.
    chooseActiveLanguage('lang-fr')
    syncActiveLanguageFromProfile('lang-es')
    expect(usePrefsStore.getState().activeLanguageId).toBe('lang-fr')
  })

  it('an account with no course never un-chooses the device', () => {
    usePrefsStore.setState({ activeLanguageId: 'lang-es' })
    syncActiveLanguageFromProfile(null)
    expect(usePrefsStore.getState().activeLanguageId).toBe('lang-es')
  })

  it('agreement is a no-op, not a store write', () => {
    usePrefsStore.setState({ activeLanguageId: 'lang-es' })
    const before = usePrefsStore.getState()
    syncActiveLanguageFromProfile('lang-es')
    expect(usePrefsStore.getState()).toBe(before)
  })
})
