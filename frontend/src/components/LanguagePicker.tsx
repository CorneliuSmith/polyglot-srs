import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getLanguages, updateProfile } from '../api/profile'
import { usePrefsStore } from '../stores/prefsStore'

export default function LanguagePicker() {
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const setActiveLanguageId = usePrefsStore((s) => s.setActiveLanguageId)

  const { data: languages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
  })

  // Auto-select first language when none is stored
  useEffect(() => {
    if (!activeLanguageId && languages.length > 0) {
      const firstId = languages[0].id
      setActiveLanguageId(firstId)
      updateProfile({ active_language_id: firstId }).catch(() => {
        // Non-fatal: store is updated even if the server call fails
      })
    }
  }, [activeLanguageId, languages, setActiveLanguageId])

  async function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const id = e.target.value
    setActiveLanguageId(id)
    await updateProfile({ active_language_id: id }).catch(() => {
      // Non-fatal
    })
  }

  if (languages.length === 0) {
    return (
      <div
        className="w-full rounded-lg border border-gray-300 bg-gray-100 px-3 py-2 text-sm text-gray-400 animate-pulse"
        style={{ minHeight: '44px' }}
        aria-label="Loading languages"
      />
    )
  }

  return (
    <select
      value={activeLanguageId ?? ''}
      onChange={handleChange}
      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
      style={{ minHeight: '44px' }}
      aria-label="Select active language"
    >
      {languages.map((lang) => (
        <option key={lang.id} value={lang.id}>
          {lang.name}
        </option>
      ))}
    </select>
  )
}
