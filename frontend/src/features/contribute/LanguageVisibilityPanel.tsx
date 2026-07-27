import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import { setLanguageVisibility } from '../../api/contribute'
import CircleFlag from '../../components/CircleFlag'
import { usePrefsStore } from '../../stores/prefsStore'

/** Admin control (owner): which languages show up in onboarding and the
 * language picker. Hiding a language never touches its content or access —
 * clicking its name jumps the admin's active language there directly (the
 * shared picker filters hidden languages out, so this is the way in). */
export default function LanguageVisibilityPanel() {
  const qc = useQueryClient()
  const setActiveLanguageId = usePrefsStore((s) => s.setActiveLanguageId)
  const { data: languages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
  })

  const mutation = useMutation({
    mutationFn: ({ id, visible }: { id: string; visible: boolean }) =>
      setLanguageVisibility(id, visible),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['languages'] }),
  })

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
        {languages.map((lang) => (
          <div key={lang.id} className="flex items-center justify-between gap-3 py-2">
            <button
              type="button"
              onClick={() => setActiveLanguageId(lang.id)}
              className="flex items-center gap-2 text-left hover:underline"
              title={`Switch to ${lang.name}`}
            >
              <CircleFlag code={lang.code} size={18} />
              <span className="text-gray-800">{lang.name}</span>
            </button>
            <label className="flex items-center gap-2 text-xs text-gray-500">
              {lang.is_visible ? 'Visible' : 'Hidden'}
              <input
                type="checkbox"
                checked={lang.is_visible}
                onChange={(e) =>
                  mutation.mutate({ id: lang.id, visible: e.target.checked })
                }
                aria-label={`${lang.name} visible to learners`}
                className="rounded border-gray-300"
              />
            </label>
          </div>
        ))}
      </div>
      {mutation.isError && (
        <p className="text-xs text-red-500">Could not save.</p>
      )}
    </div>
  )
}
