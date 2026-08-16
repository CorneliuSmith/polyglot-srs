import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import {
  deleteTutorMemoryFact,
  getTutorMemory,
} from '../../api/tutor'
import type { TutorMemoryFact } from '../../api/tutor'

/** Keys are model-written snake_case labels (native_language, motivation…),
 * not catalog entries — prettify, don't translate. */
function factLabel(key: string): string {
  return key.replace(/_/g, ' ')
}

function factValue(value: string | string[]): string {
  return Array.isArray(value) ? value.join(', ') : String(value)
}

function FactRow({
  fact,
  onDelete,
  deleting,
}: {
  fact: TutorMemoryFact
  onDelete: () => void
  deleting: boolean
}) {
  const { t } = useTranslation()
  return (
    <li className="flex items-start justify-between gap-3 py-2">
      <div className="min-w-0">
        <p className="text-sm text-gray-800">
          <span className="font-medium capitalize">{factLabel(fact.key)}</span>
          {': '}
          {factValue(fact.value)}
        </p>
        <span
          className={
            'mt-0.5 inline-block rounded-full px-2 py-0.5 text-[11px] ' +
            (fact.source === 'stated'
              ? 'bg-lang-soft text-lang-dark'
              : 'bg-amber-50 text-amber-700')
          }
        >
          {fact.source === 'stated'
            ? t('settings.memory.stated')
            : t('settings.memory.inferred')}
        </span>
      </div>
      <button
        type="button"
        onClick={onDelete}
        disabled={deleting}
        aria-label={t('settings.memory.forget', { fact: factLabel(fact.key) })}
        title={t('settings.memory.forget', { fact: factLabel(fact.key) })}
        className="shrink-0 rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
      >
        <Trash2 className="h-4 w-4" aria-hidden="true" />
      </button>
    </li>
  )
}

/**
 * "What your tutor remembers" — the learner's window into the durable
 * memory the tutor and its post-session summarizer maintain. Every fact
 * shows its provenance (stated by the learner vs an AI's inference) and
 * can be deleted; the tutor stops seeing it the very next turn. Born from
 * an inferred "native_language: Russian" being presented back to an
 * English speaker as profile truth.
 */
export default function TutorMemoryPanel() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const { data: memory, isError } = useQuery({
    queryKey: ['tutor-memory'],
    queryFn: getTutorMemory,
  })

  const forget = useMutation({
    mutationFn: deleteTutorMemoryFact,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['tutor-memory'] }),
  })

  // A learner who has never used the tutor has nothing here; hide the
  // section rather than explain an empty feature. Errors hide it too —
  // this panel is a window, never a wall.
  if (isError || !memory) return null
  const empty = memory.global.length === 0 && memory.languages.length === 0

  const pendingKey = forget.isPending ? forget.variables?.key : null

  return (
    <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
      <div>
        <h2 className="font-semibold text-gray-800">
          {t('settings.memory.title')}
        </h2>
        <p className="text-xs text-gray-500">{t('settings.memory.desc')}</p>
      </div>

      {empty && (
        <p className="text-sm text-gray-500">{t('settings.memory.empty')}</p>
      )}

      {memory.global.length > 0 && (
        <div>
          <h3 className="text-xs font-medium uppercase tracking-wide text-gray-500">
            {t('settings.memory.global')}
          </h3>
          <ul className="divide-y divide-gray-100">
            {memory.global.map((fact) => (
              <FactRow
                key={fact.key}
                fact={fact}
                deleting={pendingKey === fact.key}
                onDelete={() =>
                  forget.mutate({ scope: 'global', key: fact.key })
                }
              />
            ))}
          </ul>
        </div>
      )}

      {memory.languages.map((lang) => (
        <div key={lang.language_id}>
          <h3 className="text-xs font-medium uppercase tracking-wide text-gray-500">
            {lang.name}
          </h3>
          <ul className="divide-y divide-gray-100">
            {lang.facts.map((fact) => (
              <FactRow
                key={fact.key}
                fact={fact}
                deleting={pendingKey === fact.key}
                onDelete={() =>
                  forget.mutate({
                    scope: 'language',
                    key: fact.key,
                    languageId: lang.language_id,
                  })
                }
              />
            ))}
          </ul>
        </div>
      ))}

      {forget.isError && (
        <p className="text-xs text-amber-600">
          {t('settings.memory.forgetError')}
        </p>
      )}
    </section>
  )
}
