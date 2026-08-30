import { useTranslation } from 'react-i18next'

/** One quiet line under every AI surface: the model can be wrong.
 *
 * Owner: "The legal disclaimers too around ai being wrong." One shared
 * component so the wording (and its translations) can never drift between
 * the tutor, Speak, the reader, and the placement assessor — and so a
 * future legal pass edits one string, not four screens. Deliberately
 * muted: a warning that shouts on every message trains people to ignore
 * warnings.
 */
export default function AiDisclaimer({ className = '' }: { className?: string }) {
  const { t } = useTranslation()
  return (
    <p
      data-testid="ai-disclaimer"
      className={`text-[11px] leading-snug text-gray-400 ${className}`}
    >
      {t('common.aiDisclaimer')}
    </p>
  )
}
