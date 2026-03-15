interface RatingButtonsProps {
  onRate: (answerResult: string) => void
  nlpResult: string
}

const RATINGS = [
  { label: 'Again', value: 'wrong', colorClass: 'bg-red-100 hover:bg-red-200 text-red-800 border-red-200' },
  { label: 'Hard', value: 'wrong_form', colorClass: 'bg-orange-100 hover:bg-orange-200 text-orange-800 border-orange-200' },
  { label: 'Good', value: 'correct_sloppy', colorClass: 'bg-yellow-100 hover:bg-yellow-200 text-yellow-800 border-yellow-200' },
  { label: 'Easy', value: 'correct', colorClass: 'bg-green-100 hover:bg-green-200 text-green-800 border-green-200' },
] as const

export default function RatingButtons({ onRate, nlpResult }: RatingButtonsProps) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {RATINGS.map(({ label, value, colorClass }) => {
        const isDefault = value === nlpResult
        return (
          <button
            key={value}
            type="button"
            onClick={() => onRate(value)}
            className={`
              rounded-lg font-semibold border transition-colors touch-manipulation
              ${colorClass}
              ${isDefault ? 'ring-2 ring-offset-1 ring-indigo-500' : ''}
            `}
            style={{ minHeight: '44px' }}
            aria-pressed={isDefault}
          >
            {label}
            {isDefault && (
              <span className="ml-1 text-xs opacity-70">(suggested)</span>
            )}
          </button>
        )
      })}
    </div>
  )
}
