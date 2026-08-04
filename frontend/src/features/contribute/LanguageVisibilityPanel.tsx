import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import {
  getLanguageReadiness,
  setLanguageAutoTranslate,
  setLanguageVisibility,
} from '../../api/contribute'
import CircleFlag from '../../components/CircleFlag'
import { usePrefsStore } from '../../stores/prefsStore'
import TranslationStatusPanel from './TranslationStatusPanel'

/** Same idiom as RolesPanel: surface the server's detail when there is one —
 * here that's the 503 naming the not-yet-applied migration. */
function extractDetail(err: unknown): string | undefined {
  return (err as { response?: { data?: { detail?: string } } })?.response?.data
    ?.detail
}

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

  // Separate mutation so a failure here ("Could not save") can't be confused
  // with a visibility failure, and so its error surfaces the server detail —
  // the useful case is the 503 naming the missing migration.
  const autoTranslateMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      setLanguageAutoTranslate(id, enabled),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['languages'] })
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
          active language there, hidden or not. Auto-translate fills missing
          translations in learners&apos; own languages for that course — only
          for language pairs real accounts use, with rejects going to the
          review queue.
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
                className="flex items-center gap-2 text-start hover:underline min-w-0"
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
                <label
                  className="flex items-center gap-2 text-xs text-gray-500"
                  title="Fill missing translations in learners' own languages automatically — only for language pairs real accounts use. Rejected translations go to the review queue, and it never draws on a learner's usage allowance."
                >
                  Auto-translate
                  <input
                    type="checkbox"
                    checked={lang.auto_translate_enabled ?? false}
                    onChange={(e) =>
                      autoTranslateMutation.mutate({
                        id: lang.id,
                        enabled: e.target.checked,
                      })
                    }
                    aria-label={`${lang.name} automatic translation`}
                    className="rounded border-gray-300"
                  />
                </label>
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
      {autoTranslateMutation.isError && (
        <p className="text-xs text-red-500">
          {extractDetail(autoTranslateMutation.error) ??
            'Could not change auto-translate.'}
        </p>
      )}
      <div className="pt-3 mt-1 border-t border-gray-100">
        <p className="text-xs font-semibold text-gray-700 mb-2">
          Automatic translation status
        </p>
        <TranslationStatusPanel />
      </div>
    </div>
  )
}
