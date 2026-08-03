import { useTranslation } from 'react-i18next'
import SpeakButton from '../../components/SpeakButton'

interface FeedbackPanelProps {
  answerResult: string
  feedback: string | null
  correctAnswer: string
  userInput: string
  languageCode?: string
}

export default function FeedbackPanel({
  answerResult,
  feedback,
  correctAnswer,
  userInput,
  languageCode,
}: FeedbackPanelProps) {
  const { t } = useTranslation()
  let bgClass = ''
  let heading = ''
  let icon = ''

  switch (answerResult) {
    case 'correct':
      bgClass = 'bg-green-50 border-green-200 text-green-800'
      heading = t('review.feedbackCorrect')
      icon = '✓'
      break
    case 'correct_sloppy':
      bgClass = 'bg-amber-50 border-amber-200 text-amber-800'
      heading = t('review.feedbackAlmost')
      icon = '⚠'
      break
    case 'wrong_form':
      bgClass = 'bg-orange-50 border-orange-200 text-orange-800'
      heading = t('review.feedbackWrongForm')
      icon = '!'
      break
    case 'wrong':
    default:
      bgClass = 'bg-red-50 border-red-200 text-red-800'
      heading = t('review.feedbackIncorrect')
      icon = '✗'
      break
  }

  return (
    <div className={`rounded-lg p-4 border ${bgClass}`} data-testid="feedback-panel">
      <div className="flex items-center gap-2 mb-2 font-bold text-lg">
        <span aria-hidden="true">{icon}</span>
        <span>{heading}</span>
      </div>

      {answerResult === 'correct' && (
        <p className="text-sm">{t('review.wellDone')}</p>
      )}

      {answerResult === 'correct_sloppy' && (
        <div className="space-y-1 text-sm">
          {feedback && <p>{feedback}</p>}
          <p>{t('review.expected')} <span className="font-semibold">{correctAnswer}</span></p>
        </div>
      )}

      {answerResult === 'wrong_form' && (
        <div className="space-y-1 text-sm">
          {feedback && <p>{feedback}</p>}
          <p>{t('review.expected')} <span className="font-semibold">{correctAnswer}</span></p>
        </div>
      )}

      {answerResult === 'wrong' && (
        <p className="text-sm">
          {t('review.incorrectAnswerWas')}{' '}
          <span className="font-semibold">{correctAnswer}</span>
        </p>
      )}

      {userInput && (
        <p className="text-xs mt-2 opacity-70">
          {t('review.yourAnswer')} <span className="font-medium">{userInput}</span>
        </p>
      )}

      {languageCode && (
        <div className="mt-2 flex items-center gap-1 text-sm">
          <SpeakButton
            text={correctAnswer}
            languageCode={languageCode}
            label={t('review.hearTheWordLabel', { word: correctAnswer })}
          />
          <span className="opacity-70">{t('review.hearTheWord')}</span>
        </div>
      )}
    </div>
  )
}
