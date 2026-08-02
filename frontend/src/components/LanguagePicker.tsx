import { useEffect, useRef, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { getLanguages, getProfile, updateProfile } from '../api/profile'
import { usePrefsStore } from '../stores/prefsStore'
import { languageTheme } from '../lib/languageColors'
import { visibleLanguages } from '../lib/languages'
import CircleFlag from './CircleFlag'

/** The active-language picker. A custom listbox rather than a native
 * <select> so each option (and the trigger) can carry its circle flag —
 * <option> can't render images. Keyboard support mirrors a native select:
 * Enter/Space/arrows open, arrows move, Enter picks, Escape closes. */
export default function LanguagePicker() {
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const setActiveLanguageId = usePrefsStore((s) => s.setActiveLanguageId)

  const { data: allLanguages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
    staleTime: Infinity, // the language list never changes mid-session
  })
  // Admin-hidden languages stay out of this picker — except the one already
  // active, so a language hidden after someone starts it never strands them.
  const languages = visibleLanguages(allLanguages, activeLanguageId)
  const { data: profile } = useQuery({ queryKey: ['profile'], queryFn: getProfile })
  // A Single-language plan is locked to its licensed language.
  const lockedTo =
    profile?.plan_scope === 'single' ? profile.plan_language_id : null

  const [open, setOpen] = useState(false)
  const [highlighted, setHighlighted] = useState(0)
  const rootRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

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

  // Close on any click outside the component.
  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [open])

  // Focus the list when it opens so arrow keys work immediately.
  useEffect(() => {
    if (open) listRef.current?.focus()
  }, [open])

  function choose(id: string) {
    setOpen(false)
    buttonRef.current?.focus()
    if (id === activeLanguageId) return
    setActiveLanguageId(id)
    updateProfile({ active_language_id: id }).catch(() => {
      // Non-fatal
    })
  }

  function openList() {
    const selected = languages.findIndex((l) => l.id === activeLanguageId)
    setHighlighted(selected >= 0 ? selected : 0)
    setOpen(true)
  }

  function onListKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape' || e.key === 'Tab') {
      setOpen(false)
      buttonRef.current?.focus()
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlighted((h) => Math.min(h + 1, languages.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlighted((h) => Math.max(h - 1, 0))
    } else if (e.key === 'Home') {
      e.preventDefault()
      setHighlighted(0)
    } else if (e.key === 'End') {
      e.preventDefault()
      setHighlighted(languages.length - 1)
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      const lang = languages[highlighted]
      if (lang && !(lockedTo && lang.id !== lockedTo)) choose(lang.id)
    }
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

  const active = languages.find((l) => l.id === activeLanguageId)
  const theme = languageTheme(active?.code)

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => (open ? setOpen(false) : openList())}
        onKeyDown={(e) => {
          if (!open && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
            e.preventDefault()
            openList()
          }
        }}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Select active language"
        className="w-full flex items-center gap-2.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-start focus:outline-none focus:ring-2 focus:ring-lang"
        style={{ minHeight: '44px', borderLeft: `6px solid ${theme.primary}` }}
      >
        <CircleFlag code={active?.code} />
        <span className="flex-1 truncate text-gray-900">
          {active?.name ?? 'Choose a language'}
        </span>
        <ChevronDown
          aria-hidden
          className={`h-4 w-4 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <ul
          ref={listRef}
          role="listbox"
          aria-label="Languages"
          aria-activedescendant={`lang-option-${languages[highlighted]?.id}`}
          tabIndex={-1}
          onKeyDown={onListKeyDown}
          className="absolute z-30 mt-1 max-h-72 w-full overflow-y-auto rounded-xl border border-gray-200 bg-white py-1 shadow-lg focus:outline-none"
        >
          {languages.map((lang, i) => {
            const locked = !!lockedTo && lang.id !== lockedTo
            const selected = lang.id === activeLanguageId
            return (
              <li
                key={lang.id}
                id={`lang-option-${lang.id}`}
                role="option"
                aria-selected={selected}
                aria-disabled={locked || undefined}
                onMouseEnter={() => setHighlighted(i)}
                onClick={() => {
                  if (!locked) choose(lang.id)
                }}
                className={`flex cursor-pointer items-center gap-2.5 px-3 py-2 text-sm ${
                  locked
                    ? 'cursor-not-allowed text-gray-300'
                    : i === highlighted
                      ? 'bg-lang-soft text-gray-900'
                      : 'text-gray-700'
                }`}
                style={{ minHeight: '40px' }}
              >
                <CircleFlag
                  code={lang.code}
                  className={locked ? 'opacity-40 grayscale' : ''}
                />
                <span className="flex-1 truncate">{lang.name}</span>
                {selected && (
                  <span aria-hidden className="text-lang font-semibold">✓</span>
                )}
                {locked && (
                  <span className="text-[10px] text-gray-400">
                    All-Languages plan
                  </span>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
