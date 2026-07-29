import { describe, it, expect } from 'vitest'
import { pendingMigrationNote } from '../api/health'

describe('pendingMigrationNote', () => {
  it('names the migration when the database is behind', () => {
    expect(
      pendingMigrationNote({ ok: false, missing_migrations: ['20260902000000_placement_attempts.sql'] }),
    ).toContain('20260902000000_placement_attempts.sql')
  })

  it('counts the rest rather than listing them all', () => {
    const note = pendingMigrationNote({
      ok: false,
      missing_migrations: ['a.sql', 'b.sql', 'c.sql'],
    })
    expect(note).toContain('a.sql')
    expect(note).toContain('and 2 more')
  })

  it('says nothing when the schema is in step — the failure was something else', () => {
    expect(pendingMigrationNote({ ok: true, missing_migrations: [] })).toBeNull()
    expect(pendingMigrationNote({ ok: true })).toBeNull()
  })

  it('says nothing when the check itself could not run', () => {
    // A diagnostic that fails loudly is worse than none.
    expect(pendingMigrationNote(null)).toBeNull()
  })
})
