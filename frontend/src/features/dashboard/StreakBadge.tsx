interface StreakBadgeProps {
  days: number
}

function FlameIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className="w-8 h-8 text-orange-400"
      aria-hidden="true"
    >
      <path d="M12 2c0 0-5 5.5-5 10a5 5 0 0 0 10 0c0-4.5-5-10-5-10Zm0 13a2 2 0 0 1-2-2c0-1.7 2-4 2-4s2 2.3 2 4a2 2 0 0 1-2 2Z" />
    </svg>
  )
}

export default function StreakBadge({ days }: StreakBadgeProps) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex flex-col items-center gap-1">
      <FlameIcon />
      {days === 0 ? (
        <span className="text-sm font-medium text-gray-500 text-center">Start your streak!</span>
      ) : (
        <>
          <span className="text-3xl font-bold text-gray-900">{days}</span>
          <span className="text-sm font-medium text-gray-500 uppercase tracking-wide">
            Day streak
          </span>
        </>
      )}
    </div>
  )
}
