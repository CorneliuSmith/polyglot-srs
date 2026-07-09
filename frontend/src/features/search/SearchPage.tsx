import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import { searchContent } from '../../api/curriculum'
import { usePrefsStore } from '../../stores/prefsStore'
import LanguageWrapper from '../../components/LanguageWrapper'

/**
 * In-app search (WP13g): one box over the active language's grammar and
 * vocabulary. Grammar hits deep-link into the path page (which opens the
 * point); vocabulary hits show the word inline.
 */
export default function SearchPage() {
  const navigate = useNavigate()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const [input, setInput] = useState('')
  const [query, setQuery] = useState('')

  // Debounce: fire the search 300ms after the learner stops typing.
  useEffect(() => {
    const t = setTimeout(() => setQuery(input.trim()), 300)
    return () => clearTimeout(t)
  }, [input])

  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })
  const language = languages.find((l) => l.id === activeLanguageId)
  const languageCode = language?.code ?? 'en'

  const { data, isFetching } = useQuery({
    queryKey: ['search', activeLanguageId, query],
    queryFn: () => searchContent(activeLanguageId!, query),
    enabled: !!activeLanguageId && query.length >= 2,
    staleTime: 60 * 1000,
  })

  const empty =
    data && data.grammar.length === 0 && data.vocabulary.length === 0

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">
            Search {language ? `· ${language.name}` : ''}
          </h1>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-sm text-indigo-600 hover:underline"
          >
            ← Dashboard
          </button>
        </div>

        <input
          autoFocus
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Search grammar and vocabulary…"
          aria-label="Search"
          className="w-full rounded-2xl border border-gray-300 bg-white px-4 py-3 text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />

        {query.length > 0 && query.length < 2 && (
          <p className="text-sm text-gray-400">Type at least 2 characters.</p>
        )}
        {isFetching && <p className="text-sm text-gray-400">Searching…</p>}
        {empty && !isFetching && (
          <p className="text-sm text-gray-500">
            No matches for “{query}” in {language?.name ?? 'this language'}.
          </p>
        )}

        {data && data.grammar.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-2">
              Grammar
            </h2>
            <ol className="space-y-2" data-testid="search-grammar">
              {data.grammar.map((hit) => (
                <li key={hit.id}>
                  <button
                    type="button"
                    onClick={() => navigate(`/grammar?point=${hit.id}`)}
                    className="w-full text-left bg-white rounded-xl shadow-sm border border-gray-100 px-4 py-3 flex items-center gap-3 hover:border-indigo-300 transition"
                    style={{ minHeight: '44px' }}
                  >
                    <span className="flex-1">
                      <span className="block text-sm font-semibold text-gray-900">
                        {hit.title}
                      </span>
                      {hit.function_note && (
                        <span className="block text-xs text-gray-500">
                          {hit.function_note}
                        </span>
                      )}
                    </span>
                    {hit.level && (
                      <span className="text-xs text-gray-400">{hit.level}</span>
                    )}
                    {hit.learned && (
                      <span className="text-xs rounded-full px-2 py-0.5 bg-green-50 text-green-700">
                        In reviews ✓
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ol>
          </section>
        )}

        {data && data.vocabulary.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-2">
              Vocabulary
            </h2>
            <ol className="space-y-2" data-testid="search-vocab">
              {data.vocabulary.map((hit) => (
                <li
                  key={hit.id}
                  className="bg-white rounded-xl shadow-sm border border-gray-100 px-4 py-3 flex items-center gap-3"
                >
                  <span className="flex-1">
                    <LanguageWrapper languageCode={languageCode}>
                      <span className="text-sm font-semibold text-gray-900">
                        {hit.word}
                      </span>
                    </LanguageWrapper>
                    <span className="block text-xs text-gray-500">
                      {hit.definition ?? ''}
                      {hit.part_of_speech ? ` · ${hit.part_of_speech}` : ''}
                    </span>
                  </span>
                  {hit.level && (
                    <span className="text-xs text-gray-400">{hit.level}</span>
                  )}
                  {hit.learned && (
                    <span className="text-xs rounded-full px-2 py-0.5 bg-green-50 text-green-700">
                      In reviews ✓
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </section>
        )}
      </div>
    </div>
  )
}
