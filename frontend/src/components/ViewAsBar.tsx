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
 * STICKY, and a single row at every width. The first version laid five chips
 * out in a wrapping flex row in normal document flow: on a phone that took
 * two lines, and it scrolled away the moment a learn session started, so
 * "a toggle at the top of every page" was true only at the top of the page.
 * A native <select> is one line at any width, gets the platform picker on
 * mobile, and is keyboard- and screen-reader-navigable for free.
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
    // The level is part of every role-derived query key (see useViewAsKey),
    // so switching already lands on a different cache entry rather than
    // waiting on a refetch of the old one. This stays as a backstop for any
    // query that derives from roles without saying so in its key.
    queryClient.invalidateQueries()
  }

  const previewing = viewAs !== null

  return (
    <div
      data-testid="view-as-bar"
      // z-40 keeps it under the app's modals (z-50) — a placement prompt or
      // reviewer gate must still cover it.
      className={
        'sticky top-0 z-40 ' +
        (previewing
          ? 'bg-amber-500 text-amber-950 shadow-sm'
          : 'bg-gray-100 text-gray-600 border-b border-gray-200')
      }
    >
      <div className="max-w-3xl mx-auto px-4 py-1.5 flex items-center gap-2 text-xs">
        <label
          htmlFor="view-as-select"
          className="flex shrink-0 items-center gap-1.5 font-medium"
        >
          <Eye aria-hidden className="h-3.5 w-3.5" />
          {previewing ? 'Viewing as' : 'View as'}
        </label>
        <select
          id="view-as-select"
          value={viewAs ?? ''}
          onChange={(e) => choose((e.target.value || null) as ViewAsLevel | null)}
          className={
            'min-w-0 flex-1 rounded-full border px-2 py-1 font-semibold ' +
            (previewing
              ? 'border-amber-700/40 bg-white text-gray-900'
              : 'border-gray-300 bg-white text-gray-800')
          }
        >
          <option value="">Admin (you)</option>
          {VIEW_AS_LEVELS.map((level) => (
            <option key={level} value={level}>
              {VIEW_AS_LABEL[level]}
            </option>
          ))}
        </select>
        {previewing && (
          <button
            type="button"
            onClick={() => choose(null)}
            className="shrink-0 rounded-full bg-amber-950 px-2.5 py-1 font-semibold text-amber-50 hover:bg-amber-900"
          >
            Exit preview
          </button>
        )}
      </div>
      {previewing && (
        <p className="max-w-3xl mx-auto px-4 pb-1 text-[11px] leading-tight opacity-90">
          Preview only — your real access is unchanged.
        </p>
      )}
    </div>
  )
}
