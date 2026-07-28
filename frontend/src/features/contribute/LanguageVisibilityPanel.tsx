import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import { getLanguageReadiness, setLanguageVisibility } from '../../api/contribute'
import CircleFlag from '../../components/CircleFlag'
import { usePrefsStore } from '../../stores/prefsStore'

/** Admin control (owner): which languages show up in onboarding and the
 * language picker. Hiding a language never touches its content or access —
 * clicking its name jumps the admin's active language there directly (the
 * shared picker filters hidden languages out, so this is the way in).
 *
 * Visibility IS the release switch ("languages will need to be released
 * after review"), so each row also carries its review backlog and going
 * live with unreviewed content asks first. Admin-only, enforced server-side
 * — a reviewer calling the endpoint gets a 403. */
export default function LanguageVisibilityPanel() {
  const qc = useQueryClient()
  const setActiveLanguageId = usePrefsStore((s) => s.setActiveLanguageId)
  const { data: languages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
  })
  // Readiness is advisory: if the call fails (or the caller somehow isn't
  // an admin) the panel still works, just without the backlog badges.
  const { data: readiness = [] } = useQuery({
    queryKey: ['language-readiness'],
    queryFn: getLanguageReadiness,
    retry: false,
  })
  const readinessById = new Map(readiness.map((r) => [r.id, r]))

  const mutation = useMutation({
    mutationFn: ({ id, visible }: { id: string; visible: boolean }) =>
      setLanguageVisibility(id, visible),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['languages'] })
      qc.invalidateQueries({ queryKey: ['language-readiness'] })
    },
  })

  /** Releasing (hidden → visible) with unreviewed content is the mistake
   * this panel exists to prevent, so it asks. Un-releasing never asks. */
  const requestChange = (id: string, name: string, visible: boolean) => {
    const r = readinessById.get(id)
    if (visible && r && r.awaiting_review > 0) {
      const ok = window.confirm(
        `${name} still has ${r.awaiting_review} item${r.awaiting_review === 1 ? '' : 's'} awaiting review ` +
          `(${r.draft_points} draft grammar point${r.draft_points === 1 ? '' : 's'}, ` +
          `${r.pending_drills} drill${r.pending_drills === 1 ? '' : 's'}, ` +
          `${r.pending_examples} example sentence${r.pending_examples === 1 ? '' : 's'}).\n\n` +
          'Release it to learners anyway?',
      )
      if (!ok) return
    }
    mutation.mutate({ id, visible })
  }

  if (languages.length === 0) return null

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm space-y-3"
      data-testid="language-visibility-panel"
    >
      <div>
        <h2 className="text-sm font-semibold text-gray-800">Language visibility</h2>
        <p className="text-xs text-gray-500">
          Hidden languages stay out of onboarding and the language picker for
          everyone else — nothing is deleted. Click a name to switch your own
          active language there, hidden or not.
        </p>
      </div>
      <div className="divide-y divide-gray-100">
        {languages.map((lang) => {
          const r = readinessById.get(lang.id)
          return (
            <div key={lang.id} className="flex items-center justify-between gap-3 py-2">
              <button
                type="button"
                onClick={() => setActiveLanguageId(lang.id)}
                className="flex items-center gap-2 text-left hover:underline min-w-0"
                title={`Switch to ${lang.name}`}
              >
                <CircleFlag code={lang.code} size={18} />
                <span className="text-gray-800 truncate">{lang.name}</span>
              </button>
              <div className="flex items-center gap-3 shrink-0">
                {r && r.awaiting_review > 0 && (
                  <span
                    className="text-[10px] rounded px-1.5 py-0.5 bg-amber-50 text-amber-700"
                    title={`${r.draft_points} draft grammar points · ${r.pending_drills} drills · ${r.pending_examples} example sentences awaiting review`}
                  >
                    {r.awaiting_review} to review
                  </span>
                )}
                {r && r.awaiting_review === 0 && (
                  <span className="text-[10px] rounded px-1.5 py-0.5 bg-emerald-50 text-emerald-700">
                    Reviewed
                  </span>
                )}
                {r && r.open_reports > 0 && (
                  <span
                    className="text-[10px] text-gray-400"
                    title="Open notes, change requests and learner feedback"
                  >
                    {r.open_reports} open
                  </span>
                )}
                <label className="flex items-center gap-2 text-xs text-gray-500">
                  {lang.is_visible ? 'Visible' : 'Hidden'}
                  <input
                    type="checkbox"
                    checked={lang.is_visible}
                    onChange={(e) =>
                      requestChange(lang.id, lang.name, e.target.checked)
                    }
                    aria-label={`${lang.name} visible to learners`}
                    className="rounded border-gray-300"
                  />
                </label>
              </div>
            </div>
          )
        })}
      </div>
      {mutation.isError && (
        <p className="text-xs text-red-500">Could not save.</p>
      )}
    </div>
  )
}
