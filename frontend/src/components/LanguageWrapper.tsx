import clsx from 'clsx'

interface LanguageWrapperProps {
  children: React.ReactNode
  languageCode: string
}

export default function LanguageWrapper({ children, languageCode }: LanguageWrapperProps) {
  const isArabic = languageCode === 'ar'

  return (
    <div
      dir={isArabic ? 'rtl' : 'ltr'}
      className={clsx(isArabic && "font-['Noto_Naskh_Arabic'] text-xl leading-loose")}
    >
      {children}
    </div>
  )
}
