import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import DrillCard from '../features/review/DrillCard'
import { usePrefsStore } from '../stores/prefsStore'

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

  describe('QWERTY transliteration input', () => {
    beforeEach(() => {
      usePrefsStore.setState({ qwertyTranslit: {} })
    })

    const renderRu = (onChange = vi.fn()) => {
      render(
        <DrillCard
          sentence="Я {{answer}} книгу."
          value=""
          onChange={onChange}
          onSubmit={() => {}}
          disabled={false}
          languageCode="ru"
        />,
      )
      return onChange
    }

    it('converts Latin typing to the target script by default', () => {
      const onChange = renderRu()
      fireEvent.change(screen.getByRole('textbox'), { target: { value: 'chitayu' } })
      expect(onChange).toHaveBeenCalledWith('читаю')
    })

    it('passes input through unchanged when toggled off', () => {
      const onChange = renderRu()
      fireEvent.click(screen.getByRole('button', { name: /qwerty on/i }))
      fireEvent.change(screen.getByRole('textbox'), { target: { value: 'chitayu' } })
      expect(onChange).toHaveBeenCalledWith('chitayu')
      expect(usePrefsStore.getState().qwertyTranslit.ru).toBe(false)
    })

    it('shows the key guide on demand', () => {
      renderRu()
      expect(screen.queryByTestId('translit-guide')).toBeNull()
      fireEvent.click(screen.getByRole('button', { name: /key guide/i }))
      expect(screen.getByTestId('translit-guide')).toBeDefined()
      expect(screen.getByText('zh ch sh shch')).toBeDefined()
    })

    it('renders no controls for Latin-script languages', () => {
      render(
        <DrillCard
          sentence="I {{answer}} to school."
          value=""
          onChange={() => {}}
          onSubmit={() => {}}
          disabled={false}
          languageCode="es"
        />,
      )
      expect(screen.queryByRole('button', { name: /qwerty/i })).toBeNull()
    })
  })
})

describe('DrillCard mobile keyboard', () => {
  it('disables autocorrect, autocapitalize, and spellcheck on the answer input', () => {
    // iOS autocorrect/smart punctuation rewrote correct answers ("am" ->
    // "am." / "'ll" -> curly) and got beta testers marked wrong.
    render(
      <DrillCard
        sentence="I {{answer}} a student."
        value=""
        onChange={() => {}}
        onSubmit={() => {}}
        disabled={false}
        languageCode="en"
        result={null}
      />,
    )
    const input = screen.getByRole('textbox') as HTMLInputElement
    expect(input.getAttribute('autocapitalize')).toBe('none')
    expect(input.getAttribute('autocorrect')).toBe('off')
    expect(input.getAttribute('autocomplete')).toBe('off')
    expect(input.getAttribute('spellcheck')).toBe('false')
  })
})

describe('DrillCard Android IME path', () => {
  // Some Android soft keyboards never emit a usable Enter keydown
  // (keyCode 229 / "Unidentified") — the action key instead triggers
  // implicit form submission. The input is wrapped in a real <form>.
  it('submits via the form when the keydown never fires', () => {
    const onSubmit = vi.fn()
    const { container } = render(
      <DrillCard
        sentence="I {{answer}} a student."
        value="am"
        onChange={() => {}}
        onSubmit={onSubmit}
        disabled={false}
        languageCode="en"
        result={null}
      />,
    )
    fireEvent.submit(container.querySelector('form')!)
    expect(onSubmit).toHaveBeenCalledTimes(1)
  })

  it('ignores form submission while disabled', () => {
    const onSubmit = vi.fn()
    const { container } = render(
      <DrillCard
        sentence="I {{answer}} a student."
        value="am"
        onChange={() => {}}
        onSubmit={onSubmit}
        disabled={true}
        languageCode="en"
        result="correct"
      />,
    )
    fireEvent.submit(container.querySelector('form')!)
    expect(onSubmit).not.toHaveBeenCalled()
  })
})

describe('listening mode (WP19a)', () => {
  it('hides the sentence but keeps the input', () => {
    render(
      <DrillCard
        sentence="I {{answer}} a student."
        value=""
        onChange={() => {}}
        onSubmit={() => {}}
        disabled={false}
        languageCode="en"
        hideSentence
      />,
    )
    expect(screen.getByTestId('listening-drill')).toBeDefined()
    // The words are hidden…
    expect(screen.queryByText(/a student/)).toBeNull()
    // …the answer input is not.
    expect(screen.getByRole('textbox')).toBeDefined()
    expect(screen.getByText(/the pause is the missing word/i)).toBeDefined()
  })

  it('masks each word but marks the blank position (beta report)', () => {
    render(
      <DrillCard
        sentence="I {{answer}} a student."
        value=""
        onChange={() => {}}
        onSubmit={() => {}}
        disabled={false}
        languageCode="en"
        hideSentence
      />,
    )
    const skeleton = screen.getByTestId('listening-skeleton')
    // "I" before the blank → one mask; "a student." after → two masks.
    expect(skeleton.textContent).toBe('▬▬ ___ ▬▬ ▬▬')
  })

  it('skeleton handles a blank at the start of the sentence', () => {
    render(
      <DrillCard
        sentence="{{answer}} to school."
        value=""
        onChange={() => {}}
        onSubmit={() => {}}
        disabled={false}
        languageCode="en"
        hideSentence
      />,
    )
    expect(screen.getByTestId('listening-skeleton').textContent).toBe(
      '___ ▬▬ ▬▬',
    )
  })

  it('shows the sentence normally when off', () => {
    render(
      <DrillCard
        sentence="I {{answer}} a student."
        value=""
        onChange={() => {}}
        onSubmit={() => {}}
        disabled={false}
        languageCode="en"
      />,
    )
    expect(screen.queryByTestId('listening-drill')).toBeNull()
    expect(screen.getByText(/a student/)).toBeDefined()
  })
})
