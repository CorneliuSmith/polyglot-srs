import { describe, it, expect } from 'vitest'
import { hintLayersFor, hintSteps, safePrompt } from '../features/review/hintLayers'

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

describe('every non-Latin course leads with its reading', () => {
  // A learner cannot recall a word they cannot sound out, which is the whole
  // premise of SCRIPT_FIRST. Four courses were missing from that table while
  // carrying a romanisation: ko and th gained computed readings on 26 Aug,
  // he and fa have had authored ones for longer. All four were ordered
  // translation-first, so the layer existed and never led — the same shape as
  // the review card that ignored `sentence_reading` for months.
  const SCRIPT_COURSES = ['ru', 'ar', 'el', 'hi', 'ko', 'th', 'he', 'fa']

  it.each(SCRIPT_COURSES)('%s shows the reading first', (code) => {
    const layers = hintLayersFor(code, {
      transliteration: 'READING',
      gloss: 'a · gloss',
      translation: 'the translation',
      correct_answer: 'zzz',
    })
    expect(layers[0]?.field).toBe('transliteration')
  })

  it('a course with no reading skips the layer rather than showing a blank', () => {
    const layers = hintLayersFor('ko', {
      transliteration: null,
      translation: 'the translation',
      correct_answer: 'zzz',
    })
    expect(layers.map((l) => l.field)).not.toContain('transliteration')
    expect(layers[0]?.field).toBe('translation')
  })

  it('a Latin-script course is unaffected', () => {
    const layers = hintLayersFor('es', {
      translation: 'the translation',
      correct_answer: 'zzz',
    })
    expect(layers[0]?.field).toBe('translation')
  })
})

describe('safePrompt tokenising — the scripts it silently failed on', () => {
  // The guard matched tokens with /\p{L}+/, letters only. That excludes
  // COMBINING MARKS, so every abugida and abjad was weakened: Devanagari
  // रही is र + ह + the vowel sign ी (category Mn), which tokenised as रह and
  // never matched its own answer. Three of the 8,049 authored hints reached a
  // learner with the answer in them because of it.
  it('an answer carrying a combining mark is caught', () => {
    expect(safePrompt('feminine (respect plural takes रही + हैं)', 'रही')).toBe('')
    expect(safePrompt('बात करना takes ने; की agrees with बात (fem.)', 'की')).toBe('')
  })

  it('an answer that begins with an apostrophe is caught', () => {
    expect(safePrompt("'y — contraction after a vowel", "'y")).toBe('')
  })

  it('a hyphenated answer is caught', () => {
    expect(safePrompt('books — plural of buku is buku-buku', 'buku-buku')).toBe('')
  })

  it('...and a bare answer inside a hyphenated word still is', () => {
    // Regression: treating hyphens as word-internal made `man-passive` one
    // token, which stopped matching the answer `Man`. Both granularities are
    // needed, not either one.
    expect(safePrompt('one/you (man-passive)', 'Man')).toBe('')
    expect(safePrompt('(impersonal se-passive)', 'se')).toBe('')
  })
})

describe('every course shows the word-by-word line', () => {
  // The order is the same everywhere — reading, word-by-word, sentence
  // translation, word meaning — with one axis of variation: whether the course
  // has a script the learner cannot sound out.
  //
  // A third order used to exist and it silently dropped the gloss:
  // DEFAULT_ORDER was ['translation', 'hint']. Fourteen courses lost the layer
  // entirely, and because the omission looked deliberate, authoring for them
  // was ruled out on the strength of a bug.
  const ALL = ['ru', 'ar', 'el', 'hi', 'ko', 'th', 'he', 'fa', 'mi', 'sw', 'yo',
    'xh', 'ha', 'es', 'fr', 'de', 'it', 'pt', 'ca', 'ro', 'nl', 'en', 'tr',
    'la', 'id', 'tl', 'jam']

  it.each(ALL)('%s includes the gloss layer', (code) => {
    const layers = hintLayersFor(code, {
      transliteration: 'READING', gloss: 'a · gloss',
      translation: 'the sentence', hint: 'the meaning', correct_answer: 'zzz',
    })
    expect(layers.map((l) => l.field)).toContain('gloss')
  })

  it('orders them reading, word-by-word, sentence, meaning', () => {
    expect(hintLayersFor('ru', {
      transliteration: 'READING', gloss: 'a · gloss',
      translation: 'the sentence', hint: 'the meaning', correct_answer: 'zzz',
    }).map((l) => l.field)).toEqual(['transliteration', 'gloss', 'translation', 'hint'])
  })

  it('a Latin-script course starts at the gloss, having no reading to show', () => {
    expect(hintLayersFor('es', {
      gloss: 'a · gloss', translation: 'the sentence', hint: 'the meaning',
      correct_answer: 'zzz',
    }).map((l) => l.field)).toEqual(['gloss', 'translation', 'hint'])
  })
})

describe('the phonetics layer sits under the reading', () => {
  // A romanisation says which letters; phonetics says how to say them. Thai
  // needs both because RTGS carries no tone at all and Thai is tonal — คำ and
  // ค่ำ are both "kham" — so the reading alone tells a learner how to
  // approximate a word rather than how to pronounce it.
  it('shows reading then phonetics then the rest', () => {
    expect(hintLayersFor('th', {
      transliteration: 'khao pen khon thai',
      phonetics: 'khǎo pen khon thai',
      gloss: 'a · gloss', translation: 'the sentence', hint: 'the meaning',
      correct_answer: 'zzz',
    }).map((l) => l.field)).toEqual(
      ['transliteration', 'phonetics', 'gloss', 'translation', 'hint'])
  })

  it('a course without one skips the layer rather than showing a blank', () => {
    const fields = hintLayersFor('ru', {
      transliteration: 'Ya zhivu', gloss: 'a · gloss',
      translation: 'the sentence', hint: 'the meaning', correct_answer: 'zzz',
    }).map((l) => l.field)
    expect(fields).not.toContain('phonetics')
    expect(fields[0]).toBe('transliteration')
  })

  it('a Latin-script course is unaffected', () => {
    expect(hintLayersFor('es', {
      gloss: 'a · gloss', translation: 'the sentence', hint: 'the meaning',
      correct_answer: 'zzz',
    }).map((l) => l.field)).toEqual(['gloss', 'translation', 'hint'])
  })
})

describe('hintSteps — a gloss never strands the learner on its own', () => {
  // The complaint: "not enough to guess the word from, and confusing for
  // those unfamiliar". A Leipzig gloss answers how the sentence is BUILT,
  // not what it means, so spending a hint on it bought nothing usable.
  it('reveals the gloss and the translation in one press', () => {
    const layers = hintLayersFor('es', {
      gloss: 'almost NEG remain.3SG wine',
      translation: 'There is almost no wine left.',
      hint: 'quedar, impersonal',
    })
    const steps = hintSteps(layers)

    expect(steps).toHaveLength(2)
    expect(steps[0].map((l) => l.field)).toEqual(['gloss', 'translation'])
    // Structure first, meaning second — the order that teaches.
    expect(steps[0][0].field).toBe('gloss')
    expect(steps[1].map((l) => l.field)).toEqual(['hint'])
  })

  it('leaves every other layer its own step', () => {
    const layers = hintLayersFor('ru', {
      transliteration: 'Ya idu domoy',
      gloss: 'I go.1SG home',
      translation: 'I am going home.',
      hint: 'идти, я',
    })
    const steps = hintSteps(layers)
    expect(steps.map((s) => s.map((l) => l.field))).toEqual([
      ['transliteration'],
      ['gloss', 'translation'],
      ['hint'],
    ])
  })

  it('a gloss with no translation behind it still stands alone', () => {
    // Pairing must not invent a layer the card does not carry, or the dots
    // stop matching what is revealable.
    const steps = hintSteps(hintLayersFor('es', { gloss: 'go.1SG home' }))
    expect(steps).toEqual([[expect.objectContaining({ field: 'gloss' })]])
  })

  it('a translation with no gloss is unaffected', () => {
    const steps = hintSteps(hintLayersFor('es', {
      translation: 'I am going home.',
      hint: 'ir, yo',
    }))
    expect(steps.map((s) => s.map((l) => l.field))).toEqual([
      ['translation'],
      ['hint'],
    ])
  })

  it('counts one fewer press than there are layers when both are present', () => {
    // The rung the ladder loses is the one that only ever stranded people.
    const layers = hintLayersFor('es', {
      gloss: 'g', translation: 't', hint: 'h',
    })
    expect(layers).toHaveLength(3)
    expect(hintSteps(layers)).toHaveLength(2)
  })

  it('is empty for a card carrying no layers at all', () => {
    expect(hintSteps(hintLayersFor('es', {}))).toEqual([])
  })
})
