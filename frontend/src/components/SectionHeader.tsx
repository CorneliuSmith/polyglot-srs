import type { ReactNode } from 'react'
import HeaderUtilities from './HeaderUtilities'
import SectionNav from './SectionNav'

/**
 * The shared header for the four tab sections.
 *
 * The whole utility cluster rides here — account, globe, what's new, tour
 * — on every section (owner: "no matter what tab … I want to see the four
 * circle icons"), and deliberately not the study-language picker.
 *
 * The globe made this argument first and it holds for the rest: it is an
 * escape hatch. Someone who has landed in a language they cannot read
 * needs to change it from wherever they are standing, and cannot navigate
 * to a specific page to do it, because they cannot read the way there. A
 * globe icon carries no words, so it works when nothing else on the
 * screen does. Putting it anywhere less than everywhere makes it useless
 * in exactly the case it exists for. The bell earns its place the same
 * way — an announcement badge only works where the learner actually is.
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
      <div className="flex items-center gap-3 sm:gap-4">
        {/* Desktop has no tab bar, so without this the only way back to
            another section is the browser's Back button. */}
        <SectionNav />
        {actions}
        {/* Utility cluster, set apart from navigation: announcements and
            the tour are ABOUT the app, not places in it. */}
        <span aria-hidden className="hidden md:block h-4 w-px bg-gray-200" />
        <HeaderUtilities />
      </div>
    </div>
  )
}
