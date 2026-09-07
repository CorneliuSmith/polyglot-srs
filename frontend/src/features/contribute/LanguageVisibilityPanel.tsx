import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeftRight, Settings2 } from 'lucide-react'
import { getLanguages } from '../../api/profile'
import {
  getLanguageReadiness,
  setLanguageAutoTranslate,
  setLanguagePolicy,
  setLanguageTutorModel,
  setLanguageVisibility,
  TUTOR_MODELS,
} from '../../api/contribute'
import type { PublishPolicy } from '../../lib/publishPolicy'
import {
  normalizePolicy,
  POLICY_HELP,
  POLICY_LABELS,
  PUBLISH_POLICIES,
} from '../../lib/publishPolicy'
import CircleFlag from '../../components/CircleFlag'
import { chooseActiveLanguage } from '../../lib/activeLanguage'
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
  // Through chooseActiveLanguage, not the bare store setter: the profile is
  // the authority on the study language now, and a device-only switch would
  // be bounced back by the next profile heartbeat.
  const setActiveLanguageId = chooseActiveLanguage
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  // One row's settings drawer open at a time keeps the list readable while
  // cycling; "Edit all settings" opens every drawer for a sweep across the
  // whole catalog in one view.
  const [openRow, setOpenRow] = useState<string | null>(null)
  const [showAll, setShowAll] = useState(false)
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

  // The two dials that used to live only on the active language's
  // ContributorPage controls — reaching them for another course meant
  // switching your own active language there first, once per language.
  const policyMutation = useMutation({
    mutationFn: ({ id, policy }: { id: string; policy: PublishPolicy }) =>
      setLanguagePolicy(id, policy),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['language-readiness'] })
      qc.invalidateQueries({ queryKey: ['grammar'] })
    },
  })
  const tutorModelMutation = useMutation({
    mutationFn: ({ id, model }: { id: string; model: string | null }) =>
      setLanguageTutorModel(id, model),
    onSuccess: () => {
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
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-gray-800">Language visibility</h2>
          <p className="text-xs text-gray-500">
            Hidden languages stay out of onboarding and the language picker for
            everyone else — nothing is deleted. The ⇄ arrow (or the name)
            switches your own active language there, hidden or not — the
            marked row is where you are now. Learners are always served:
            whatever a learner is waiting on translates regardless of the
            toggle, and a course in real recent use gets a starter corpus
            scaled by its active learners. Auto-translate opts the course into
            the <em>full</em> backlog fill on top of that — it works only
            toward the interface languages real learners on the course
            actually use, and goes quiet once the backlog is drained; rejects
            go to the review queue either way.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setShowAll(!showAll)
            setOpenRow(null)
          }}
          className="shrink-0 rounded-lg border border-gray-200 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50"
        >
          {showAll ? 'Collapse all' : 'Edit all settings'}
        </button>
      </div>
      <div className="divide-y divide-gray-100">
        {languages.map((lang) => {
          const r = readinessById.get(lang.id)
          const expanded = showAll || openRow === lang.id
          // With every drawer open at once, a failed save must point at the
          // row it belongs to — not appear under all of them.
          const rowError =
            policyMutation.isError && policyMutation.variables?.id === lang.id
              ? policyMutation.error
              : tutorModelMutation.isError &&
                  tutorModelMutation.variables?.id === lang.id
                ? tutorModelMutation.error
                : null
          return (
            <div key={lang.id} className="py-2">
            {/* The controls are genuinely wider than a phone. They used to
                be `shrink-0` beside a `min-w-0` name, so the name absorbed
                the whole shortfall and collapsed to nothing — every row
                read as a flag and some checkboxes, with no language on it
                — and the row STILL overflowed, pushing the settings icon
                past the card edge. Below `sm` the name takes its own line
                and the controls wrap underneath; from `sm` up the original
                single row comes back. */}
            <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
              <button
                type="button"
                onClick={() => setActiveLanguageId(lang.id)}
                className="flex basis-full items-center gap-2 text-start hover:underline min-w-0 sm:basis-auto sm:flex-1"
                title={`Switch to ${lang.name}`}
              >
                <CircleFlag code={lang.code} size={18} />
                <span className="text-gray-800 truncate">{lang.name}</span>
                {/* The name click was the only way in and nothing marked
                    where you already were — invisible on touch screens,
                    where there is no hover underline and no tooltip. The
                    switch is now an explicit control below; this chip is
                    the feedback that it worked. */}
                {lang.id === activeLanguageId && (
                  <span className="shrink-0 rounded-full bg-lang-soft px-1.5 py-0.5 text-[10px] text-lang-dark">
                    active
                  </span>
                )}
              </button>
              <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1.5">
                {lang.id !== activeLanguageId && (
                  <button
                    type="button"
                    onClick={() => setActiveLanguageId(lang.id)}
                    aria-label={`Switch your active language to ${lang.name}`}
                    title={`Make ${lang.name} your active language (works even while it's hidden)`}
                    className="rounded-md p-1 text-gray-500 hover:text-gray-600"
                  >
                    <ArrowLeftRight aria-hidden className="h-4 w-4" />
                  </button>
                )}
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
                    className="text-[10px] text-gray-500"
                    title="Open notes, change requests and learner feedback"
                  >
                    {r.open_reports} open
                  </span>
                )}
                <label
                  className="flex items-center gap-2 whitespace-nowrap text-xs text-gray-500"
                  title="Opt this course into the FULL backlog fill. Off still serves learners: what they wait on translates on demand, and recent real use buys a usage-scaled starter corpus. Rejects go to the review queue either way; no learner allowance is drawn."
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
                <label className="flex items-center gap-2 whitespace-nowrap text-xs text-gray-500">
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
                <button
                  type="button"
                  onClick={() => setOpenRow(openRow === lang.id ? null : lang.id)}
                  aria-expanded={expanded}
                  aria-label={`${lang.name} settings`}
                  title="Review policy and tutor model"
                  className={`rounded-md p-1 ${
                    expanded
                      ? 'bg-gray-100 text-gray-700'
                      : 'text-gray-500 hover:text-gray-600'
                  }`}
                >
                  <Settings2 aria-hidden className="h-4 w-4" />
                </button>
              </div>
            </div>
            {expanded && !r && (
              <div className="mt-2 ms-6 rounded-lg bg-gray-50 p-3 text-xs text-gray-500">
                Policy and tutor model unavailable — the review status for
                this language hasn't loaded.
              </div>
            )}
            {expanded && r && (
              <div
                className="mt-2 ms-6 space-y-2 rounded-lg bg-gray-50 p-3"
                data-testid={`language-settings-${lang.code}`}
              >
                <label className="block text-xs text-gray-600">
                  <span className="font-medium">Publish policy</span>
                  <select
                    value={normalizePolicy(r.review_policy)}
                    onChange={(e) =>
                      policyMutation.mutate({
                        id: lang.id,
                        policy: e.target.value as PublishPolicy,
                      })
                    }
                    aria-label={`${lang.name} publish policy`}
                    className="mt-1 block w-full rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-xs"
                  >
                    {PUBLISH_POLICIES.map((p) => (
                      <option key={p} value={p}>{POLICY_LABELS[p]}</option>
                    ))}
                  </select>
                  <span className="mt-1 block text-[11px] text-gray-500">
                    {POLICY_HELP[normalizePolicy(r.review_policy)]}
                  </span>
                </label>
                <label className="block text-xs text-gray-600">
                  <span className="font-medium">Tutor model</span>
                  <select
                    value={r.tutor_model ?? ''}
                    onChange={(e) =>
                      tutorModelMutation.mutate({
                        id: lang.id,
                        model: e.target.value || null,
                      })
                    }
                    aria-label={`${lang.name} tutor model`}
                    className="mt-1 block w-full rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-xs"
                  >
                    <option value="">Default (server setting)</option>
                    {TUTOR_MODELS.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </label>
                {rowError != null && (
                  <p className="text-[11px] text-red-500">
                    {extractDetail(rowError) ?? 'Could not save.'}
                  </p>
                )}
              </div>
            )}
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
