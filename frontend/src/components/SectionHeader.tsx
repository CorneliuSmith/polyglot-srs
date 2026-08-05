import type { ReactNode } from 'react'
import LanguagePicker from './LanguagePicker'

/**
 * The shared header for the four tab sections.
 *
 * The language switcher rides here rather than living on the Study tab
 * alone. Which language you're in changes what EVERY section shows —
 * Practice's Gym availability, Progress's numbers, More's language guide —
 * so having to go back to Study to change it, then return, was a detour
 * with no purpose. Same position on every tab, so it's never hunted for.
 */
export default function SectionHeader({
  title,
  actions,
}: {
  title: string
  actions?: ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-3 flex-wrap">
      <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
      <div className="flex items-center gap-2">
        {actions}
        <LanguagePicker compact />
      </div>
    </div>
  )
}
