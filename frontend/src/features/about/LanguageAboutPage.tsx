import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getLanguages } from '../../api/profile'
import { usePrefsStore } from '../../stores/prefsStore'
import {
  factsFor,
  flagsFor,
  syntaxFor,
  type SyntaxExample,
} from './languageFacts'

/** An interlinear example: each word stacked over its gloss, then the natural
 * translation. Shows how the word order actually works, not just names it. */
function GlossedExample({ example }: { example: SyntaxExample }) {
  return (
    <div className="rounded-xl bg-gray-50 border border-gray-100 p-3">
      <div
        className="flex flex-wrap gap-x-4 gap-y-2"
        dir={example.rtl ? 'rtl' : 'ltr'}
      >
        {example.words.map((word, i) => (
          <div key={i} className="flex flex-col">
            <span className="text-sm text-gray-900">{word.w}</span>
            <span className="text-[11px] text-gray-400">{word.g}</span>
          </div>
        ))}
      </div>
      <p className="mt-2 text-sm text-gray-700">
        <span aria-hidden className="text-gray-400">→ </span>
        {example.translation}
      </p>
      {example.note && (
        <p className="mt-1 text-xs text-gray-500">{example.note}</p>
      )}
    </div>
  )
}

/**
 * "Things to know about this language" — a one-minute orientation to the active
 * language: its family, reach, writing system, word order, a short history, and
 * what makes it distinctive. Same card style as Letters & Sounds.
 */
export default function LanguageAboutPage() {
  const navigate = useNavigate()
  // Live active language from prefs (the cached profile query lagged switches).
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })

  const language = languages.find((l) => l.id === activeLanguageId)
  const facts = factsFor(language?.code)
  const flags = flagsFor(language?.code)
  const syntax = syntaxFor(language?.code)
  const name = language?.name ?? 'this language'

  const rows: { label: string; value: string }[] = facts
    ? [
        { label: 'Language family', value: facts.family },
        { label: 'Speakers', value: facts.speakers },
        { label: 'Where it’s spoken', value: facts.whereSpoken },
        { label: 'Writing system', value: facts.writingSystem },
      ]
    : []

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        <div className="flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-sm text-gray-500 hover:text-lang"
          >
            ← Dashboard
          </button>
          <h1 className="text-lg font-bold text-gray-900">Things to know</h1>
        </div>

        {!facts && (
          <p className="text-sm text-gray-500">
            No language guide for {name} yet.
          </p>
        )}

        {facts && (
          <>
            {/* Title + one-line hook, with representative flags */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
              <div className="flex items-start justify-between gap-3">
                <h2 className="text-2xl font-bold text-gray-900">{name}</h2>
                {flags && (
                  <span
                    className="text-xl leading-none shrink-0"
                    aria-label="Where it’s spoken"
                    title="Where it’s spoken"
                  >
                    {flags}
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-gray-600">{facts.tagline}</p>
            </div>

            {/* At-a-glance facts */}
            <section
              className="bg-white rounded-2xl border border-gray-100 shadow-sm divide-y divide-gray-50"
              data-testid="about-facts"
            >
              {rows.map((row) => (
                <div
                  key={row.label}
                  className="p-4 flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-4"
                >
                  <span className="shrink-0 sm:w-40 text-xs uppercase tracking-wide text-gray-400">
                    {row.label}
                  </span>
                  <span className="text-sm text-gray-700">{row.value}</span>
                </div>
              ))}
            </section>

            {/* How sentences are built — word order + a glossed example */}
            <section
              className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4"
              data-testid="about-syntax"
            >
              <h3 className="text-xs uppercase tracking-wide text-gray-400 mb-2">
                How sentences are built
              </h3>
              <p className="text-sm text-gray-700 leading-relaxed">
                {facts.wordOrder}
              </p>
              {syntax.length > 0 && (
                <div className="mt-3 space-y-3">
                  {syntax.map((example) => (
                    <GlossedExample key={example.sentence} example={example} />
                  ))}
                </div>
              )}
            </section>

            {/* History */}
            <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
              <h3 className="text-xs uppercase tracking-wide text-gray-400 mb-2">
                A short history
              </h3>
              <p className="text-sm text-gray-700 leading-relaxed">{facts.history}</p>
            </section>

            {/* What makes it unique */}
            <section className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
              <h3 className="text-xs uppercase tracking-wide text-gray-400 mb-2">
                What makes it unique
              </h3>
              <ul className="space-y-2">
                {facts.unique.map((point) => (
                  <li key={point} className="flex gap-2 text-sm text-gray-700">
                    <span aria-hidden className="mt-0.5 text-lang">◆</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}
      </div>
    </div>
  )
}
