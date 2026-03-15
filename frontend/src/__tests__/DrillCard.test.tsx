import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import DrillCard from '../features/review/DrillCard'

describe('DrillCard', () => {
  describe('fill-in-the-blank mode ({{answer}} marker)', () => {
    it('renders text before the marker', () => {
      render(
        <DrillCard
          sentence="I {{answer}} to school."
          value=""
          onChange={() => {}}
          onSubmit={() => {}}
          disabled={false}
        />,
      )
      expect(screen.getByText(/I/)).toBeDefined()
    })

    it('renders text after the marker', () => {
      render(
        <DrillCard
          sentence="I {{answer}} to school."
          value=""
          onChange={() => {}}
          onSubmit={() => {}}
          disabled={false}
        />,
      )
      expect(screen.getByText(/to school\./)).toBeDefined()
    })

    it('renders an input field replacing the {{answer}} marker', () => {
      render(
        <DrillCard
          sentence="I {{answer}} to school."
          value="go"
          onChange={() => {}}
          onSubmit={() => {}}
          disabled={false}
        />,
      )
      const input = screen.getByRole('textbox')
      expect(input).toBeDefined()
      expect((input as HTMLInputElement).value).toBe('go')
    })

    it('calls onSubmit when Enter key is pressed', () => {
      const onSubmit = vi.fn()
      render(
        <DrillCard
          sentence="I {{answer}} to school."
          value="go"
          onChange={() => {}}
          onSubmit={onSubmit}
          disabled={false}
        />,
      )
      const input = screen.getByRole('textbox')
      fireEvent.keyDown(input, { key: 'Enter' })
      expect(onSubmit).toHaveBeenCalledTimes(1)
    })

    it('does not call onSubmit when disabled', () => {
      const onSubmit = vi.fn()
      render(
        <DrillCard
          sentence="I {{answer}} to school."
          value="go"
          onChange={() => {}}
          onSubmit={onSubmit}
          disabled={true}
        />,
      )
      const input = screen.getByRole('textbox')
      fireEvent.keyDown(input, { key: 'Enter' })
      expect(onSubmit).not.toHaveBeenCalled()
    })

    it('calls onChange when input value changes', () => {
      const onChange = vi.fn()
      render(
        <DrillCard
          sentence="I {{answer}} to school."
          value=""
          onChange={onChange}
          onSubmit={() => {}}
          disabled={false}
        />,
      )
      const input = screen.getByRole('textbox')
      fireEvent.change(input, { target: { value: 'go' } })
      expect(onChange).toHaveBeenCalledWith('go')
    })
  })

  describe('type-the-word mode (no {{answer}} marker)', () => {
    it('renders the sentence as a prompt above the input', () => {
      render(
        <DrillCard
          sentence="a large body of water"
          value=""
          onChange={() => {}}
          onSubmit={() => {}}
          disabled={false}
        />,
      )
      expect(screen.getByText('a large body of water')).toBeDefined()
    })

    it('renders an input field below the sentence', () => {
      render(
        <DrillCard
          sentence="a large body of water"
          value=""
          onChange={() => {}}
          onSubmit={() => {}}
          disabled={false}
        />,
      )
      const input = screen.getByRole('textbox')
      expect(input).toBeDefined()
    })

    it('calls onSubmit when Enter pressed in type-the-word mode', () => {
      const onSubmit = vi.fn()
      render(
        <DrillCard
          sentence="a large body of water"
          value="ocean"
          onChange={() => {}}
          onSubmit={onSubmit}
          disabled={false}
        />,
      )
      const input = screen.getByRole('textbox')
      fireEvent.keyDown(input, { key: 'Enter' })
      expect(onSubmit).toHaveBeenCalledTimes(1)
    })
  })
})
