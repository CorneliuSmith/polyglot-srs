import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import TutorMarkdown from '../features/tutor/TutorMarkdown'

describe('TutorMarkdown', () => {
  it('renders a GFM pipe table as a real table', () => {
    render(
      <TutorMarkdown
        content={
          '| Català | Español |\n| --- | --- |\n| jo | yo |\n| tu | tú |'
        }
      />,
    )
    expect(screen.getByRole('table')).toBeDefined()
    expect(screen.getByRole('columnheader', { name: 'Català' })).toBeDefined()
    expect(screen.getByRole('cell', { name: 'jo' })).toBeDefined()
    // No raw pipes left on screen.
    expect(screen.queryByText(/\|/)).toBeNull()
  })

  it('renders emphasis and lists instead of raw markers', () => {
    const { container } = render(
      <TutorMarkdown content={'**Molt bé!**\n\n- primer\n- segon'} />,
    )
    expect(container.querySelector('strong')?.textContent).toBe('Molt bé!')
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
  })
})
