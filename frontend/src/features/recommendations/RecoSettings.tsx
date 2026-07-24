import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usePrefsStore } from '../../stores/prefsStore'
import {
  getRecoProfile,
  getRecommendations,
  updateRecoProfile,
  MEDIA_TYPE_LABELS,
} from '../../api/recommendations'

const GENRES = [
  'Fiction', 'Non-fiction', 'Sci-fi & fantasy', 'Mystery & thriller',
  'Romance', 'History', 'Comedy', 'Drama', 'Documentary',
  'News & current affairs', 'Science & tech', 'True crime',
  'Sports', 'Kids & family', 'Music', 'Travel & food',
]
const MEDIA = ['book', 'film', 'series', 'podcast']

/**
 * Recommendations settings: the on/off switch plus the interest profile used to
 * personalize the weekly picks. Lives as a section on the Settings page. Lets a
 * learner configure it whether or not they're currently tutor+ (the picks
 * themselves need tutor+; a note says so).
 */
export default function RecoSettings() {
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const queryClient = useQueryClient()

  const { data: profile } = useQuery({
    queryKey: ['reco-profile'],
    queryFn: getRecoProfile,
  })
  const { data: state } = useQuery({
    queryKey: ['recommendations', activeLanguageId],
    queryFn: () => getRecommendations(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
  })

  const [enabled, setEnabled] = useState(false)
  const [about, setAbout] = useState('')
  const [genres, setGenres] = useState<string[]>([])
  const [mediaTypes, setMediaTypes] = useState<string[]>([])
  const [dirty, setDirty] = useState(false)

  // Seed the form once the saved profile loads.
  useEffect(() => {
    if (profile && !dirty) {
      setEnabled(profile.enabled)
      setAbout(profile.about)
      setGenres(profile.genres)
      setMediaTypes(profile.media_types)
    }
  }, [profile, dirty])

  const save = useMutation({
    mutationFn: () =>
      updateRecoProfile({ enabled, about, genres, media_types: mediaTypes }),
    onSuccess: () => {
      setDirty(false)
      queryClient.invalidateQueries({ queryKey: ['reco-profile'] })
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
    },
  })

  const touch = () => setDirty(true)
  const toggleIn = (list: string[], v: string) =>
    list.includes(v) ? list.filter((x) => x !== v) : [...list, v]

  return (
    <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-semibold text-gray-800">Recommendations</h2>
          <p className="text-xs text-gray-500">
            Get the occasional book, film, series, or podcast in your target
            language — picked for your level and interests, about once a week.
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          aria-label="Recommendations"
          onClick={() => { setEnabled((v) => !v); touch() }}
          className={
            'relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors ' +
            (enabled ? 'bg-lang' : 'bg-gray-300')
          }
        >
          <span
            className={
              'inline-block h-5 w-5 transform rounded-full bg-white transition-transform ' +
              (enabled ? 'translate-x-5' : 'translate-x-1')
            }
          />
        </button>
      </div>

      {state && !state.entitled && (
        <p className="text-xs text-amber-600">
          Receiving picks needs a tutor+ subscription for this language — you can
          still set up your profile now.
        </p>
      )}

      {enabled && (
        <div className="space-y-4 pt-1">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              About you
            </label>
            <textarea
              value={about}
              onChange={(e) => { setAbout(e.target.value); touch() }}
              maxLength={1000}
              rows={3}
              placeholder="What do you like to read and watch? Hobbies, favourite authors or shows, topics you love…"
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-lang focus:outline-none"
            />
            <p className="mt-1 text-[11px] text-gray-400">
              The more you share, the better the picks.
            </p>
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Genres</p>
            <div className="flex flex-wrap gap-2">
              {GENRES.map((g) => {
                const on = genres.includes(g)
                return (
                  <button
                    key={g}
                    type="button"
                    aria-pressed={on}
                    onClick={() => { setGenres((l) => toggleIn(l, g)); touch() }}
                    className={
                      'rounded-full border px-3 py-1 text-xs transition-colors ' +
                      (on
                        ? 'border-lang bg-lang-soft text-lang-dark'
                        : 'border-gray-200 text-gray-600 hover:border-lang/50')
                    }
                  >
                    {g}
                  </button>
                )
              })}
            </div>
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">
              What to recommend
            </p>
            <div className="flex flex-wrap gap-2">
              {MEDIA.map((m) => {
                const on = mediaTypes.includes(m)
                return (
                  <button
                    key={m}
                    type="button"
                    aria-pressed={on}
                    onClick={() => { setMediaTypes((l) => toggleIn(l, m)); touch() }}
                    className={
                      'rounded-full border px-3 py-1 text-xs transition-colors ' +
                      (on
                        ? 'border-lang bg-lang-soft text-lang-dark'
                        : 'border-gray-200 text-gray-600 hover:border-lang/50')
                    }
                  >
                    {MEDIA_TYPE_LABELS[m]}
                  </button>
                )
              })}
            </div>
            <p className="mt-1 text-[11px] text-gray-400">
              Leave all off to let us pick across everything.
            </p>
          </div>
        </div>
      )}

      {dirty && (
        <div className="flex items-center gap-3 pt-1">
          <button
            type="button"
            onClick={() => save.mutate()}
            disabled={save.isPending}
            className="bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-xl px-4 py-2 text-sm"
          >
            {save.isPending ? 'Saving…' : 'Save'}
          </button>
          {save.isError && (
            <span className="text-xs text-amber-600">Couldn’t save — try again.</span>
          )}
        </div>
      )}
    </section>
  )
}
