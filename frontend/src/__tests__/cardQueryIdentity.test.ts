import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

/**
 * The loading contract (docs/plans/language-switch-loading.md): no card
 * renders until the app knows which language pair it belongs to, and a
 * card fetched under one identity is never shown under another.
 *
 * This audit is the contract's tripwire. It reads the surfaces that fetch
 * card-shaped content and asserts the shape that keeps them honest — so
 * the next surface added without identity in its key fails HERE, with the
 * plan document named, instead of shipping the next wrong-language deck.
 */
const src = (rel: string) =>
  readFileSync(join(__dirname, '..', rel), 'utf8')

describe('every card query carries its language identity', () => {
  it('Review: the deck key holds language + locale, and the fetch waits for the profile', () => {
    const page = src('features/review/ReviewSessionPage.tsx')
    // Key: ['due-cards', activeLanguageId, …, supportLocale, deckEpoch]
    expect(page).toMatch(
      /'due-cards',\s*activeLanguageId[\s\S]{0,120}supportLocale/,
    )
    // Gate: no fetch under the placeholder locale (C3 in the plan).
    expect(page).toMatch(/enabled:\s*!!activeLanguageId\s*&&\s*profileResolved/)
  })

  it('Review: the remount key carries both halves of the identity', () => {
    const page = src('features/review/ReviewSessionPage.tsx')
    expect(page).toMatch(/key=\{`\$\{activeLanguageId \?\? 'none'\}:\$\{epoch\}`\}/)
  })

  it('Learn: the remount key carries both halves of the identity', () => {
    const page = src('features/review/LearnPage.tsx')
    expect(page).toMatch(/key=\{`\$\{activeLanguageId \?\? 'none'\}:\$\{epoch\}`\}/)
  })

  it('the parked session is keyed by identity, not URL alone', () => {
    const snap = src('features/review/sessionSnapshot.ts')
    expect(snap).toMatch(/identity:\s*string/)
    expect(snap).toMatch(/review-session:\$\{identity\}/)
  })

  it('the wait games pool from language-keyed queries', () => {
    expect(src('features/review/TrailblazerWait.tsx')).toMatch(
      /'session-readiness',\s*languageId/,
    )
    expect(src('features/reader/ReadingWait.tsx')).toMatch(
      /'due-cards',\s*languageId/,
    )
  })

  it('cram is the documented exception: point-scoped by design', () => {
    // Cram decks are drawn from grammar points the learner picked — the
    // points ARE the identity. If this shape changes, revisit the plan.
    expect(src('features/review/ReviewSessionPage.tsx')).toMatch(
      /'cram-cards',\s*cramPoints/,
    )
  })
})
