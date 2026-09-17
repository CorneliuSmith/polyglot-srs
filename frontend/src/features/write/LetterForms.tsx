import { useTranslation } from 'react-i18next'
import type { Glyph } from '../../api/strokes'
import LanguageWrapper from '../../components/LanguageWrapper'
import StrokePreview from './StrokePreview'
import { shapedForm } from './LettersMode'

const TATWEEL = 'ـ'

/** How a form is shown in context: the letter joined to a kashida on the
 * joining sides, so an initial reads as the start of a word and a medial
 * as the middle of one. Cased scripts show the case; a cursive hand shows
 * the letter between two vowels, joined. */
function contextOf(script: string, style: string, glyph: string, form: string): string {
  if (script === 'arabic') {
    if (form === 'initial') return glyph + TATWEEL
    if (form === 'medial') return TATWEEL + glyph + TATWEEL
    if (form === 'final') return TATWEEL + glyph
    return glyph
  }
  const g = shapedForm(script, glyph, form)
  if (style === 'cursive' && form === 'lower') {
    const vowel = script === 'cyrillic' ? 'о' : 'o'
    return `${vowel}${g}${vowel}`
  }
  return g
}

/**
 * Every form of one letter, side by side, before the learner focuses on
 * one of them (owner: "show each and every version within the letter so
 * they can see medial, alone, final in context of the letter and then
 * focus on the case"). The letter is set in the same face the strokes
 * were derived from, in context; under each, its strokes at the script's
 * shared scale, so an initial's stub and a final's tail are visible as
 * what they are.
 */
export default function LetterForms({
  script,
  style,
  code,
  glyph,
  forms,
  current,
  fontFamily,
  onPick,
}: {
  script: string
  style: string
  code: string | undefined
  glyph: string
  /** The letter's forms in alphabet order, with strokes where authored. */
  forms: { form: string; authored: Glyph | null }[]
  current: string
  fontFamily: string
  onPick: (form: string) => void
}) {
  const { t } = useTranslation()
  if (forms.length < 2) return null
  const cased = forms.some((f) => f.form === 'upper')
  return (
    <div data-testid="letter-forms" className="space-y-2">
      <p className="text-xs uppercase tracking-wide text-gray-500">{t('write.formsOf', { letter: glyph })}</p>
      <div className="flex flex-wrap gap-2">
        {forms.map((f) => (
          <button
            key={f.form}
            type="button"
            onClick={() => onPick(f.form)}
            aria-pressed={f.form === current}
            data-testid={`letter-form-${f.form}`}
            className={`flex flex-col items-center gap-1 rounded-xl border px-3 py-2 ${
              f.form === current ? 'border-lang bg-lang/5' : 'border-gray-200 bg-white'
            }`}
          >
            <LanguageWrapper languageCode={code ?? 'en'} inline>
              <span
                className="text-4xl leading-none text-gray-900"
                style={{ fontFamily: `${fontFamily}, cursive` }}
              >
                {contextOf(script, style, glyph, f.form)}
              </span>
            </LanguageWrapper>
            {f.authored ? (
              <StrokePreview strokes={f.authored.strokes} size={72} playing={false} fit="box" />
            ) : (
              <span className="h-[72px] w-[72px]" aria-hidden />
            )}
            <span className="text-[11px] text-gray-600">
              {t(`write.form_${f.form}`, { defaultValue: f.form })}
            </span>
          </button>
        ))}
      </div>
      <p className="text-xs text-gray-500">{cased ? t('write.casesHint') : t('write.formsHint')}</p>
    </div>
  )
}
