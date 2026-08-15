import { describe, it, expect } from 'vitest'
import { hintLayersFor, safePrompt } from '../features/review/hintLayers'

describe('safePrompt — the Gym prompt must never give the answer', () => {
  it('strips a spelled-out recipe clause', () => {
    expect(safePrompt('to watch — add -es', 'watches')).toBe('to watch')
    expect(safePrompt('to study — y changes to -ies', 'studies')).toBe('to study')
    expect(safePrompt('to fly — y becomes -ies', 'flies')).toBe('to fly')
  })

  it('blanks the prompt when the base form IS the answer', () => {
    expect(safePrompt('to speak', 'speak')).toBe('')
    expect(safePrompt('speak', 'speak')).toBe('')
  })

  it('keeps legitimate cues that do not reveal the answer', () => {
    expect(safePrompt('preparar, tú', 'preparas')).toBe('preparar, tú')
    expect(safePrompt('go — past', 'went')).toBe('go — past')
    expect(safePrompt('the indefinite article', 'a')).toBe('the indefinite article')
  })

  it('matches the answer only as a whole word', () => {
    // "comer" contains "come" as a substring but not a whole word.
    expect(safePrompt('comer, tú', 'come')).toBe('comer, tú')
    // A stripped lemma that still equals the answer is blanked.
    expect(safePrompt('to run — no change', 'run')).toBe('')
  })

  it('handles empty / missing input', () => {
    expect(safePrompt('', 'x')).toBe('')
    expect(safePrompt('to watch', null)).toBe('to watch')
    expect(safePrompt('to watch', undefined)).toBe('to watch')
  })
})

describe('hintLayersFor — the leak guard covers every surface, not just the Gym', () => {
  // The guard used to run only at the Gym's call site, so a graded review
  // session and the listening cue rendered the authored hint verbatim. 256
  // of the 8,049 authored drill hints contain the answer as a whole word.
  const base = { language_code: 'de', translation: 'We have time.' }

  it('drops an authored hint that is the answer', () => {
    const layers = hintLayersFor('de', {
      ...base, hint: 'haben, wir', correct_answer: 'haben',
    })
    expect(layers.map((l) => l.field)).not.toContain('hint')
    // …and the meaning cue survives, so the card is still answerable.
    expect(layers.map((l) => l.field)).toContain('translation')
  })

  it('keeps an authored hint that only names the form to produce', () => {
    const layers = hintLayersFor('es', {
      translation: 'The cars are new.',
      hint: 'coche, plural',
      correct_answer: 'coches',
    })
    expect(layers.find((l) => l.field === 'hint')?.text).toBe('coche, plural')
  })

  it('still strips a spelled-out recipe inside a layer', () => {
    const layers = hintLayersFor('en', {
      hint: 'to watch — add -es', correct_answer: 'watches',
    })
    expect(layers.find((l) => l.field === 'hint')?.text).toBe('to watch')
  })

  it('never blanks a translation that happens to contain the answer', () => {
    // The translation is the cue the exercise is built on — blanking it
    // would leave a cloze with nothing to go on.
    const layers = hintLayersFor('es', {
      translation: 'The cars are new.', correct_answer: 'new',
    })
    expect(layers.find((l) => l.field === 'translation')?.text).toBe(
      'The cars are new.',
    )
  })

  it('leaves hints alone when the card carries no answer', () => {
    const layers = hintLayersFor('de', { hint: 'haben, wir' })
    expect(layers.find((l) => l.field === 'hint')?.text).toBe('haben, wir')
  })

  it('keeps the dots in step with what is actually revealable', () => {
    // A blanked hint must not leave an empty layer behind, or the Hint
    // button would count a press that shows nothing.
    const withLeak = hintLayersFor('de', {
      translation: 'We have time.', hint: 'haben, wir', correct_answer: 'haben',
    })
    const withoutLeak = hintLayersFor('de', {
      translation: 'We have time.', hint: 'haben, wir', correct_answer: 'hatten',
    })
    expect(withLeak).toHaveLength(withoutLeak.length - 1)
  })
})
