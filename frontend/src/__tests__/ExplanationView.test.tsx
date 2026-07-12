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
