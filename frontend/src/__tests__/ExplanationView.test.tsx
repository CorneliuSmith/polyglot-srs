import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ExplanationView from '../components/ExplanationView'

describe('ExplanationView', () => {
  it('typesets a pronoun enumeration as a two-column table', () => {
    // the Romanian example the owner flagged as unreadable — enumeration
    // and follow-up prose in ONE paragraph, as the live data has it
    render(
      <ExplanationView text={
        'Eu (I), tu (you, informal), el/ea (he/she), noi (we), voi (you all), ei/ele (they m/f), plus polite dumneavoastră. The verb ending names the person, so Romanian usually drops the pronoun — vorbesc românește — and uses it for emphasis.'
      } />,
    )
    const rows = screen.getAllByRole('row')
    expect(rows.length).toBe(6)
    expect(screen.getByText('el/ea')).toBeDefined()
    expect(screen.getByText('you, informal')).toBeDefined()
    // the leftover clause survives as a note
    expect(screen.getByText(/plus polite dumneavoastră/)).toBeDefined()
    // the plain paragraph still renders
    expect(screen.getByText(/verb ending names the person/)).toBeDefined()
  })

  it('typesets a colon-introduced example enumeration (the ne/ce card class)', () => {
    // the Hausa card the owner flagged: rule text, colon, then example
    // sentences with glosses — previously one unreadable paragraph
    render(
      <ExplanationView text={
        'Identity sentences end in ne (masculine/plural) or ce (feminine): Ni malami ne (I am a teacher), Ita malama ce (She is a teacher), Su ɗalibai ne (They are students).'
      } />,
    )
    // rule intro stays as prose (parens and all)
    expect(screen.getByText(/Identity sentences end in ne/)).toBeDefined()
    // the three examples become table rows: sentence | gloss
    const rows = screen.getAllByRole('row')
    expect(rows.length).toBe(3)
    expect(screen.getByText('Ni malami ne')).toBeDefined()
    expect(screen.getByText('She is a teacher')).toBeDefined()
  })

  it('typesets a Devanagari colon enumeration and keeps the follow-on prose', () => {
    render(
      <ExplanationView text={
        'होना (to be) in the present: मैं हूँ (I am), यह/वह है (he/she/it is), तुम हो (you are, informal). Unlike Russian or Arabic, Hindi NEVER drops the copula.'
      } />,
    )
    const rows = screen.getAllByRole('row')
    expect(rows.length).toBe(3)
    expect(screen.getByText('मैं हूँ')).toBeDefined()
    expect(screen.getByText(/NEVER drops the copula/)).toBeDefined()
  })

  it('typesets equals-sign runs (the Patois pronoun card class)', () => {
    render(
      <ExplanationView text={
        'Patois pronouns do not change form: mi = I/me/my, yu = you/your, im = he/she/him/her, wi = we/us/our.'
      } />,
    )
    expect(screen.getByText(/Patois pronouns do not change form/)).toBeDefined()
    const rows = screen.getAllByRole('row')
    expect(rows.length).toBe(4)
    expect(screen.getByText('yu')).toBeDefined()
    expect(screen.getByText('he/she/him/her')).toBeDefined()
  })

  it('typesets arrow derivations as a from→to table with intro', () => {
    render(
      <ExplanationView text={
        'Build it from the eles-perfeito minus -am: falaram → falar, quiseram → quiser, fizeram → fizer.'
      } />,
    )
    expect(screen.getByText(/Build it from the eles-perfeito/)).toBeDefined()
    expect(screen.getByText('falaram')).toBeDefined()
    expect(screen.getByText('→ quiser')).toBeDefined()
  })

  it('keeps the sentence AFTER an arrow table out of the rows', () => {
    // the beta screenshot: "Señales: now, at the moment…" was swallowed
    // into the write→writing row and dangled below the table
    render(
      <ExplanationView text={
        'Ortografía: run → running (se dobla la consonante), write → writing (cae la e muda). Señales: now, at the moment, look!'
      } />,
    )
    const rows = screen.getAllByRole('row')
    expect(rows.length).toBe(2)
    // the follow-on sentence renders whole, as prose below the table
    expect(screen.getByText(/Señales: now, at the moment, look!/)).toBeDefined()
    // and no row cell contains the fused text
    expect(screen.queryByText(/muda\). Señales/)).toBeNull()
  })

  it('typesets labeled form runs with a chip', () => {
    render(<ExplanationView text={'-ar: falei, falou, falamos, falaram.'} />)
    expect(screen.getByText('-ar')).toBeDefined()
    expect(screen.getByText('falei, falou, falamos, falaram')).toBeDefined()
  })

  it('dims quoted glosses but never word-internal apostrophes', () => {
    render(
      <ExplanationView text={"falei 'I spoke' means l'hôtel isn't split."} />,
    )
    expect(screen.getByText('‘I spoke’')).toBeDefined()
    expect(screen.getByText(/l'hôtel isn't split/)).toBeDefined()
  })

  it('falls back to plain paragraphs for ordinary prose', () => {
    render(<ExplanationView text={'One sentence.\n\nAnother sentence.'} />)
    expect(screen.getByText('One sentence.')).toBeDefined()
    expect(screen.getByText('Another sentence.')).toBeDefined()
  })
})

describe('ExplanationView — Swahili shapes', () => {
  it('typesets an enumeration with a sentence intro and quoted follow-up', () => {
    // the exact Swahili paragraph the owner flagged
    render(
      <ExplanationView text={
        "The independent pronouns are mimi (I), wewe (you), yeye (he/she), sisi (we), ninyi (you all), wao (they). 'Ni' is the all-purpose present 'to be' and never changes: Mimi ni mwalimu (I am a teacher), Yeye ni daktari."
      } />,
    )
    const rows = screen.getAllByRole('row')
    expect(rows.length).toBe(6)
    expect(screen.getByText('mimi')).toBeDefined() // intro peeled off
    expect(screen.getByText(/The independent pronouns are/)).toBeDefined()
    expect(screen.getByText('wao')).toBeDefined()
    // the follow-up sentence survives as prose
    expect(screen.getByText(/all-purpose present/)).toBeDefined()
  })
})

describe('ExplanationView — markdown blocks (7c phase 2)', () => {
  it('renders a block that carries markdown through the sanitised renderer', () => {
    render(
      <ExplanationView
        text={'**Ser** is for identity.\n\n- ser: soy, eres\n- estar: estoy\n\n| form | use |\n|---|---|\n| soy | I am |'}
      />,
    )
    expect(screen.getByText('Ser').tagName).toBe('STRONG')
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByText('I am')).toBeInTheDocument()
  })

  it('leaves a plain block to the typesetter, even beside a markdown block', () => {
    render(
      <ExplanationView text={'Eu (I), tu (you), el (he), noi (we).\n\n- one item'} />,
    )
    // The enumeration is still the typesetter's two-column table, and the
    // list is the renderer's — one table, one list item, on one card.
    expect(screen.getAllByRole('table')).toHaveLength(1)
    expect(screen.getByText('Eu')).toBeInTheDocument()
    expect(screen.getByRole('listitem').textContent).toBe('one item')
  })

  it('refuses what the allow-list refuses: images, raw html, unsafe links', () => {
    const { container } = render(
      <ExplanationView
        text={'**x** ![pic](https://e.com/p.png) <b>raw</b> [go](javascript:alert(1))'}
      />,
    )
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('b')).toBeNull()
    expect(screen.getByText(/raw/)).toBeInTheDocument()
    const href = container.querySelector('a')?.getAttribute('href') ?? ''
    expect(href).not.toMatch(/javascript/)
  })

  it('a blank written as underscores does not flip a card into markdown', () => {
    // Korean's cards write blanks as "___"; that is prose, not bold.
    render(<ExplanationView text={"Use it for 'I live in ___', and 'I have ___'."} />)
    expect(screen.queryByTestId('card-markdown')).toBeNull()
    expect(screen.getByText(/I live in ___/)).toBeInTheDocument()
  })
})
