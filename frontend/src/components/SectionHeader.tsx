import type { ReactNode } from 'react'
import UiLanguageSwitcher from './UiLanguageSwitcher'

/**
 * The shared header for the four tab sections.
 *
 * The INTERFACE language switcher rides here — the globe — on every
 * section, and deliberately not the study-language picker.
 *
 * The reason is that it is an escape hatch. Someone who has landed in a
 * language they cannot read needs to change it from wherever they are
 * standing, and cannot navigate to a specific page to do it, because they
 * cannot read the way there. A globe icon carries no words, so it works
 * when nothing else on the screen does. Putting it anywhere less than
 * everywhere makes it useless in exactly the case it exists for.
 *
 * The study language is a different kind of choice — deliberate, made
 * rarely, and legible by definition — so it stays on Study.
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
        <UiLanguageSwitcher />
      </div>
    </div>
  )
}
