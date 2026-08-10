import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import WidgetSlots from '../features/dashboard/WidgetSlots'
import { usePrefsStore } from '../stores/prefsStore'
import type { DashboardStats } from '../api/types'

const stats: DashboardStats = {
  due_count: 5,
  due_grammar: 2,
  due_vocab: 3,
  learned_today: 4,
  streak_days: 12,
  cefr_progress: { A1: { learned: 30, total: 60 } },
  forecast: [
    { date: '2026-08-09', count: 0 },
    { date: '2026-08-10', count: 7 },
  ],
  activity: [{ date: '2026-08-08', vocab: 4, grammar: 3 }],
  stages: {
    vocab: {
      beginner: 0, adept: 0, seasoned: 0, expert: 0, master: 0,
      self_study: 0, ghost: 0,
    },
    grammar: {
      beginner: 0, adept: 0, seasoned: 0, expert: 0, master: 0,
      self_study: 0, ghost: 0,
    },
  },
  profile: {
    days_studied: 8,
    items_studied: 321,
    last_session_accuracy: null,
    week: [],
  },
}

beforeEach(() => {
  usePrefsStore.setState({ dashboardWidgets: [] })
})

describe('WidgetSlots', () => {
  it('starts as two open slots offering to add a widget', () => {
    render(<WidgetSlots stats={stats} />)
    expect(screen.getAllByRole('button', { name: /add widget/i })).toHaveLength(2)
  })

  it('adds a widget through the picker and persists the choice', () => {
    render(<WidgetSlots stats={stats} />)
    fireEvent.click(screen.getAllByRole('button', { name: /add widget/i })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Streak' }))
    expect(screen.getByTestId('widget-streak')).toBeDefined()
    expect(screen.getByText('12')).toBeDefined()
    expect(usePrefsStore.getState().dashboardWidgets).toEqual(['streak'])
    // The other slot stays open.
    expect(screen.getAllByRole('button', { name: /add widget/i })).toHaveLength(1)
  })

  it('renders a persisted choice on mount and removes it via the × button', () => {
    usePrefsStore.setState({ dashboardWidgets: ['forecast'] })
    render(<WidgetSlots stats={stats} />)
    expect(screen.getByTestId('widget-forecast')).toBeDefined()
    expect(screen.getByText('7')).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: /remove widget/i }))
    expect(screen.queryByTestId('widget-forecast')).toBeNull()
    expect(usePrefsStore.getState().dashboardWidgets).toEqual([])
  })

  it('does not offer a widget already pinned in the other slot', () => {
    usePrefsStore.setState({ dashboardWidgets: ['streak'] })
    render(<WidgetSlots stats={stats} />)
    fireEvent.click(screen.getByRole('button', { name: /add widget/i }))
    // "Streak" only appears as the pinned card's heading, not as a picker
    // option — role=button narrows it to the picker.
    expect(screen.queryByRole('button', { name: 'Streak' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Items studied' }))
    expect(screen.getByText('321')).toBeDefined()
    expect(usePrefsStore.getState().dashboardWidgets).toEqual(['streak', 'itemsStudied'])
  })

  it('ignores stale ids from an old persisted state', () => {
    usePrefsStore.setState({ dashboardWidgets: ['retired-widget', 'cefr'] })
    render(<WidgetSlots stats={stats} />)
    expect(screen.getByTestId('widget-cefr')).toBeDefined()
    expect(screen.getAllByRole('button', { name: /add widget/i })).toHaveLength(1)
  })
})
