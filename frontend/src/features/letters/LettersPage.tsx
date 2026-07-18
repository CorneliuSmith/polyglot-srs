import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getLanguages, getProfile } from '../../api/profile'
import SpeakButton from '../../components/SpeakButton'
import LanguageWrapper from '../../components/LanguageWrapper'
import { TTS_LANGUAGES } from '../../api/audio'
import { lettersFor } from './lettersData'

/**
 * Letters & Sounds (beta request): every letter/character of the active
 * language with its diacritic/vowel variants, an example word to hear it in,
 * and a plain-English description of the sound. Scripts (ru/el/ar/hi) show
 * their full inventories with the QWERTY typing key.
 */
export default function LettersPage() {
  const navigate = useNavigate()
  const { data: profile } = useQuery({ queryKey: ['profile'], queryFn: getProfile })
  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })

  const language = languages.find((l) => l.id === profile?.active_language_id)
  const code = language?.code
  const letters = lettersFor(code)
  const hasVoice = !!code && TTS_LANGUAGES.has(code)

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-sm text-gray-500 hover:text-lang"
          >
            ← Dashboard
          </button>
          <h1 className="text-lg font-bold text-gray-900">Letters &amp; Sounds</h1>
        </div>

        {!letters && (
          <p className="text-sm text-gray-500">
            No letter guide for this language yet.
          </p>
        )}

        {letters?.intro && (
          <p className="text-sm text-gray-600 bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
            {letters.intro}
          </p>
        )}

        {letters?.sections.map((section) => (
          <section
            key={section.title}
            className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4"
            data-testid="letters-section"
          >
            <h2 className="text-xs uppercase tracking-wide text-gray-400 mb-1">
              {section.title}
            </h2>
            {section.note && (
              <p className="text-xs text-gray-500 mb-2">{section.note}</p>
            )}
            <ul className="divide-y divide-gray-50">
              {section.rows.map((row) => (
                <li key={row.char + row.example} className="py-2 flex items-center gap-3">
                  <LanguageWrapper languageCode={code ?? 'en'}>
                    <span className="block min-w-[3.5rem] text-xl font-semibold text-lang-dark text-center">
                      {row.char}
                    </span>
                  </LanguageWrapper>
                  {row.roman && (
                    <span className="shrink-0 rounded bg-lang-soft px-1.5 py-0.5 text-[10px] font-mono text-lang-dark">
                      {row.roman}
                    </span>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-700">{row.sound}</p>
                    <p className="text-xs text-gray-400">
                      as in <span className="text-gray-600">{row.example}</span>
                    </p>
                  </div>
                  {hasVoice && (
                    <SpeakButton
                      text={row.example}
                      languageCode={code!}
                      label={`Hear ${row.example}`}
                      className="shrink-0 text-lang hover:bg-lang-soft rounded-full p-2"
                    />
                  )}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  )
}
