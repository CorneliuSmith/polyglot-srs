interface DrillCardProps {
  sentence: string
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  disabled: boolean
  dir?: 'ltr' | 'rtl'
}

export default function DrillCard({
  sentence,
  value,
  onChange,
  onSubmit,
  disabled,
  dir = 'ltr',
}: DrillCardProps) {
  const hasMarker = sentence.includes('{{answer}}')

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !disabled) {
      onSubmit()
    }
  }

  if (!hasMarker) {
    // Type-the-word mode: sentence is the definition/prompt, user types the word
    return (
      <div className="flex flex-col items-center gap-6">
        <p className="text-xl leading-loose text-center text-gray-700" dir={dir}>
          {sentence}
        </p>
        <input
          type="text"
          autoFocus
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Type the word…"
          className="min-w-[200px] border-b-2 border-indigo-400 focus:border-indigo-600 outline-none text-xl text-center py-1 bg-transparent"
          dir={dir}
        />
      </div>
    )
  }

  // Fill-in-the-blank mode: split at {{answer}} marker
  const parts = sentence.split('{{answer}}')
  const before = parts[0]
  const after = parts.slice(1).join('{{answer}}')

  return (
    <p className="text-xl leading-loose text-center" dir={dir}>
      {before}
      <input
        type="text"
        autoFocus
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        className="inline-block min-w-[120px] border-b-2 border-indigo-400 focus:border-indigo-600 outline-none text-xl text-center mx-1 py-0 bg-transparent"
        dir={dir}
      />
      {after}
    </p>
  )
}
