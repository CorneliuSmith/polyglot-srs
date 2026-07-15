import { useState } from 'react'
import LanguageWrapper from '../../components/LanguageWrapper'
import { useTranslit } from '../keyboards/useTranslit'
import { convertTranslit, translitGuide } from '../keyboards/translit'

interface DrillCardProps {
  sentence: string
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  disabled: boolean
  languageCode?: string
  /** @deprecated use languageCode instead; kept for backward compat */
  dir?: 'ltr' | 'rtl'
  inputRef?: React.RefObject<HTMLInputElement | null>
  /** After grading: colors the blank green/amber/red in place. */
  result?: string | null
}

// The graded answer stays visible IN the blank: green = right,
// amber = right but sloppy (diacritics/spelling), red = wrong.
const RESULT_INPUT_STYLES: Record<string, string> = {
  correct: 'border-green-500 text-green-700',
  correct_sloppy: 'border-amber-400 text-amber-600',
  wrong_form: 'border-red-400 text-red-600',
  wrong: 'border-red-400 text-red-600',
}

/** QWERTY-transliteration toggle + key guide under the answer blank. */
function TranslitControls({
  languageCode,
  enabled,
  onToggle,
}: {
  languageCode: string
  enabled: boolean
  onToggle: () => void
}) {
  const [showGuide, setShowGuide] = useState(false)
  return (
    <div className="mt-3 text-xs">
      <div className="flex items-center justify-center gap-3 text-gray-400">
        <button
          type="button"
          onClick={onToggle}
          aria-pressed={enabled}
          title="Type Latin letters and they convert to the target script"
          className={`rounded-full px-2 py-0.5 border transition ${
            enabled
              ? 'border-lang/30 bg-lang-soft text-lang'
              : 'border-gray-200 text-gray-400 hover:text-gray-600'
          }`}
        >
          QWERTY {enabled ? 'on' : 'off'}
        </button>
        {enabled && (
          <button
            type="button"
            onClick={() => setShowGuide((v) => !v)}
            aria-expanded={showGuide}
            className="text-lang hover:underline"
          >
            {showGuide ? 'Hide key guide' : 'Key guide'}
          </button>
        )}
      </div>
      {enabled && showGuide && (
        <div
          className="mt-2 mx-auto max-w-sm rounded-xl border border-gray-100 bg-gray-50 p-3 text-left"
          data-testid="translit-guide"
        >
          <table className="w-full text-xs">
            <tbody>
              {translitGuide(languageCode).map((row) => (
                <tr key={row.keys} className="align-top">
                  <td className="pr-3 py-0.5 font-mono text-gray-600 whitespace-nowrap">
                    {row.keys}
                  </td>
                  <td className="py-0.5 text-gray-900">{row.out}</td>
                  <td className="pl-2 py-0.5 text-gray-400">{row.note ?? ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default function DrillCard({
  sentence,
  value,
  onChange,
  onSubmit,
  disabled,
  languageCode = 'en',
  dir,
  inputRef,
  result,
}: DrillCardProps) {
  const translit = useTranslit(languageCode)
  const hasMarker = sentence.includes('{{answer}}')
  const inputTone = (result && RESULT_INPUT_STYLES[result]) ||
    'border-lang/50 focus:border-lang'


  // Resolve direction: languageCode takes precedence, fall back to legacy dir prop
  const resolvedDir = languageCode === 'ar' ? 'rtl' : dir ?? 'ltr'

  const handleChange = (raw: string) => {
    onChange(translit.enabled ? convertTranslit(languageCode, raw) : raw)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !disabled) {
      onSubmit()
    }
  }

  const controls = translit.supported ? (
    <TranslitControls
      languageCode={languageCode}
      enabled={translit.enabled}
      onToggle={translit.toggle}
    />
  ) : null

  if (!hasMarker) {
    // Type-the-word mode: sentence is the definition/prompt, user types the word
    return (
      <div className="flex flex-col items-center gap-6">
        <LanguageWrapper languageCode={languageCode}>
          <p className="text-xl leading-loose text-center text-gray-700">
            {sentence}
          </p>
        </LanguageWrapper>
        <div className="flex flex-col items-center">
          <input
            ref={inputRef}
            type="text"
            autoFocus
            autoCapitalize="none"
            autoCorrect="off"
            autoComplete="off"
            spellCheck={false}
            value={value}
            onChange={(e) => handleChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Type the word…"
            className={`min-w-[200px] border-b-2 ${inputTone} outline-none text-xl text-center py-1 bg-transparent text-base touch-manipulation`}
            style={{ minHeight: '44px' }}
            dir={resolvedDir}
          />
          {controls}
        </div>
      </div>
    )
  }

  // Fill-in-the-blank mode: split at {{answer}} marker
  const parts = sentence.split('{{answer}}')
  const before = parts[0]
  const after = parts.slice(1).join('{{answer}}')

  return (
    <div>
      <LanguageWrapper languageCode={languageCode}>
        <p className="text-xl leading-loose text-center">
          {before}
          <input
            ref={inputRef}
            type="text"
            autoFocus
            autoCapitalize="none"
            autoCorrect="off"
            autoComplete="off"
            spellCheck={false}
            value={value}
            onChange={(e) => handleChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            className={`inline-block min-w-[120px] border-b-2 ${inputTone} outline-none text-xl text-center mx-1 py-0 bg-transparent text-base touch-manipulation`}
            style={{ minHeight: '44px' }}
            dir={resolvedDir}
          />
          {after}
        </p>
      </LanguageWrapper>
      {controls}
    </div>
  )
}
