import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import LetterForms from '../features/write/LetterForms'

HTMLCanvasElement.prototype.getContext = (() => null) as unknown as typeof HTMLCanvasElement.prototype.getContext

const authored = (form: string) => ({
  id: `g-${form}`, script: 'arabic', glyph: 'ب', form, style: 'naskh',
  strokes: [[[0, 600], [100, 600]]], joins: {}, hints: [], source: 'provisional', reviewed: true,
})

describe('LetterForms', () => {
  it('shows every form of the letter in context, marks the current one, and lets the learner jump', () => {
    const onPick = vi.fn()
    render(
      <LetterForms
        script="arabic" style="naskh" code="ar" glyph="ب" fontFamily="serif" current="medial" onPick={onPick}
        forms={[
          { form: 'isolated', authored: authored('isolated') },
          { form: 'final', authored: authored('final') },
          { form: 'initial', authored: null },
          { form: 'medial', authored: authored('medial') },
        ]}
      />,
    )
    expect(screen.getByTestId('letter-forms')).toHaveTextContent('Every form of ب')
    // In context: the medial sits between two kashidas, the initial before one.
    expect(screen.getByTestId('letter-form-medial')).toHaveTextContent('ـبـ')
    expect(screen.getByTestId('letter-form-initial')).toHaveTextContent('بـ')
    expect(screen.getByTestId('letter-form-medial')).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('letter-form-isolated')).toHaveAttribute('aria-pressed', 'false')
    fireEvent.click(screen.getByTestId('letter-form-final'))
    expect(onPick).toHaveBeenCalledWith('final')
  })

  it('cursive cases: the lower-case letter is shown joined between vowels', () => {
    render(
      <LetterForms
        script="cyrillic" style="cursive" code="ru" glyph="т" fontFamily="serif" current="lower" onPick={() => {}}
        forms={[{ form: 'lower', authored: null }, { form: 'upper', authored: null }]}
      />,
    )
    expect(screen.getByTestId('letter-form-lower')).toHaveTextContent('ото')
    expect(screen.getByTestId('letter-form-upper')).toHaveTextContent('Т')
    expect(screen.getByText(/both cases/i)).toBeInTheDocument()
  })

  it('renders nothing for a letter with one form', () => {
    const { container } = render(
      <LetterForms script="thai" style="print" code="th" glyph="ก" fontFamily="serif" current="letter" onPick={() => {}}
        forms={[{ form: 'letter', authored: null }]} />,
    )
    expect(container.firstChild).toBeNull()
  })
})
