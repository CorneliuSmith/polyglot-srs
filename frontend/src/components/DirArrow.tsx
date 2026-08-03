import { useTranslation } from 'react-i18next'

/**
 * A '→'/'←' glyph that points the reading-forward (or reading-back)
 * direction for the CURRENT UI language: → forward / ← back in LTR,
 * flipped in RTL (Arabic). For standalone chevrons that aren't already
 * part of a translated string — those bake the correct arrow straight
 * into the string per locale (see ar.json), which this component would
 * only fight with.
 */
export default function DirArrow({
  dir = 'forward',
  className,
}: {
  /** 'forward' = go to / continue; 'back' = return / undo. */
  dir?: 'forward' | 'back'
  className?: string
}) {
  const { i18n } = useTranslation()
  const rtl = i18n.dir() === 'rtl'
  const forward = dir === 'forward'
  const glyph = forward === rtl ? '←' : '→'
  return (
    <span aria-hidden className={className}>
      {glyph}
    </span>
  )
}
