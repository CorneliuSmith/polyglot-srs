import clsx from 'clsx'

interface LanguageWrapperProps {
  children: React.ReactNode
  languageCode: string
}

export default function LanguageWrapper({ children, languageCode }: LanguageWrapperProps) {
  // Persian shares Arabic's script (and Naskh renders it correctly), so it
  // gets the same script treatment; Hebrew is RTL but a different script —
  // direction only, default typeface.
  const isArabicScript = languageCode === 'ar' || languageCode === 'fa'
  const isRtl = isArabicScript || languageCode === 'he'
  // Devanagari's matras and conjunct stacks need air — same size/leading
  // treatment Arabic gets for its Naskh.
  const isDevanagari = languageCode === 'hi'

  return (
    <div
      dir={isRtl ? 'rtl' : 'ltr'}
      className={clsx(
        isArabicScript && "font-['Noto_Naskh_Arabic'] text-xl leading-loose",
        isDevanagari && 'text-xl leading-loose',
      )}
    >
      {children}
    </div>
  )
}
