import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Eye } from 'lucide-react'
import { getMyRoles } from '../api/contribute'
import { useViewAsStore } from '../stores/viewAsStore'
import { VIEW_AS_LABEL, VIEW_AS_LEVELS, type ViewAsLevel } from '../lib/viewAs'

/**
 * Admin "view as" switcher (owner request): preview the app at each access
 * level without a second account.
 *
 * Sits above every authenticated page (mounted once in ProtectedRoute) and
 * renders for nobody but a real admin. Switching levels re-fetches the
 * role-gated queries so the whole UI — nav, panels, buttons — settles into
 * what that level actually sees.
 *
 * It is a PREVIEW, not a permission change: the downgrade only ever removes
 * capability client-side, and every privileged endpoint re-derives the
 * caller's real roles server-side. The bar stays visible (and loud) while a
 * preview is on so an admin can never forget they're wearing it.
 */
export default function ViewAsBar() {
  const queryClient = useQueryClient()
  const viewAs = useViewAsStore((s) => s.viewAs)
  const setViewAs = useViewAsStore((s) => s.setViewAs)

  // The preview downgrades getMyRoles, so this query can't answer "am I
  // really an admin?" while one is active. `real_is_admin` is untouched by
  // the downgrade and is what gates the bar.
  const { data } = useQuery({
    queryKey: ['my-roles-real'],
    queryFn: getMyRoles,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
  const isRealAdmin = (data?.real_is_admin ?? data?.is_admin) === true

  if (!isRealAdmin) return null

  const choose = (level: ViewAsLevel | null) => {
    setViewAs(level)
    // Role-gated data is cached per query; drop it all so each surface
    // re-derives against the new level.
    queryClient.invalidateQueries()
  }

  const previewing = viewAs !== null

  return (
    <div
      data-testid="view-as-bar"
      className={
        previewing
          ? 'bg-amber-500 text-amber-950'
          : 'bg-gray-100 text-gray-600 border-b border-gray-200'
      }
    >
      <div className="max-w-3xl mx-auto px-4 py-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
        <span className="flex items-center gap-1.5 font-medium">
          <Eye aria-hidden className="h-3.5 w-3.5" />
          {previewing ? `Viewing as ${VIEW_AS_LABEL[viewAs]}` : 'View as'}
        </span>
        <div
          role="group"
          aria-label="Preview access level"
          className="flex flex-wrap items-center gap-1"
        >
          <button
            type="button"
            onClick={() => choose(null)}
            aria-pressed={!previewing}
            className={`rounded-full px-2 py-0.5 transition-colors ${
              !previewing
                ? 'bg-white text-gray-900 font-semibold'
                : 'bg-amber-400/60 hover:bg-amber-400'
            }`}
          >
            Admin (you)
          </button>
          {VIEW_AS_LEVELS.map((level) => (
            <button
              key={level}
              type="button"
              onClick={() => choose(level)}
              aria-pressed={viewAs === level}
              className={`rounded-full px-2 py-0.5 transition-colors ${
                viewAs === level
                  ? 'bg-white text-gray-900 font-semibold'
                  : previewing
                    ? 'bg-amber-400/60 hover:bg-amber-400'
                    : 'bg-white/70 hover:bg-white border border-gray-200'
              }`}
            >
              {VIEW_AS_LABEL[level]}
            </button>
          ))}
        </div>
        {previewing && (
          <span className="ml-auto opacity-90">
            Preview only — your real access is unchanged.
          </span>
        )}
      </div>
    </div>
  )
}
