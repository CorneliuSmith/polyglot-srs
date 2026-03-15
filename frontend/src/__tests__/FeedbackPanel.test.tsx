import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import FeedbackPanel from '../features/review/FeedbackPanel'

describe('FeedbackPanel', () => {
  describe('correct result', () => {
    it('renders Correct heading', () => {
      render(
        <FeedbackPanel
          answerResult="correct"
          feedback={null}
          correctAnswer="go"
          userInput="go"
        />,
      )
      expect(screen.getByText('Correct!')).toBeDefined()
    })

    it('has green background class', () => {
      const { container } = render(
        <FeedbackPanel
          answerResult="correct"
          feedback={null}
          correctAnswer="go"
          userInput="go"
        />,
      )
      const panel = container.querySelector('[data-testid="feedback-panel"]')
      expect(panel?.className).toContain('bg-green')
    })
  })

  describe('correct_sloppy result', () => {
    it('renders Almost heading', () => {
      render(
        <FeedbackPanel
          answerResult="correct_sloppy"
          feedback="Try using the more formal form."
          correctAnswer="goes"
          userInput="go"
        />,
      )
      expect(screen.getByText('Almost!')).toBeDefined()
    })

    it('shows feedback message', () => {
      render(
        <FeedbackPanel
          answerResult="correct_sloppy"
          feedback="Try using the more formal form."
          correctAnswer="goes"
          userInput="go"
        />,
      )
      expect(screen.getByText('Try using the more formal form.')).toBeDefined()
    })

    it('shows expected form', () => {
      render(
        <FeedbackPanel
          answerResult="correct_sloppy"
          feedback={null}
          correctAnswer="goes"
          userInput="go"
        />,
      )
      expect(screen.getByText('goes')).toBeDefined()
    })

    it('has amber background class', () => {
      const { container } = render(
        <FeedbackPanel
          answerResult="correct_sloppy"
          feedback={null}
          correctAnswer="goes"
          userInput="go"
        />,
      )
      const panel = container.querySelector('[data-testid="feedback-panel"]')
      expect(panel?.className).toContain('bg-amber')
    })
  })

  describe('wrong_form result', () => {
    it('renders Wrong Form heading', () => {
      render(
        <FeedbackPanel
          answerResult="wrong_form"
          feedback="Use the past tense form."
          correctAnswer="went"
          userInput="go"
        />,
      )
      expect(screen.getByText('Wrong Form')).toBeDefined()
    })

    it('shows grammar explanation feedback text', () => {
      render(
        <FeedbackPanel
          answerResult="wrong_form"
          feedback="Use the past tense form."
          correctAnswer="went"
          userInput="go"
        />,
      )
      expect(screen.getByText('Use the past tense form.')).toBeDefined()
    })

    it('has orange background class', () => {
      const { container } = render(
        <FeedbackPanel
          answerResult="wrong_form"
          feedback={null}
          correctAnswer="went"
          userInput="go"
        />,
      )
      const panel = container.querySelector('[data-testid="feedback-panel"]')
      expect(panel?.className).toContain('bg-orange')
    })
  })

  describe('wrong result', () => {
    it('renders Incorrect heading', () => {
      render(
        <FeedbackPanel
          answerResult="wrong"
          feedback={null}
          correctAnswer="went"
          userInput="gone"
        />,
      )
      expect(screen.getByText('Incorrect')).toBeDefined()
    })

    it('shows the correct answer', () => {
      render(
        <FeedbackPanel
          answerResult="wrong"
          feedback={null}
          correctAnswer="went"
          userInput="gone"
        />,
      )
      expect(screen.getByText('went')).toBeDefined()
    })

    it('has red background class', () => {
      const { container } = render(
        <FeedbackPanel
          answerResult="wrong"
          feedback={null}
          correctAnswer="went"
          userInput="gone"
        />,
      )
      const panel = container.querySelector('[data-testid="feedback-panel"]')
      expect(panel?.className).toContain('bg-red')
    })
  })

  it('shows the user input', () => {
    render(
      <FeedbackPanel
        answerResult="wrong"
        feedback={null}
        correctAnswer="went"
        userInput="gone"
      />,
    )
    expect(screen.getByText('gone')).toBeDefined()
  })
})
