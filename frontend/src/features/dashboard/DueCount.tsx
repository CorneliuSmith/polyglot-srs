interface DueCountProps {
  count: number
}

export default function DueCount({ count }: DueCountProps) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex flex-col items-center gap-1">
      <span className="text-5xl font-bold text-indigo-600">{count}</span>
      <span className="text-sm font-medium text-gray-500 uppercase tracking-wide">Cards Due</span>
    </div>
  )
}
