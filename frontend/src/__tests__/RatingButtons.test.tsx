import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import RatingButtons from '../features/review/RatingButtons'

describe('RatingButtons', () => {
  it('renders all 4 rating buttons', () => {
    render(<RatingButtons onRate={() => {}} nlpResult="correct" />)
    expect(screen.getByText('Again')).toBeDefined()
    expect(screen.getByText('Hard')).toBeDefined()
    expect(screen.getByText('Good')).toBeDefined()
    // Easy button has "(suggested)" appended when nlpResult=correct
    expect(screen.getByRole('button', { name: /easy/i })).toBeDefined()
  })

  it('calls onRate with "wrong" when Again is clicked', () => {
    const onRate = vi.fn()
    render(<RatingButtons onRate={onRate} nlpResult="correct" />)
    fireEvent.click(screen.getByText('Again'))
    expect(onRate).toHaveBeenCalledWith('wrong')
  })

  it('calls onRate with "wrong_form" when Hard is clicked', () => {
    const onRate = vi.fn()
    render(<RatingButtons onRate={onRate} nlpResult="correct" />)
    fireEvent.click(screen.getByText('Hard'))
    expect(onRate).toHaveBeenCalledWith('wrong_form')
  })

  it('calls onRate with "correct_sloppy" when Good is clicked', () => {
    const onRate = vi.fn()
    render(<RatingButtons onRate={onRate} nlpResult="correct" />)
    fireEvent.click(screen.getByText('Good'))
    expect(onRate).toHaveBeenCalledWith('correct_sloppy')
  })

  it('calls onRate with "correct" when Easy is clicked', () => {
    const onRate = vi.fn()
    render(<RatingButtons onRate={onRate} nlpResult="wrong" />)
    // Easy has no suffix when not suggested
    fireEvent.click(screen.getByText('Easy'))
    expect(onRate).toHaveBeenCalledWith('correct')
  })

  it('highlights the button matching nlpResult with aria-pressed', () => {
    render(<RatingButtons onRate={() => {}} nlpResult="correct_sloppy" />)
    // "Good" maps to correct_sloppy
    const goodButton = screen.getByRole('button', { name: /good/i })
    expect(goodButton.getAttribute('aria-pressed')).toBe('true')
  })

  it('other buttons have aria-pressed false', () => {
    render(<RatingButtons onRate={() => {}} nlpResult="correct_sloppy" />)
    const againButton = screen.getByRole('button', { name: /again/i })
    expect(againButton.getAttribute('aria-pressed')).toBe('false')
  })

  it('all buttons have minHeight of 44px via style', () => {
    render(<RatingButtons onRate={() => {}} nlpResult="correct" />)
    const buttons = screen.getAllByRole('button')
    buttons.forEach((btn) => {
      expect(btn.style.minHeight).toBe('44px')
    })
  })
})
