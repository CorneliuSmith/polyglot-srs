import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getGymManifest } from '../../api/gym'
import DrillsEditor from './DrillsEditor'

/**
 * Gym-centric view of the drill corpus for the Contributor section: the form
 * categories the Gym trains (verbs, cases, …) with how many drills each holds.
 * Expand one to review or edit its drills via the same DrillsEditor used on the
 * grammar-point editor — so the Gym's coverage is inspectable in one place,
 * alongside the generated-drill review queue. Hidden for languages with no Gym.
 */
export default function GymDrillsPanel({
  languageId,
  canEdit,
}: {
  languageId: string
  canEdit: boolean
}) {
  const { data } = useQuery({
    queryKey: ['gym-manifest', languageId],
    queryFn: () => getGymManifest(languageId),
    enabled: !!languageId,
    retry: false,
  })
  const [openId, setOpenId] = useState<string | null>(null)

  const columns = data?.columns ?? []
  if (columns.length === 0) return null

  return (
    <section
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-4"
      data-testid="gym-drills-panel"
    >
      <div>
        <h2 className="font-semibold text-gray-900">Gym drills</h2>
        <p className="text-xs text-gray-500">
          The form categories the Gym trains, and how many drills each has.
          Expand one to review or edit its drills.
        </p>
      </div>

      {columns.map((col) => (
        <div key={col.kind} className="space-y-1.5">
          <p className="text-xs uppercase tracking-wide text-gray-400">
            {col.label}
          </p>
          {col.entries.map((e) => {
            const open = openId === e.point_id
            return (
              <div
                key={e.point_id}
                className="rounded-lg border border-gray-100 overflow-hidden"
              >
                <button
                  type="button"
                  onClick={() => setOpenId(open ? null : e.point_id)}
                  aria-expanded={open}
                  className="w-full flex items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-gray-50"
                >
                  <span className="font-medium text-gray-800">
                    {e.label}
                    {e.nonstandard && (
                      <span className="ml-2 text-[10px] uppercase tracking-wide text-amber-600">
                        non-standard
                      </span>
                    )}
                  </span>
                  <span className="flex items-center gap-2 text-xs text-gray-400">
                    <span className="tabular-nums">
                      {e.drills} drill{e.drills === 1 ? '' : 's'}
                    </span>
                    {e.level && <span>{e.level}</span>}
                    <span
                      aria-hidden
                      className={'inline-block transition-transform ' + (open ? 'rotate-180' : '')}
                    >
                      ⌄
                    </span>
                  </span>
                </button>
                {open && (
                  <div className="px-3 pb-3 border-t border-gray-100">
                    <DrillsEditor pointId={e.point_id} canEdit={canEdit} />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ))}
    </section>
  )
}
