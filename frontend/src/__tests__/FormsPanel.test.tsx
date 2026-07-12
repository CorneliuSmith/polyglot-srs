import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import FormsPanel from '../components/FormsPanel'

const ruVerb = {
  pos: 'verb',
  chips: [
    { label: 'Aspect', value: 'imperfective' },
    { label: 'Perfective pair', value: 'сказа́ть' },
  ],
  charts: [
    {
      title: 'Present',
      rows: [
        ['я', 'говорю́'],
        ['ты', 'говори́шь'],
        ['он/она́', 'говори́т'],
      ],
    },
    {
      title: 'Declension',
      columns: ['', 'Singular', 'Plural'],
      rows: [['Nom.', 'кни́га', 'кни́ги']],
    },
  ],
}

describe('FormsPanel', () => {
  it('renders chips and conjugation charts', () => {
    render(<FormsPanel morphology={ruVerb} languageCode="ru" />)
    expect(screen.getByText('Forms')).toBeDefined()
    expect(screen.getByText('Aspect')).toBeDefined()
    expect(screen.getByText('сказа́ть')).toBeDefined()
    expect(screen.getByText('Present')).toBeDefined()
    expect(screen.getByText('говорю́')).toBeDefined()
    expect(screen.getByText('Singular')).toBeDefined() // column header
  })

  it('accepts morphology as a JSON string (older payloads)', () => {
    render(
      <FormsPanel morphology={JSON.stringify(ruVerb)} languageCode="ru" />,
    )
    expect(screen.getByText('говорю́')).toBeDefined()
  })

  it('renders nothing when there are no chips or charts', () => {
    const { container } = render(
      <FormsPanel morphology={{ lemma: 'x' }} languageCode="es" />,
    )
    expect(container.innerHTML).toBe('')
  })

  it('renders nothing on unparseable input', () => {
    const { container } = render(
      <FormsPanel morphology="not json" languageCode="es" />,
    )
    expect(container.innerHTML).toBe('')
  })
})
