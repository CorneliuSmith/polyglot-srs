import LanguageWrapper from './LanguageWrapper'

interface Chip {
  label: string
  value: string
}

interface Chart {
  title: string
  columns?: string[]
  rows: string[][]
}

/**
 * Language-shaped word forms (§3b): chips carry the facts a learner of THIS
 * language needs at a glance (gender, aspect + pair, verb form, plural,
 * noun class…) and charts carry the tables (conjugations, declensions).
 * Both structures are built per-language by the morphology pipeline —
 * this component just renders whatever the language decided matters.
 */
export default function FormsPanel({
  morphology,
  languageCode,
}: {
  morphology: Record<string, unknown> | string | null
  languageCode: string
}) {
  let m: Record<string, unknown> | null = null
  if (typeof morphology === 'string') {
    try {
      m = JSON.parse(morphology)
    } catch {
      m = null
    }
  } else {
    m = morphology
  }
  const chips = (m?.chips as Chip[] | undefined) ?? []
  const charts = (m?.charts as Chart[] | undefined) ?? []
  if (chips.length === 0 && charts.length === 0) return null

  return (
    <div data-testid="forms-panel">
      <h3 className="font-semibold text-gray-700 mb-1">Forms</h3>
      {chips.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {chips.map((c, i) => (
            <span
              key={i}
              className="inline-flex items-baseline gap-1 rounded-full bg-lang-soft px-2 py-0.5 text-xs"
            >
              <span className="text-gray-500">{c.label}</span>
              <LanguageWrapper languageCode={languageCode}>
                <span className="font-medium text-lang-dark">{c.value}</span>
              </LanguageWrapper>
            </span>
          ))}
        </div>
      )}
      {charts.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {charts.map((chart, i) => (
            <table
              key={i}
              className="w-full text-sm border border-gray-100 rounded-lg overflow-hidden"
            >
              <thead>
                <tr className="bg-lang-soft">
                  <th
                    colSpan={chart.columns?.length ?? 2}
                    className="text-left px-2 py-1 text-xs uppercase tracking-wide text-lang-dark"
                  >
                    {chart.title}
                  </th>
                </tr>
                {chart.columns && (
                  <tr className="text-xs text-gray-400">
                    {chart.columns.map((col, j) => (
                      <th key={j} className="text-left px-2 py-0.5 font-normal">
                        {col}
                      </th>
                    ))}
                  </tr>
                )}
              </thead>
              <tbody>
                {chart.rows.map((row, j) => (
                  <tr key={j} className="odd:bg-gray-50">
                    {row.map((cell, k) => (
                      <td
                        key={k}
                        className={
                          k === 0
                            ? 'px-2 py-1 text-gray-500 whitespace-nowrap'
                            : 'px-2 py-1 text-gray-800'
                        }
                      >
                        {k === 0 ? (
                          cell
                        ) : (
                          <LanguageWrapper languageCode={languageCode}>
                            <span>{cell}</span>
                          </LanguageWrapper>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          ))}
        </div>
      )}
    </div>
  )
}
