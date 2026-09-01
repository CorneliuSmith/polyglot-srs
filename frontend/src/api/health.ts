import apiClient from './client'

export interface SchemaHealth {
  ok: boolean
  initialized?: boolean
  /** Migration filenames the database is missing. */
  missing_migrations?: string[]
  /** "table.column (from 00000_x.sql)" for each absent object. */
  missing?: string[]
  error?: string
}

/**
 * Is the database in step with this build?
 *
 * The backend has answered this since the Gym 500, but nothing in the UI ever
 * asked — so every "why is this one feature broken after a deploy" has been
 * diagnosed by hand. A surface that fails for a schema reason can call this
 * and say WHICH migration is missing instead of "something went wrong".
 *
 * Never throws: a diagnostic that can itself fail loudly is worse than none.
 */
export async function getSchemaHealth(): Promise<SchemaHealth | null> {
  try {
    const response = await apiClient.get<SchemaHealth>('/api/health/schema')
    return response.data
  } catch {
    return null
  }
}

/** The one-line cause to show a user, or null when the schema is fine and
 *  the failure was something else. */
export function pendingMigrationNote(health: SchemaHealth | null): string | null {
  const missing = health?.missing_migrations ?? []
  if (missing.length === 0) return null
  const first = missing[0]
  const rest = missing.length > 1 ? ` (and ${missing.length - 1} more)` : ''
  return `The database is behind this build — ${first}${rest} hasn’t been applied yet.`
}

export interface BuildInfo {
  /** Git commit, when the platform passed one at build time; null otherwise. */
  sha: string | null
  /** When the image was built (ISO), null outside a Docker image. */
  built_at: string | null
  /** The newest migration file this build ships — the newest it expects
   *  the database to have. */
  latest_migration: string | null
  /** 0 means the image carries no migration files and the schema check is
   *  blind. */
  migrations_shipped: number
}

/** What the API is running — the answer to "is X deployed yet?" that used
 *  to be a guess. Never throws. */
export async function getBuildInfo(): Promise<BuildInfo | null> {
  try {
    const response = await apiClient.get<{ status: string; build?: BuildInfo }>(
      '/api/health',
    )
    return response.data.build ?? null
  } catch {
    return null
  }
}
