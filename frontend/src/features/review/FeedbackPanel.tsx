interface FeedbackPanelProps {
  answerResult: string
  feedback: string | null
  correctAnswer: string
  userInput: string
}

export default function FeedbackPanel({
  answerResult,
  feedback,
  correctAnswer,
  userInput,
}: FeedbackPanelProps) {
  let bgClass = ''
  let heading = ''
  let icon = ''

  switch (answerResult) {
    case 'correct':
      bgClass = 'bg-green-50 border-green-200 text-green-800'
      heading = 'Correct!'
      icon = '✓'
      break
    case 'correct_sloppy':
      bgClass = 'bg-amber-50 border-amber-200 text-amber-800'
      heading = 'Almost!'
      icon = '⚠'
      break
    case 'wrong_form':
      bgClass = 'bg-orange-50 border-orange-200 text-orange-800'
      heading = 'Wrong Form'
      icon = '!'
      break
    case 'wrong':
    default:
      bgClass = 'bg-red-50 border-red-200 text-red-800'
      heading = 'Incorrect'
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
        <p className="text-sm">Well done!</p>
      )}

      {answerResult === 'correct_sloppy' && (
        <div className="space-y-1 text-sm">
          {feedback && <p>{feedback}</p>}
          <p>Expected: <span className="font-semibold">{correctAnswer}</span></p>
        </div>
      )}

      {answerResult === 'wrong_form' && (
        <div className="space-y-1 text-sm">
          {feedback && <p>{feedback}</p>}
          <p>Expected: <span className="font-semibold">{correctAnswer}</span></p>
        </div>
      )}

      {answerResult === 'wrong' && (
        <p className="text-sm">
          Incorrect. The answer was:{' '}
          <span className="font-semibold">{correctAnswer}</span>
        </p>
      )}

      {userInput && (
        <p className="text-xs mt-2 opacity-70">
          Your answer: <span className="font-medium">{userInput}</span>
        </p>
      )}
    </div>
  )
}
