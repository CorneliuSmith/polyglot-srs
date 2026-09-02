import clsx from 'clsx'

interface LanguageWrapperProps {
  children: React.ReactNode
  languageCode: string
  /** Render as a span, for a word quoted inside running text. The default
   * is a block, which inside a paragraph forces the quoted word — and the
   * quote marks around it — onto lines of their own. */
  inline?: boolean
}

export default function LanguageWrapper({
  children,
  languageCode,
  inline = false,
}: LanguageWrapperProps) {
  // Persian shares Arabic's script (and Naskh renders it correctly), so it
  // gets the same script treatment; Hebrew is RTL but a different script —
  // direction only, default typeface.
  const isArabicScript = languageCode === 'ar' || languageCode === 'fa'
  const isRtl = isArabicScript || languageCode === 'he'
  // Devanagari's matras and conjunct stacks need air — same size/leading
  // treatment Arabic gets for its Naskh.
  const isDevanagari = languageCode === 'hi'

  const Tag = inline ? 'span' : 'div'
  return (
    <Tag
      dir={isRtl ? 'rtl' : 'ltr'}
      className={clsx(
        isArabicScript && "font-['Noto_Naskh_Arabic'] text-xl leading-loose",
        isDevanagari && 'text-xl leading-loose',
      )}
    >
      {children}
    </Tag>
  )
}
