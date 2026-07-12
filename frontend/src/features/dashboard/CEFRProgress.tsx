import type { CEFRLevelProgress } from '../../api/types'

const CEFR_LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']

interface CEFRProgressProps {
  progress: Record<string, CEFRLevelProgress>
}

export default function CEFRProgress({ progress }: CEFRProgressProps) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
      <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
        CEFR Progress
      </h2>
      <div className="space-y-3">
        {CEFR_LEVELS.map((level) => {
          const { learned = 0, total = 0 } = progress[level] ?? {}
          const pct = total > 0 ? Math.round((learned / total) * 100) : 0
          return (
            <div key={level} className="flex items-center gap-3">
              <span className="w-7 text-xs font-semibold text-gray-500 shrink-0">{level}</span>
              <div
                className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden"
                role="progressbar"
                aria-valuenow={pct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${level} progress`}
              >
                <div
                  className="h-full bg-lang rounded-full transition-all duration-500"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="w-9 text-xs text-gray-400 text-end shrink-0">{pct}%</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
