import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Headphones } from 'lucide-react'
import LanguageWrapper from '../../components/LanguageWrapper'
import { useTranslit } from '../keyboards/useTranslit'
import { backspaceUnit, convertTranslit, translitGuide } from '../keyboards/translit'

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
  /** Listening mode (WP19a): hide the sentence — the learner types the
   * missing word from the AUDIO, and the text reveals after grading. */
  hideSentence?: boolean
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
  const { t } = useTranslation()
  return (
    <div className="mt-3 text-xs">
      <div className="flex items-center justify-center gap-3 text-gray-500">
        <button
          type="button"
          onClick={onToggle}
          aria-pressed={enabled}
          title={t('review.qwertyTitle')}
          className={`rounded-full px-2 py-0.5 border transition ${
            enabled
              ? 'border-lang/30 bg-lang-soft text-lang'
              : 'border-gray-200 text-gray-500 hover:text-gray-600'
          }`}
        >
          {enabled ? t('review.qwertyOn') : t('review.qwertyOff')}
        </button>
        {enabled && (
          <button
            type="button"
            onClick={() => setShowGuide((v) => !v)}
            aria-expanded={showGuide}
            className="text-lang hover:underline"
          >
            {showGuide ? t('review.hideKeyGuide') : t('review.keyGuide')}
          </button>
        )}
      </div>
      {enabled && showGuide && (
        <div
          className="mt-2 mx-auto max-w-sm rounded-xl border border-gray-100 bg-gray-50 p-3 text-start"
          data-testid="translit-guide"
        >
          <table className="w-full text-xs">
            <tbody>
              {translitGuide(languageCode).map((row) => (
                <tr key={row.keys} className="align-top">
                  <td className="pe-3 py-0.5 font-mono text-gray-600 whitespace-nowrap">
                    {row.keys}
                  </td>
                  <td className="py-0.5 text-gray-900">{row.out}</td>
                  <td className="ps-2 py-0.5 text-gray-500">{row.note ?? ''}</td>
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
  hideSentence = false,
}: DrillCardProps) {
  const { t } = useTranslation()
  const translit = useTranslit(languageCode)
  const hasMarker = sentence.includes('{{answer}}')
  const inputTone = (result && RESULT_INPUT_STYLES[result]) ||
    'border-lang/50 focus:border-lang'


  // Resolve direction: languageCode takes precedence, fall back to legacy dir prop
  const resolvedDir =
    languageCode === 'ar' || languageCode === 'he' || languageCode === 'fa'
      ? 'rtl'
      : dir ?? 'ltr'

  const handleChange = (raw: string) => {
    onChange(translit.enabled ? convertTranslit(languageCode, raw) : raw)
  }

  // Two submit paths on purpose. Physical keyboards fire keydown Enter;
  // some Android IMEs never do (keyCode 229 / "Unidentified"), but the
  // soft keyboard's action key ALWAYS triggers implicit form submission —
  // so each mode wraps its input in a <form>. preventDefault in keydown
  // stops the two paths double-firing on desktop.
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.nativeEvent.isComposing && !disabled) {
      e.preventDefault()
      onSubmit()
    }
    // Backspace on a composed Hangul syllable peels ONE jamo (한 → 하), the
    // way a real IME behaves — native delete vaporizes the whole
    // three-keystroke block, which made every typo cost a full syllable.
    if (e.key === 'Backspace' && !e.nativeEvent.isComposing && !disabled) {
      const input = e.currentTarget
      const start = input.selectionStart ?? value.length
      const end = input.selectionEnd ?? value.length
      const peeled = backspaceUnit(languageCode, value, start, end)
      if (peeled) {
        e.preventDefault()
        onChange(peeled.text)
        requestAnimationFrame(() => {
          input.setSelectionRange(peeled.caret, peeled.caret)
        })
      }
    }
  }

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!disabled) onSubmit()
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
      <form
        onSubmit={handleFormSubmit}
        className="flex flex-col items-center gap-6"
      >
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
            enterKeyHint="go"
            value={value}
            onChange={(e) => handleChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={t('review.typeTheWord')}
            className={`min-w-[200px] border-b-2 ${inputTone} outline-none text-xl text-center py-1 bg-transparent text-base touch-manipulation`}
            style={{ minHeight: '44px' }}
            dir={resolvedDir}
          />
          {controls}
        </div>
      </form>
    )
  }

  // Fill-in-the-blank mode: split at {{answer}} marker.
  //
  // The blank is an INLINE input, so its height decides where the underline
  // lands relative to the sentence. A flat `min-height: 44px` — the mobile
  // touch-target rule, correct on the standalone inputs above — makes the
  // box taller than the 40px line it sits in, and because inline boxes align
  // on the BASELINE the surplus hangs underneath: the bar drew ~16px below
  // its own words, floating in the gap before the next line. On a phone the
  // column is narrow and it reads as part of the flow; on a desktop column
  // the sentence wraps and the bar visibly detaches from the blank it
  // belongs to. Reported as "the typing bars are sometimes hidden".
  //
  // So the touch target is applied only where a finger is actually used.
  // With a fine pointer the box is its natural 30px and the underline sits
  // where a handwritten blank would. (`text-base` came off at the same time:
  // it was on the same element as `text-xl`, which wins by stylesheet order,
  // so it changed nothing and only obscured which size was in force.)
  const parts = sentence.split('{{answer}}')
  const before = parts[0]
  const after = parts.slice(1).join('{{answer}}')

  if (hideSentence) {
    // Listening mode: ears only — but the SHAPE of the sentence stays
    // visible (beta report: with the words hidden and the audio gapped,
    // nothing showed where the missing word even falls). Every word is
    // masked; the blank glows in place.
    const mask = (part: string) =>
      part.trim().split(/\s+/).filter(Boolean).map(() => '▬▬')
    const beforeMasks = mask(before)
    const afterMasks = mask(after)
    return (
      <form
        onSubmit={handleFormSubmit}
        className="flex flex-col items-center gap-4"
        data-testid="listening-drill"
      >
        <p className="text-sm text-gray-500 text-center">
          <Headphones aria-hidden className="me-1 inline h-4 w-4 align-[-2px]" />{t('review.listenPause')}
        </p>
        <p
          className="text-lg text-gray-300 text-center tracking-widest select-none"
          aria-hidden
          data-testid="listening-skeleton"
        >
          {beforeMasks.join(' ')}
          {beforeMasks.length > 0 && ' '}
          <span className="text-lang font-bold">___</span>
          {afterMasks.length > 0 && ' '}
          {afterMasks.join(' ')}
        </p>
        <input
          ref={inputRef}
          type="text"
          autoFocus
          autoCapitalize="none"
          autoCorrect="off"
          autoComplete="off"
          spellCheck={false}
          enterKeyHint="go"
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          className={`min-w-[200px] border-b-2 ${inputTone} outline-none text-xl text-center py-1 bg-transparent text-base touch-manipulation`}
          style={{ minHeight: '44px' }}
          dir={resolvedDir}
        />
        {controls}
      </form>
    )
  }

  return (
    <form onSubmit={handleFormSubmit}>
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
            enterKeyHint="go"
            value={value}
            onChange={(e) => handleChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            className={`inline-block min-w-[120px] border-b-2 ${inputTone} outline-none text-xl text-center mx-1 py-0 bg-transparent touch-manipulation pointer-coarse:min-h-[44px]`}
            dir={resolvedDir}
          />
          {after}
        </p>
      </LanguageWrapper>
      {controls}
    </form>
  )
}
