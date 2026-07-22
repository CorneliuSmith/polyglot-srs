import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the axios client so we can assert the exact URLs hit. Declared via
// vi.hoisted so the refs exist when the hoisted vi.mock factory runs.
const { get, post, patch, del } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  del: vi.fn(),
}))
vi.mock('../api/client', () => ({
  default: { get, post, patch, delete: del },
}))

import {
  createPersonalDeck,
  deletePersonalDeck,
  filePersonalCard,
  getPersonalCards,
  getPersonalDecks,
  renamePersonalDeck,
} from '../api/personalDecks'

describe('personalDecks API — /api prefix (deck page crash regression)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    get.mockResolvedValue({ data: [] })
    post.mockResolvedValue({ data: { id: 'd1' } })
    patch.mockResolvedValue({ data: {} })
    del.mockResolvedValue({ data: {} })
  })

  // Every endpoint must be under /api so DigitalOcean's path router sends it
  // to the backend. A missing prefix returned the SPA's index.html (HTML),
  // and `htmlString.filter(...)` crashed the Decks page on load.
  it('all personal-deck calls target /api/personal-decks', async () => {
    await getPersonalDecks('lang-1')
    await getPersonalCards('lang-1')
    await createPersonalDeck('lang-1', 'X')
    await renamePersonalDeck('deck-1', 'Y')
    await deletePersonalDeck('deck-1')
    await filePersonalCard('card-1', 'deck-1')

    expect(get).toHaveBeenCalledWith('/api/personal-decks', expect.anything())
    expect(get).toHaveBeenCalledWith('/api/personal-decks/cards', expect.anything())
    expect(post).toHaveBeenCalledWith('/api/personal-decks', expect.anything())
    expect(patch).toHaveBeenCalledWith('/api/personal-decks/deck-1', expect.anything())
    expect(del).toHaveBeenCalledWith('/api/personal-decks/deck-1')
    expect(patch).toHaveBeenCalledWith('/api/personal-decks/cards/card-1', expect.anything())
  })

  it('coerces a null body to an empty array (defense in depth)', async () => {
    get.mockResolvedValueOnce({ data: null })
    expect(await getPersonalDecks('lang-1')).toEqual([])
    get.mockResolvedValueOnce({ data: null })
    expect(await getPersonalCards('lang-1')).toEqual([])
  })
})
