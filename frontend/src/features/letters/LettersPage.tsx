import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getLanguages } from '../../api/profile'
import { usePrefsStore } from '../../stores/prefsStore'
import SpeakButton from '../../components/SpeakButton'
import LanguageWrapper from '../../components/LanguageWrapper'
import { TTS_LANGUAGES, prefetchTTSMany } from '../../api/audio'
import { lettersFor } from './lettersData'

/**
 * Letters & Sounds (beta request): every letter/character of the active
 * language with its diacritic/vowel variants, an example word to hear it in,
 * and a plain-English description of the sound. Scripts (ru/el/ar/hi) show
 * their full inventories with the QWERTY typing key.
 */

// Positional shaping for joining scripts (Arabic): a zero-width joiner on
// either side makes the font itself draw the start/middle/end form — no
// presentation-form tables needed, and non-joining letters (ا د ر…) simply
// keep their true shapes.
const ZWJ = '\u200D'
const POSITION_SHAPES: { label: string; wrap: (c: string) => string }[] = [
  { label: 'alone', wrap: (c) => c },
  { label: 'start', wrap: (c) => c + ZWJ },
  { label: 'middle', wrap: (c) => ZWJ + c + ZWJ },
  { label: 'end', wrap: (c) => ZWJ + c },
]
export default function LettersPage() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  // The LIVE active language comes from the prefs store (same source the
  // dashboard uses) — the cached profile query lagged a language switch,
  // so Russian/Turkish/Arabic letters leaked into the next language.
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })

  const language = languages.find((l) => l.id === activeLanguageId)
  const code = language?.code
  const letters = lettersFor(code)
  const hasVoice = !!code && TTS_LANGUAGES.has(code)

  // A whole alphabet of speaker buttons is the worst case for pressing play
  // and waiting. Warm them in reading order, so the rows on screen are ready
  // first and the tail arrives while the learner is still on the top of the
  // page. Example words are shared curriculum text, so after the first
  // learner on a language these are all CDN hits.
  useEffect(() => {
    if (!letters || !code || !hasVoice) return
    return prefetchTTSMany(
      code,
      letters.sections.flatMap((s) => s.rows.map((r) => r.example)),
    )
  }, [letters, code, hasVoice])

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-sm text-gray-500 hover:text-lang"
          >
            {t('common.backToDashboard')}
          </button>
          <h1 className="text-lg font-bold text-gray-900">{t('dashboard.lettersTitle')}</h1>
        </div>

        {!letters && (
          <p className="text-sm text-gray-500">{t('letters.noGuide')}</p>
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
                  {section.positions ? (
                    // The four positional shapes, right-to-left like the
                    // script itself: alone · start · middle · end.
                    <span
                      dir="rtl"
                      className="flex shrink-0 gap-1"
                      data-testid="letter-positions"
                    >
                      {POSITION_SHAPES.map((shape) => (
                        <span
                          key={shape.label}
                          className="flex flex-col items-center min-w-[2.1rem]"
                        >
                          <LanguageWrapper languageCode={code ?? 'en'}>
                            <span className="text-xl font-semibold text-lang-dark leading-6">
                              {shape.wrap(row.char)}
                            </span>
                          </LanguageWrapper>
                          <span className="text-[9px] text-gray-400">
                            {shape.label}
                          </span>
                        </span>
                      ))}
                    </span>
                  ) : (
                    <LanguageWrapper languageCode={code ?? 'en'}>
                      <span className="block min-w-[3.5rem] text-xl font-semibold text-lang-dark text-center">
                        {row.char}
                        {section.italics && (
                          // The same letter in italics — the shape shift IS
                          // the lesson (т → m-like, и → u-like).
                          <span className="italic ms-2" data-testid="italic-twin">
                            {row.char}
                          </span>
                        )}
                      </span>
                    </LanguageWrapper>
                  )}
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
