import { useQuery } from '@tanstack/react-query'
import { getBuildInfo, getSchemaHealth } from '../../api/health'

/**
 * What is deployed, and is the database keeping up with it.
 *
 * Three rounds of "I still don't see the setting" against the live app,
 * with the setting on `main` the whole time, came down to two unknowables:
 * which build the server was running, and whether the migration that
 * setting needs had been applied. Both were answerable by the API — and
 * nothing in the UI asked. This panel asks, so the owner reads it here
 * instead of asking an engineer to guess.
 *
 * Read-only by design. Migrations are owner-applied (`supabase db push`);
 * the app names what is missing and stops there.
 */
export default function DeploymentPanel() {
  const { data: build, isLoading: buildLoading } = useQuery({
    queryKey: ['build-info'],
    queryFn: getBuildInfo,
    retry: false,
    staleTime: 60_000,
  })
  const { data: schema, isLoading: schemaLoading } = useQuery({
    queryKey: ['schema-health'],
    queryFn: getSchemaHealth,
    retry: false,
    staleTime: 60_000,
  })

  const missing = schema?.missing_migrations ?? []
  const blind = !!schema?.error || (build != null && build.migrations_shipped === 0)

  return (
    <section
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm"
      data-testid="deployment"
    >
      <h2 className="font-semibold text-gray-800">Deployment</h2>
      <p className="mt-1 text-xs text-gray-500">
        Which build is serving, and whether the database has every migration
        it needs. A feature that is on the branch but not here has not
        deployed; a feature that 500s while everything else works is almost
        always a migration listed below.
      </p>

      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
        <dt className="text-gray-500">Built</dt>
        <dd className="tabular-nums text-gray-800" data-testid="deployment-built">
          {buildLoading
            ? '…'
            : build?.built_at
              ? new Date(build.built_at).toLocaleString()
              : 'unknown (not a container build)'}
        </dd>
        <dt className="text-gray-500">Commit</dt>
        <dd className="font-mono text-gray-800" data-testid="deployment-sha">
          {buildLoading ? '…' : build?.sha ? build.sha.slice(0, 12) : 'not recorded by the platform'}
        </dd>
        <dt className="text-gray-500">Newest migration in this build</dt>
        <dd className="font-mono text-gray-800" data-testid="deployment-migration">
          {buildLoading ? '…' : (build?.latest_migration ?? 'none shipped')}
        </dd>
      </dl>

      <div className="mt-3" data-testid="deployment-schema">
        {schemaLoading ? (
          <p className="text-xs text-gray-500">Checking the database…</p>
        ) : blind ? (
          <p className="text-xs text-amber-700">
            This build cannot check the schema — it carries no migration
            files. Redeploy from a build that ships <code>supabase/migrations</code>.
          </p>
        ) : schema == null ? (
          <p className="text-xs text-gray-500">The schema check did not answer.</p>
        ) : schema.initialized === false ? (
          <p className="text-xs text-red-700">
            The database is empty — no migrations have been applied.
          </p>
        ) : missing.length === 0 ? (
          <p className="text-xs text-emerald-700">
            The database has every migration this build expects.
          </p>
        ) : (
          <div>
            <p className="text-xs text-red-700">
              The database is behind this build. Apply, in order:
            </p>
            <ul className="mt-1 space-y-0.5 font-mono text-xs text-gray-800">
              {missing.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
            {schema.missing && schema.missing.length > 0 && (
              <details className="mt-2 text-xs text-gray-600">
                <summary className="cursor-pointer">
                  What each one adds ({schema.missing.length})
                </summary>
                <ul className="mt-1 space-y-0.5 font-mono">
                  {schema.missing.map((m) => (
                    <li key={m}>{m}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
