/**
 * QWERTY transliteration input ("type privet, get привет").
 *
 * For the non-Latin-script languages a learner without a native keyboard can
 * type standard romanization on QWERTY and the answer blank converts as they
 * type. Schemes follow each language's common convention (translit.ru-style
 * for Russian, chat-alphabet digits for Arabic, letter-name phonetics for
 * Hebrew, "Finglish" for Persian, Greeklish for Greek, and IME-style
 * romanization for the three ASSEMBLING scripts — Devanagari, Thai and
 * Hangul); every mapping is viewable in the in-app key guide.
 *
 * Design:
 *  - `convertTranslit` runs over the WHOLE input value on every keystroke.
 *    It is idempotent on already-converted text, so `value =
 *    convert(prevConverted + newChar)` is the entire integration contract.
 *  - Digraphs typed across keystrokes (s → с, then h) are handled by combo
 *    rules on (converted char + Latin char) pairs: сh → ш.
 *  - Arabic short vowels are positional (initial → ا, medial → omitted,
 *    final → long letter), so a vowel at the end of the input stays Latin
 *    until the next keystroke decides its fate; `finalizeTranslit` resolves
 *    it at submit time.
 *  - The assembling scripts (hi/th/ko) can't substitute letter-for-letter:
 *    each decodes the field back to a phonetic string and re-encodes it, so
 *    a syllable re-forms correctly as it grows ("ka" → का on the next
 *    keystroke). A trailing consonant with nothing to attach to stays
 *    pending (Latin) until `finalizeTranslit`.
 *  - `composeScript` is the on-screen-keyboard counterpart: those keys insert
 *    raw glyphs, which only Hangul needs fusing into blocks.
 */

export const TRANSLIT_LANGS = ['ru', 'ar', 'el', 'he', 'fa', 'hi', 'th', 'ko'] as const

export function hasTranslit(code: string): boolean {
  return (TRANSLIT_LANGS as readonly string[]).includes(code)
}

export interface GuideRow {
  keys: string
  out: string
  note?: string
}

const isUpper = (ch: string) => ch !== ch.toLowerCase() && ch === ch.toUpperCase()

/** Case-preserving scan: longest multigraph first, then single letters. */
function convertLatinRuns(
  text: string,
  multi: [string, string][],
  single: Record<string, string>,
): string {
  let res = ''
  let i = 0
  while (i < text.length) {
    let matched = false
    for (const [seq, rep] of multi) {
      const slice = text.slice(i, i + seq.length)
      if (slice.toLowerCase() === seq) {
        res += isUpper(slice[0]) ? rep.charAt(0).toUpperCase() + rep.slice(1) : rep
        i += seq.length
        matched = true
        break
      }
    }
    if (matched) continue
    const ch = text[i]
    const rep = single[ch.toLowerCase()]
    if (rep !== undefined) {
      res += isUpper(ch) ? rep.toUpperCase() : rep
    } else {
      res += ch
    }
    i++
  }
  return res
}

/** Apply combo rules (converted char + latin char) with uppercase variants. */
function applyCombos(text: string, combos: [string, string][]): string {
  let out = text
  for (const [seq, rep] of combos) {
    out = out.split(seq).join(rep)
    const upperSeq = seq.charAt(0).toUpperCase() + seq.slice(1)
    if (upperSeq !== seq) out = out.split(upperSeq).join(rep.toUpperCase())
  }
  return out
}

// ── Russian ──────────────────────────────────────────────────────────────────

const RU_MULTI: [string, string][] = [
  ['shch', 'щ'], ['sch', 'щ'],
  ['zh', 'ж'], ['kh', 'х'], ['ts', 'ц'], ['ch', 'ч'], ['sh', 'ш'],
  ['yo', 'ё'], ['yu', 'ю'], ['ya', 'я'], ['ye', 'е'],
  ["e'", 'э'], ["''", 'ъ'],
]

const RU_SINGLE: Record<string, string> = {
  a: 'а', b: 'б', v: 'в', g: 'г', d: 'д', e: 'е', z: 'з', i: 'и', j: 'й',
  k: 'к', l: 'л', m: 'м', n: 'н', o: 'о', p: 'п', r: 'р', s: 'с', t: 'т',
  u: 'у', f: 'ф', h: 'х', x: 'х', c: 'ц', w: 'в', q: 'к', y: 'ы', "'": 'ь',
}

// Digraph completions across keystrokes: the first letter is already
// converted when the second arrives.
const RU_COMBOS: [string, string][] = [
  ['сh', 'ш'], ['зh', 'ж'], ['цh', 'ч'], ['кh', 'х'], ['шч', 'щ'],
  ['ыa', 'я'], ['ыu', 'ю'], ['ыo', 'ё'], ['ыe', 'е'],
  ["е'", 'э'], ["ь'", 'ъ'],
]

function convertRu(text: string): string {
  return convertLatinRuns(applyCombos(text, RU_COMBOS), RU_MULTI, RU_SINGLE)
}

// ── Greek ────────────────────────────────────────────────────────────────────

const EL_MULTI: [string, string][] = [
  ['th', 'θ'], ['ch', 'χ'], ['ps', 'ψ'],
]

const EL_SINGLE: Record<string, string> = {
  a: 'α', b: 'β', v: 'β', g: 'γ', d: 'δ', e: 'ε', z: 'ζ', h: 'η', i: 'ι',
  k: 'κ', l: 'λ', m: 'μ', n: 'ν', x: 'ξ', o: 'ο', p: 'π', r: 'ρ', s: 'σ',
  t: 'τ', u: 'υ', y: 'υ', f: 'φ', w: 'ω', c: 'κ',
}

const EL_COMBOS: [string, string][] = [
  ['τh', 'θ'], ['κh', 'χ'], ['πs', 'ψ'],
]

const GREEK_LETTER = /[Ͱ-Ͽἀ-῿]/

function fixFinalSigma(text: string): string {
  let out = ''
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]
    const next = text[i + 1]
    if (ch === 'σ' && (!next || !GREEK_LETTER.test(next))) out += 'ς'
    else if (ch === 'ς' && next && GREEK_LETTER.test(next)) out += 'σ'
    else out += ch
  }
  return out
}

function convertEl(text: string): string {
  return fixFinalSigma(
    convertLatinRuns(applyCombos(text, EL_COMBOS), EL_MULTI, EL_SINGLE),
  )
}

// ── Arabic ───────────────────────────────────────────────────────────────────
// Case-sensitive: capitals are the emphatic letters (S=ص D=ض T=ط Z=ظ H=ح),
// chat-alphabet digits cover the rest (3=ع 7=ح 2=ء 5=خ). Short vowels are
// positional: word-initial → ا, medial → omitted (Arabic doesn't write
// them), final a → ا, final i/e → ي, final o/u → و; doubled vowels are the
// long letters anywhere (aa → ا, ii → ي, uu → و). Word-final "ah" → ة.

const AR_MULTI: [string, string][] = [
  ['aa', 'ا'], ['ee', 'ي'], ['ii', 'ي'], ['oo', 'و'], ['uu', 'و'],
  ['th', 'ث'], ['kh', 'خ'], ['dh', 'ذ'], ['sh', 'ش'], ['gh', 'غ'],
]

const AR_SINGLE: Record<string, string> = {
  b: 'ب', t: 'ت', j: 'ج', H: 'ح', '7': 'ح', '5': 'خ', d: 'د', r: 'ر',
  z: 'ز', s: 'س', S: 'ص', D: 'ض', T: 'ط', Z: 'ظ', '3': 'ع', '2': 'ء',
  g: 'ج', f: 'ف', q: 'ق', k: 'ك', l: 'ل', m: 'م', n: 'ن', h: 'ه',
  w: 'و', y: 'ي', "'": 'ء',
}

const AR_VOWEL_FINAL: Record<string, string> = {
  a: 'ا', e: 'ي', i: 'ي', o: 'و', u: 'و',
}

// Digraph completions across keystrokes: the first letter converted on its
// own keystroke, the h arrives later (s → س, h → merge into ش). A vowel
// typed between them (still pending as Latin) keeps them apart, so سهل
// ("sahl") never merges.
const AR_COMBOS: [string, string][] = [
  ['سh', 'ش'], ['تh', 'ث'], ['دh', 'ذ'], ['كh', 'خ'], ['جh', 'غ'],
]

const AR_WORD_CHAR = /[A-Za-z0-9'ء-ي٠-٩]/

function convertAr(rawText: string, finalizePending: boolean): string {
  let text = rawText
  for (const [seq, rep] of AR_COMBOS) text = text.split(seq).join(rep)
  // A taa marbuta is only ever word-final; if typing continued past one it
  // was formed prematurely ("sah|l") — revert it to ه.
  text = text.replace(/ة(?=[A-Za-z0-9'ء-ي٠-٩])/g, 'ه')
  let res = ''
  let i = 0
  const wordChar = (ch?: string) => !!ch && AR_WORD_CHAR.test(ch)
  while (i < text.length) {
    const ch = text[i]
    const prev = i > 0 ? text[i - 1] : undefined
    // multigraphs (all lowercase; Arabic scheme is case-sensitive)
    let matched = false
    for (const [seq, rep] of AR_MULTI) {
      if (text.slice(i, i + seq.length) === seq) {
        res += rep
        i += seq.length
        matched = true
        break
      }
    }
    if (matched) continue
    // word-final "ah" → ة (taa marbuta), checked before plain h
    if (
      ch === 'a' && text[i + 1] === 'h' && !wordChar(text[i + 2]) &&
      wordChar(prev)
    ) {
      res += 'ة'
      i += 2
      continue
    }
    if (ch.toLowerCase() in AR_VOWEL_FINAL && ch === ch.toLowerCase()) {
      const next = text[i + 1]
      if (!wordChar(prev)) {
        res += 'ا' // word-initial vowel seat
      } else if (!wordChar(next)) {
        // Trailing vowel: undecided until the next keystroke — keep it Latin
        // while typing, resolve to the long letter on submit.
        res += finalizePending ? AR_VOWEL_FINAL[ch] : ch
      }
      // medial short vowel: unwritten
      i++
      continue
    }
    res += AR_SINGLE[ch] ?? ch
    i++
  }
  return res
}

// ── Hebrew ───────────────────────────────────────────────────────────────────
// Consonantal like Arabic, and the vowels behave the same way: unwritten in
// the middle of a word, seated on א at the start. Modern ktiv male does spell
// the long o/u with ו and long i with י, which is why only those carry a
// letter medially — writing every vowel gives שאלומ for "shalom" instead of
// שלום. Two Hebrew-specific mechanics on top:
//   - FINAL FORMS: כ מ נ פ צ become ך ם ן ף ץ at a word's end.
//   - final a/e is spelled ה (torah → תורה).
// Both are deferred while the word is still growing, exactly as Arabic defers
// its trailing vowel, and resolved by `finalize` at submit.

const HE_MULTI: [string, string][] = [
  ['sh', 'ש'], ['ts', 'צ'], ['tz', 'צ'], ['ch', 'ח'], ['kh', 'כ'],
  ['th', 'ת'], ['ph', 'פ'], ['ee', 'י'], ['ii', 'י'], ['oo', 'ו'], ['uu', 'ו'],
]

const HE_SINGLE: Record<string, string> = {
  b: 'ב', g: 'ג', d: 'ד', h: 'ה', v: 'ו', w: 'ו', z: 'ז', T: 'ט', y: 'י',
  k: 'כ', l: 'ל', m: 'מ', n: 'נ', s: 'ס', p: 'פ', f: 'פ', q: 'ק', r: 'ר',
  t: 'ת', c: 'צ', "'": 'ע',
}

/** Medial spelling: only the long o/u/i are written in ktiv male. */
const HE_VOWEL_MEDIAL: Record<string, string> = { o: 'ו', u: 'ו' }
/** Word-initial: every vowel takes an א seat, and i/o/u add their mater
 *  (ish → איש, or → אור) — א alone would give אש, a different word. */
const HE_VOWEL_INITIAL: Record<string, string> = {
  a: 'א', e: 'א', i: 'אי', o: 'או', u: 'או',
}
/** Word-final spelling: a/e settle on ה, i on י, o/u on ו. */
const HE_VOWEL_FINAL: Record<string, string> = {
  a: 'ה', e: 'ה', i: 'י', o: 'ו', u: 'ו',
}

/** כ מ נ פ צ → ך ם ן ף ץ at the end of a word. */
const HE_FINALS: Record<string, string> = {
  'כ': 'ך', 'מ': 'ם', 'נ': 'ן', 'פ': 'ף', 'צ': 'ץ',
}

const HE_WORD_CHAR = /[A-Za-z'֐-׿]/

function convertHe(rawText: string, finalize: boolean): string {
  // Digraph completed across keystrokes: ס then h → ש.
  let text = rawText
  for (const [seq, rep] of [
    ['סh', 'ש'], ['תh', 'ת'], ['כh', 'כ'], ['צh', 'צ'], ['חh', 'ח'],
  ] as [string, string][]) {
    text = text.split(seq).join(rep)
  }
  let res = ''
  let i = 0
  const wordChar = (ch?: string) => !!ch && HE_WORD_CHAR.test(ch)
  while (i < text.length) {
    let matched = false
    for (const [seq, rep] of HE_MULTI) {
      if (text.slice(i, i + seq.length).toLowerCase() === seq) {
        res += rep
        i += seq.length
        matched = true
        break
      }
    }
    if (matched) continue
    const ch = text[i]
    const lower = ch.toLowerCase()
    const prev = i > 0 ? text[i - 1] : undefined
    if (lower in HE_VOWEL_FINAL && ch !== 'T') {
      const next = text[i + 1]
      if (!wordChar(prev)) {
        res += HE_VOWEL_INITIAL[lower]
      } else if (!wordChar(next)) {
        // Trailing vowel: undecided until the next keystroke.
        res += finalize ? HE_VOWEL_FINAL[lower] : ch
      } else {
        // Medial: only long o/u surface, as ו.
        res += HE_VOWEL_MEDIAL[lower] ?? ''
      }
      i++
      continue
    }
    res += HE_SINGLE[ch] ?? HE_SINGLE[lower] ?? ch
    i++
  }
  // Final forms: fold a foldable letter that no word character follows. The
  // very last character is only decided once `finalize` says so.
  return res.replace(/[כמנפצ]/g, (m, idx: number) => {
    const next = res[idx + 1]
    if (next === undefined) return finalize ? HE_FINALS[m] : m
    return HE_WORD_CHAR.test(next) ? m : HE_FINALS[m]
  })
}

// ── Persian ("Finglish") ─────────────────────────────────────────────────────
// Persian shares Arabic's script and its "short vowels aren't written" rule,
// so the positional vowel logic is the same shape as convertAr's. What
// differs: the four Persian-only letters (پ چ ژ گ), aa → آ word-initially,
// and the ZWNJ (nim-fasele) that keeps می‌ attached-but-separate from its
// verb — typed as a hyphen, since a zero-width character has no key.

const FA_MULTI: [string, string][] = [
  ['kh', 'خ'], ['gh', 'ق'], ['ch', 'چ'], ['sh', 'ش'], ['zh', 'ژ'],
  ['aa', 'ا'], ['ee', 'ی'], ['ii', 'ی'], ['oo', 'و'], ['uu', 'و'],
]

const FA_SINGLE: Record<string, string> = {
  b: 'ب', p: 'پ', t: 'ت', s: 'س', j: 'ج', h: 'ه', d: 'د', z: 'ز', r: 'ر',
  f: 'ف', k: 'ک', g: 'گ', l: 'ل', m: 'م', n: 'ن', v: 'و', w: 'و', y: 'ی',
  q: 'ق', "'": 'ع', '3': 'ع',
}

const FA_VOWEL_FINAL: Record<string, string> = {
  a: 'ا', e: 'ه', i: 'ی', o: 'و', u: 'و',
}

const FA_ZWNJ = '‌'
const FA_WORD_CHAR = /[A-Za-z'؀-ۿ]/

function convertFa(rawText: string, finalizePending: boolean): string {
  let text = rawText
  for (const [seq, rep] of [
    ['کh', 'خ'], ['گh', 'ق'], ['چh', 'چ'], ['سh', 'ش'], ['زh', 'ژ'],
  ] as [string, string][]) {
    text = text.split(seq).join(rep)
  }
  let res = ''
  let i = 0
  const wordChar = (ch?: string) => !!ch && FA_WORD_CHAR.test(ch)
  while (i < text.length) {
    const ch = text[i]
    const prev = i > 0 ? text[i - 1] : undefined
    if (ch === '-') {
      res += FA_ZWNJ
      i++
      continue
    }
    let matched = false
    for (const [seq, rep] of FA_MULTI) {
      if (text.slice(i, i + seq.length).toLowerCase() === seq) {
        // Word-initial long â takes the alef-madda seat: آب, not اب.
        res += seq === 'aa' && !wordChar(prev) ? 'آ' : rep
        i += seq.length
        matched = true
        break
      }
    }
    if (matched) continue
    if (ch.toLowerCase() in FA_VOWEL_FINAL) {
      const next = text[i + 1]
      if (!wordChar(prev)) {
        res += 'ا' // word-initial vowel seat
      } else if (!wordChar(next)) {
        res += finalizePending ? FA_VOWEL_FINAL[ch.toLowerCase()] : ch
      }
      // medial short vowel: unwritten, as in Persian orthography
      i++
      continue
    }
    res += FA_SINGLE[ch] ?? FA_SINGLE[ch.toLowerCase()] ?? ch
    i++
  }
  return res
}

// ── Hindi (Devanagari) ───────────────────────────────────────────────────────
// A syllabic IME, not a letter substitution: Devanagari builds each syllable
// from a consonant + a vowel sign (matra), with the inherent "a" written as
// nothing, and consonant clusters joined by a virama (halant). Capitals are
// the retroflex/aspirate set (T D N = ट ड ण, and Sh = ष), matching the
// Arabic scheme's "capitals are the hard letters" convention.
//
// The integration contract re-converts the WHOLE field each keystroke, so
// the field holds committed Devanagari + a trailing Latin run. We decode the
// Devanagari back to a phonetic string (reversible because committed clusters
// always end in a matra or virama — never an ambiguous bare consonant during
// typing), append the pending Latin, and re-encode. A trailing consonant is
// kept PENDING (Latin) until a following letter or `finalize` decides it —
// at submit it becomes the bare glyph, which is how Hindi writes a
// word-final consonant (नाम, not नाम्).

const HI_CONS: [string, string][] = [
  ['chh', 'छ'], ['Rh', 'ढ़'], ['Th', 'ठ'], ['Dh', 'ढ'], ['kh', 'ख'],
  ['gh', 'घ'], ['ch', 'च'], ['jh', 'झ'], ['th', 'थ'], ['dh', 'ध'],
  ['ph', 'फ'], ['bh', 'भ'], ['sh', 'श'], ['Sh', 'ष'], ['ng', 'ङ'],
  ['ny', 'ञ'],
  ['k', 'क'], ['g', 'ग'], ['j', 'ज'], ['T', 'ट'], ['D', 'ड'], ['N', 'ण'],
  ['R', 'ड़'], ['t', 'त'], ['d', 'द'], ['n', 'न'], ['p', 'प'], ['b', 'ब'],
  ['m', 'म'], ['y', 'य'], ['r', 'र'], ['l', 'ल'], ['v', 'व'], ['w', 'व'],
  ['s', 'स'], ['h', 'ह'], ['z', 'ज़'], ['f', 'फ़'], ['q', 'क़'],
]

// vowel grapheme -> [independent letter, matra ("" for inherent a)]
const HI_VOWEL: [string, [string, string]][] = [
  ['aa', ['आ', 'ा']], ['ai', ['ऐ', 'ै']], ['au', ['औ', 'ौ']],
  ['ii', ['ई', 'ी']], ['ee', ['ई', 'ी']], ['uu', ['ऊ', 'ू']],
  ['oo', ['ऊ', 'ू']], ['ri', ['ऋ', 'ृ']],
  ['a', ['अ', '']], ['A', ['आ', 'ा']], ['i', ['इ', 'ि']],
  ['I', ['ई', 'ी']], ['u', ['उ', 'ु']], ['U', ['ऊ', 'ू']],
  ['e', ['ए', 'े']], ['o', ['ओ', 'ो']], ['M', ['ं', 'ं']],
]

const HI_VIRAMA = '्'
// Reverse maps for decoding committed Devanagari back to phonetic.
const HI_CONS_REV: Record<string, string> = {}
for (const [lat, dev] of HI_CONS) if (!(dev in HI_CONS_REV)) HI_CONS_REV[dev] = lat
const HI_MATRA_REV: Record<string, string> = {}
const HI_INDEP_REV: Record<string, string> = {}
for (const [lat, [indep, matra]] of HI_VOWEL) {
  if (matra && !(matra in HI_MATRA_REV)) HI_MATRA_REV[matra] = lat
  if (!(indep in HI_INDEP_REV)) HI_INDEP_REV[indep] = lat
}

const HI_NUKTA = '़' // U+093C, always decomposed after NFD
const HI_NUKTA_REV: Record<string, string> = {
  'ज': 'z', 'फ': 'f', 'क': 'q', 'ड': 'R', 'ढ': 'Rh',
}

/** Decode committed Devanagari (+ passthrough Latin/other) to a phonetic
 * string the encoder can round-trip. Works on NFD so precomposed nukta
 * letters (ड़ etc.) split into base + U+093C and decode uniformly. */
function decodeHi(text: string): string {
  let out = ''
  const chars = Array.from(text.normalize('NFD'))
  for (let i = 0; i < chars.length; i++) {
    const ch = chars[i]
    // nukta loan consonant: base + ़ , optionally + matra/virama
    if (chars[i + 1] === HI_NUKTA && ch in HI_NUKTA_REV) {
      const lat = HI_NUKTA_REV[ch]
      const after = chars[i + 2]
      if (after === HI_VIRAMA) { out += lat; i += 2; continue }
      if (after && after in HI_MATRA_REV) { out += lat + HI_MATRA_REV[after]; i += 2; continue }
      out += lat + 'a'; i++; continue
    }
    if (ch in HI_CONS_REV) {
      const after = chars[i + 1]
      if (after === HI_VIRAMA) { out += HI_CONS_REV[ch]; i++; continue }
      if (after && after in HI_MATRA_REV) { out += HI_CONS_REV[ch] + HI_MATRA_REV[after]; i++; continue }
      out += HI_CONS_REV[ch] + 'a' // bare consonant = inherent a
      continue
    }
    if (ch in HI_INDEP_REV) { out += HI_INDEP_REV[ch]; continue }
    if (ch === 'ं') { out += 'M'; continue }
    out += ch // passthrough (Latin still pending, spaces, punctuation)
  }
  return out
}

/** Encode a phonetic string to Devanagari. When finalize is false the last
 * consonant with no following vowel is left as Latin (pending). */
function encodeHi(phon: string, finalize: boolean): string {
  // tokenize into consonant / vowel / other graphemes
  type Tok = { t: 'c' | 'v' | 'o'; lat: string; dev: string; matra?: string }
  const toks: Tok[] = []
  let i = 0
  const matchAt = (arr: [string, string][] | [string, [string, string]][]) => {
    for (const entry of arr) {
      const seq = entry[0]
      if (phon.slice(i, i + seq.length) === seq) return entry
    }
    return null
  }
  while (i < phon.length) {
    const c = matchAt(HI_CONS) as [string, string] | null
    if (c) { toks.push({ t: 'c', lat: c[0], dev: c[1] }); i += c[0].length; continue }
    const v = matchAt(HI_VOWEL) as [string, [string, string]] | null
    if (v) { toks.push({ t: 'v', lat: v[0], dev: v[1][0], matra: v[1][1] }); i += v[0].length; continue }
    toks.push({ t: 'o', lat: phon[i], dev: phon[i] }); i++
  }
  let out = ''
  for (let k = 0; k < toks.length; k++) {
    const tok = toks[k]
    if (tok.t === 'c') {
      const next = toks[k + 1]
      if (next && next.t === 'v') {
        out += tok.dev + next.matra // consonant + matra (inherent a → '')
        k++
      } else if (next && next.t === 'c') {
        out += tok.dev + HI_VIRAMA // cluster join
      } else {
        // trailing consonant: pending (Latin) until finalize, then bare glyph
        out += finalize ? tok.dev : tok.lat
      }
    } else if (tok.t === 'v') {
      out += tok.dev // independent vowel (word-initial or post-vowel)
    } else {
      out += tok.dev
    }
  }
  return out
}

function convertHi(text: string, finalize: boolean): string {
  return encodeHi(decodeHi(text), finalize)
}

// ── Korean (Hangul) ──────────────────────────────────────────────────────────
// Hangul is ASSEMBLED, not spelled: an initial (L), a medial vowel (V), and an
// optional final (T) fuse into one syllable block by arithmetic —
//   block = 0xAC00 + (L * 21 + V) * 28 + T
// Both entry paths land here. The QWERTY scheme romanizes ("hanguk" → 한국),
// and the on-screen keyboard emits CONJOINING jamo (U+1100 ᄀ, U+1161 ᅡ) which
// render as loose marks until composed — so composeScript() runs the field
// through the same encoder after every keypress.

const KO_L = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
const KO_V = ['ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ','ㅚ','ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ']
// Finals: index 0 is "no final".
const KO_T = ['','ㄱ','ㄲ','ㄳ','ㄴ','ㄵ','ㄶ','ㄷ','ㄹ','ㄺ','ㄻ','ㄼ','ㄽ','ㄾ','ㄿ','ㅀ','ㅁ','ㅂ','ㅄ','ㅅ','ㅆ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']

// Eleven finals are STACKED — two consonants sharing one syllable's bottom
// slot. They were decodable but never assemblable, so every word built on one
// came out broken: 없 ("there isn't", about as common as Korean words get)
// typed 업ㅅ, 앉 typed 안ㅈ, 닭 typed 달ㅋ. The trailing consonant simply fell
// out of the block and sat beside it as a loose jamo.
//
// Splitting is the other half of the contract and is what makes it behave
// like a real IME: a vowel after a stacked final steals the second consonant
// away to open the next syllable (없 + ㅏ → 업사), which the assembly rule
// below gets for free by refusing to stack when a vowel follows.
const KO_COMPOUND_T: Record<string, string> = {
  'ㄱㅅ': 'ㄳ',
  'ㄴㅈ': 'ㄵ', 'ㄴㅎ': 'ㄶ',
  'ㄹㄱ': 'ㄺ', 'ㄹㅁ': 'ㄻ', 'ㄹㅂ': 'ㄼ', 'ㄹㅅ': 'ㄽ',
  'ㄹㅌ': 'ㄾ', 'ㄹㅍ': 'ㄿ', 'ㄹㅎ': 'ㅀ',
  'ㅂㅅ': 'ㅄ',
}
/** The same table read backwards: a stacked final → its two jamo. decodeKo
 * uses it so the encoder only ever sees atomic pieces, which is what lets a
 * following vowel pull the second one off into the next syllable. */
const KO_SPLIT_T: Record<string, string> = Object.fromEntries(
  Object.entries(KO_COMPOUND_T).map(([pair, stacked]) => [stacked, pair]),
)

const KO_SYL_BASE = 0xac00
const KO_SYL_LAST = 0xd7a3
const KO_SILENT_L = KO_L.indexOf('ㅇ') // the placeholder initial for a bare vowel

/** Conjoining jamo (what the on-screen keyboard emits) → the compatibility
 * jamo the tables use. U+1100.. initials, U+1161.. medials, U+11A8.. finals. */
function koNormalizeJamo(ch: string): string {
  const c = ch.codePointAt(0) ?? 0
  if (c >= 0x1100 && c <= 0x1112) return KO_L[c - 0x1100]
  if (c >= 0x1161 && c <= 0x1175) return KO_V[c - 0x1161]
  if (c >= 0x11a8 && c <= 0x11c2) return KO_T[c - 0x11a8 + 1]
  return ch
}

// Typing scheme. Aspirates are the plain Latin stops (k t p ch), the lax
// series is voiced (g d b j), and doubling tenses them (kk tt pp ss jj) —
// the convention every Korean romanization IME uses.
const KO_CONS: [string, string][] = [
  ['kk','ㄲ'], ['gg','ㄲ'], ['tt','ㄸ'], ['dd','ㄸ'], ['pp','ㅃ'], ['bb','ㅃ'],
  ['ss','ㅆ'], ['jj','ㅉ'], ['ch','ㅊ'], ['ng','ㅇ'],
  // kh/th/ph are the same aspirates as bare k/t/p. They exist so that an
  // aspirated FINAL (rare: 부엌, 빛) has a spelling that decodes and
  // re-encodes back to ㅋ/ㅌ/ㅍ instead of collapsing to ㄱ/ㄷ/ㅂ.
  ['kh','ㅋ'], ['th','ㅌ'], ['ph','ㅍ'],
  ['g','ㄱ'], ['n','ㄴ'], ['d','ㄷ'], ['r','ㄹ'], ['l','ㄹ'], ['m','ㅁ'],
  ['b','ㅂ'], ['s','ㅅ'], ['j','ㅈ'], ['k','ㅋ'], ['t','ㅌ'], ['p','ㅍ'],
  ['h','ㅎ'],
]
const KO_VOW: [string, string][] = [
  ['yeo','ㅕ'], ['yae','ㅒ'], ['wae','ㅙ'],
  ['ya','ㅑ'], ['ye','ㅖ'], ['yo','ㅛ'], ['yu','ㅠ'],
  ['eo','ㅓ'], ['eu','ㅡ'], ['ae','ㅐ'], ['oe','ㅚ'], ['ui','ㅢ'],
  ['wa','ㅘ'], ['wo','ㅝ'], ['we','ㅞ'], ['wi','ㅟ'],
  ['a','ㅏ'], ['e','ㅔ'], ['i','ㅣ'], ['o','ㅗ'], ['u','ㅜ'],
]
const KO_VOWEL_START = /[aeiouwy]/

// Romanization is ASYMMETRIC by position: the lax stops are voiced as an
// initial (g d b) and voiceless as a final (k t p) — "hanguk" ends in ㄱ, not
// the aspirated ㅋ that a plain 'k' means at the start of a syllable.
const KO_FINAL: Record<string, string> = {
  k: 'ㄱ', g: 'ㄱ', kk: 'ㄲ', gg: 'ㄲ', n: 'ㄴ', t: 'ㄷ', d: 'ㄷ',
  l: 'ㄹ', r: 'ㄹ', m: 'ㅁ', p: 'ㅂ', b: 'ㅂ', s: 'ㅅ', ss: 'ㅆ',
  ng: 'ㅇ', j: 'ㅈ', ch: 'ㅊ', h: 'ㅎ',
  kh: 'ㅋ', th: 'ㅌ', ph: 'ㅍ',
}

const KO_CONS_REV: Record<string, string> = {}
for (const [lat, jamo] of KO_CONS) if (!(jamo in KO_CONS_REV)) KO_CONS_REV[jamo] = lat
const KO_VOW_REV: Record<string, string> = {}
for (const [lat, jamo] of KO_VOW) if (!(jamo in KO_VOW_REV)) KO_VOW_REV[jamo] = lat

/** Hangul → the string the encoder re-assembles: every syllable is exploded
 * into its JAMO, never back into romanization.
 *
 * Round-tripping through romanization is what made ㄱ/ㄷ/ㅂ finals flip to
 * ㅋ/ㅌ/ㅍ when the next keystroke moved them into an initial slot ("gada"
 * typed 가타). Carrying the jamo itself is lossless in both directions and
 * keeps the aspirated finals (부엌) and stacked ones (없) intact too. */
function decodeKo(text: string): string {
  let out = ''
  for (const raw of Array.from(text)) {
    const ch = koNormalizeJamo(raw)
    const code = ch.codePointAt(0) ?? 0
    if (code >= KO_SYL_BASE && code <= KO_SYL_LAST) {
      const n = code - KO_SYL_BASE
      out += KO_L[Math.floor(n / 588)]
      // Vowels go back to ROMANIZATION: unlike consonants they are
      // unambiguous in that direction, and it's what lets a vowel still grow
      // across keystrokes — ㅔ + "u" has to become ㅡ ("hangeul" → 한글),
      // which a committed jamo could never do.
      out += KO_VOW_REV[KO_V[Math.floor((n % 588) / 28)]] ?? ''
      const t = KO_T[n % 28] // '' when the syllable is open
      out += KO_SPLIT_T[t] ?? t
      continue
    }
    // Standalone jamo: vowels romanize (same reason), consonants stay jamo.
    const plain = KO_VOW_REV[ch] ?? ch
    out += KO_SPLIT_T[plain] ?? plain
  }
  return out
}

// `committed` marks a unit that already exists as Hangul on screen, so the
// encoder must place it rather than hold it back as pending Latin.
type KoTok = { t: 'c' | 'v' | 'o'; lat: string; jamo: string; committed?: boolean }

function tokenizeKo(phon: string): KoTok[] {
  const toks: KoTok[] = []
  let i = 0
  while (i < phon.length) {
    let matched = false
    // Jamo carried over from decode (or typed on the on-screen keyboard).
    const jamo = phon[i]
    if (KO_V.includes(jamo)) {
      toks.push({ t: 'v', lat: jamo, jamo, committed: true })
      i++
      continue
    }
    if (KO_L.includes(jamo) || KO_T.includes(jamo)) {
      toks.push({ t: 'c', lat: jamo, jamo, committed: true })
      i++
      continue
    }
    for (const [seq, jamo] of KO_CONS) {
      if (phon.slice(i, i + seq.length) !== seq) continue
      // "ng" is the final ㅇ — but in "hanguk" the n ends one syllable and the
      // g opens the next, so refuse the digraph when a vowel follows it.
      if (seq === 'ng' && KO_VOWEL_START.test(phon[i + 2] ?? '')) continue
      toks.push({ t: 'c', lat: seq, jamo })
      i += seq.length
      matched = true
      break
    }
    if (matched) continue
    for (const [seq, jamo] of KO_VOW) {
      if (phon.slice(i, i + seq.length) !== seq) continue
      toks.push({ t: 'v', lat: seq, jamo })
      i += seq.length
      matched = true
      break
    }
    if (matched) continue
    toks.push({ t: 'o', lat: phon[i], jamo: phon[i] })
    i++
  }
  return toks
}

function koBlock(l: string, v: string, t: string): string {
  const li = KO_L.indexOf(l)
  const vi = KO_V.indexOf(v)
  const ti = t ? KO_T.indexOf(t) : 0
  if (li < 0 || vi < 0 || ti < 0) return l + v + t
  return String.fromCodePoint(KO_SYL_BASE + (li * 21 + vi) * 28 + ti)
}

/** Phonetic → Hangul blocks. A consonant with no vowel yet stays pending
 * (Latin while typing, the bare jamo once finalized) — the same contract the
 * Hindi encoder uses. */
function encodeKo(phon: string, finalize: boolean): string {
  const toks = tokenizeKo(phon)
  let out = ''
  let i = 0
  while (i < toks.length) {
    const tok = toks[i]
    if (tok.t === 'o') { out += tok.jamo; i++; continue }

    let initial: string | null = null
    if (tok.t === 'c') {
      const next = toks[i + 1]
      if (!next || next.t !== 'v') {
        // No vowel to seat it: pending until the next keystroke decides.
        out += finalize ? tok.jamo : tok.lat
        i++
        continue
      }
      initial = tok.jamo
      i++
    }
    const vowel = toks[i].jamo // guaranteed 'v' here
    i++
    // A following consonant closes THIS syllable only when it isn't the
    // initial of the next one (i.e. no vowel comes after it).
    let final = ''
    const c1 = toks[i]
    if (c1 && c1.t === 'c') {
      const asFinal = c1.committed ? c1.jamo : KO_FINAL[c1.lat] ?? c1.jamo
      const c2 = toks[i + 1]
      if (KO_T.includes(asFinal) && (!c2 || c2.t !== 'v')) {
        // A just-typed consonant at the very END is still ambiguous — it
        // could close this syllable or open the next one, and committing it
        // as a final would decide the aspiration wrongly ("bapo" → 바보).
        // Hold it pending; the next keystroke (or submit) settles it.
        if (c2 || c1.committed || finalize) {
          final = asFinal
          i++
          // A second consonant can stack onto it (ㅂ+ㅅ → ㅄ) — but only if
          // no vowel follows, because a vowel claims that consonant as its
          // own initial instead (없 + ㅏ is 업사, not 없아).
          const d1 = toks[i]
          const d2 = toks[i + 1]
          if (d1 && d1.t === 'c' && (!d2 || d2.t !== 'v')) {
            const stackWith = d1.committed ? d1.jamo : KO_FINAL[d1.lat] ?? d1.jamo
            const stacked = KO_COMPOUND_T[final + stackWith]
            if (stacked && (d2 || d1.committed || finalize)) {
              final = stacked
              i++
            }
          }
        }
      }
    }
    out += koBlock(initial ?? KO_L[KO_SILENT_L], vowel, final)
  }
  return out
}

function convertKo(text: string, finalize: boolean): string {
  return encodeKo(decodeKo(text), finalize)
}

// ── Thai ─────────────────────────────────────────────────────────────────────
// Thai vowels WRAP their consonant — before it, after it, above, below, or on
// several sides at once — so each vowel is stored as a TEMPLATE with `_` where
// the initial consonant goes ("e" → "เ_", "ia" → "เ_ีย"). Tone marks (typed as
// digits 1-4) sit directly on the initial, i.e. immediately after `_`.

const TH_CONS: [string, string][] = [
  ['kh','ข'], ['ch','ช'], ['th','ท'], ['ph','พ'], ['ng','ง'],
  ['k','ก'], ['j','จ'], ['s','ส'], ['y','ย'], ['d','ด'], ['t','ต'],
  ['n','น'], ['b','บ'], ['p','ป'], ['f','ฟ'], ['m','ม'], ['r','ร'],
  ['l','ล'], ['w','ว'], ['h','ห'],
]
// Longest romanization first; the template's `_` is the initial consonant.
const TH_VOW: [string, string][] = [
  ['uea','เ_ือ'], ['oe','เ_อ'], ['ia','เ_ีย'], ['ua','_ัว'],
  ['ae','แ_'], ['ao','เ_า'], ['ai','ไ_'], ['am','_ำ'], ['or','_อ'],
  ['ue','_ือ'], ['aa','_า'], ['ii','_ี'], ['uu','_ู'],
  ['a','_ะ'], ['i','_ิ'], ['u','_ุ'], ['e','เ_'], ['o','โ_'],
]
const TH_TONES: Record<string, string> = { '1': '่', '2': '้', '3': '๊', '4': '๋' }
const TH_CARRIER = 'อ' // seats a vowel with no consonant of its own

const TH_CONS_REV: Record<string, string> = {}
for (const [lat, th] of TH_CONS) if (!(th in TH_CONS_REV)) TH_CONS_REV[th] = lat
const TH_TONE_REV: Record<string, string> = {}
for (const [digit, mark] of Object.entries(TH_TONES)) TH_TONE_REV[mark] = digit
// Decode tries the longest rendered template first so "เ_ีย" wins over "เ_".
const TH_VOW_BY_LEN = [...TH_VOW].sort((a, b) => b[1].length - a[1].length)

/** Thai → the phonetic string the encoder round-trips. Templates are matched
 * with `_` as a single-consonant wildcard (plus an optional tone mark), which
 * is what makes the wrapped vowels invertible. */
function decodeTh(text: string): string {
  let out = ''
  let i = 0
  while (i < text.length) {
    let matched = false
    for (const [lat, template] of TH_VOW_BY_LEN) {
      const [before, after] = template.split('_')
      if (text.slice(i, i + before.length) !== before) continue
      let j = i + before.length
      const cons = text[j]
      // The slot holds a real consonant or the bare carrier (a vowel with no
      // consonant of its own) — the carrier romanizes to nothing and the
      // encoder puts it back.
      if (!cons || !(cons in TH_CONS_REV || cons === TH_CARRIER)) continue
      j += 1
      let tone = ''
      if (text[j] && text[j] in TH_TONE_REV) { tone = TH_TONE_REV[text[j]]; j += 1 }
      if (text.slice(j, j + after.length) !== after) continue
      out += (cons === TH_CARRIER ? '' : TH_CONS_REV[cons]) + lat + tone
      i = j + after.length
      matched = true
      break
    }
    if (matched) continue
    const ch = text[i]
    if (ch === TH_CARRIER) { i++; continue } // stray carrier: re-added on encode
    if (ch in TH_CONS_REV) { out += TH_CONS_REV[ch]; i++; continue }
    if (ch in TH_TONE_REV) { out += TH_TONE_REV[ch]; i++; continue }
    out += ch // passthrough
    i++
  }
  return out
}

type ThTok = { t: 'c' | 'v' | 'tone' | 'o'; lat: string; out: string }

function tokenizeTh(phon: string): ThTok[] {
  const toks: ThTok[] = []
  let i = 0
  while (i < phon.length) {
    let matched = false
    for (const [seq, th] of TH_CONS) {
      if (phon.slice(i, i + seq.length) !== seq) continue
      toks.push({ t: 'c', lat: seq, out: th })
      i += seq.length
      matched = true
      break
    }
    if (matched) continue
    for (const [seq, template] of TH_VOW) {
      if (phon.slice(i, i + seq.length) !== seq) continue
      toks.push({ t: 'v', lat: seq, out: template })
      i += seq.length
      matched = true
      break
    }
    if (matched) continue
    const ch = phon[i]
    toks.push({ t: ch in TH_TONES ? 'tone' : 'o', lat: ch, out: TH_TONES[ch] ?? ch })
    i++
  }
  return toks
}

/** Phonetic → Thai. Each syllable is [consonant] vowel [tone] [final]; the
 * vowel's template decides where the consonant actually lands. A trailing
 * consonant with no vowel stays pending, as in the Hindi/Korean encoders. */
function encodeTh(phon: string, finalize: boolean): string {
  const toks = tokenizeTh(phon)
  let out = ''
  let i = 0
  while (i < toks.length) {
    const tok = toks[i]
    if (tok.t === 'o' || tok.t === 'tone') { out += tok.out; i++; continue }

    let initial: string | null = null
    if (tok.t === 'c') {
      const next = toks[i + 1]
      if (!next || next.t !== 'v') {
        out += finalize ? tok.out : tok.lat
        i++
        continue
      }
      initial = tok.out
      i++
    }
    const template = toks[i].out
    i++
    let tone = ''
    if (toks[i]?.t === 'tone') { tone = toks[i].out; i++ }
    out += template.replace('_', (initial ?? TH_CARRIER) + tone)
    // A consonant that isn't opening the next syllable closes this one.
    const c1 = toks[i]
    if (c1 && c1.t === 'c' && toks[i + 1]?.t !== 'v') {
      out += c1.out
      i++
    }
  }
  return out
}

function convertTh(text: string, finalize: boolean): string {
  return encodeTh(decodeTh(text), finalize)
}

// ── Public API ───────────────────────────────────────────────────────────────

/** Convert as-you-type. Idempotent on already-converted text. */
export function convertTranslit(code: string, text: string): string {
  switch (code) {
    case 'ru':
      return convertRu(text)
    case 'el':
      return convertEl(text)
    case 'ar':
      return convertAr(text, false)
    case 'he':
      return convertHe(text, false)
    case 'fa':
      return convertFa(text, false)
    case 'hi':
      return convertHi(text, false)
    case 'th':
      return convertTh(text, false)
    case 'ko':
      return convertKo(text, false)
    default:
      return text
  }
}

/** Assemble typed units into their composed glyphs.
 *
 * The on-screen keyboard inserts raw glyphs straight into the field, bypassing
 * the QWERTY path — fine for alphabets, broken for Hangul, whose keys are
 * jamo that must fuse into syllable blocks (ᄒ ᅡ ᄂ → 한). Keyboard handlers
 * run their result through here; every other script is returned untouched. */
export function composeScript(code: string, text: string): string {
  return code === 'ko' ? convertKo(text, true) : text
}

/** Resolve anything left pending (Arabic trailing vowels, Hindi trailing
 * consonants) at submit time. */
export function finalizeTranslit(code: string, text: string): string {
  if (code === 'ar') return convertAr(text, true)
  if (code === 'he') return convertHe(text, true)
  if (code === 'fa') return convertFa(text, true)
  if (code === 'hi') return convertHi(text, true)
  if (code === 'th') return convertTh(text, true)
  if (code === 'ko') return convertKo(text, true)
  return convertTranslit(code, text)
}

export function isTranslitEnabled(
  code: string,
  prefs: Record<string, boolean>,
): boolean {
  return hasTranslit(code) && (prefs[code] ?? true)
}

/** Finalize the typed answer iff QWERTY input is on for this language. */
export function finalizeInput(
  code: string,
  text: string,
  prefs: Record<string, boolean>,
): string {
  return isTranslitEnabled(code, prefs) ? finalizeTranslit(code, text) : text
}

export function translitGuide(code: string): GuideRow[] {
  switch (code) {
    case 'ru':
      return [
        { keys: 'a b v g d e', out: 'а б в г д е' },
        { keys: 'z i j k l m n', out: 'з и й к л м н' },
        { keys: 'o p r s t u f', out: 'о п р с т у ф' },
        { keys: 'h / x', out: 'х' },
        { keys: 'c / ts', out: 'ц' },
        { keys: 'zh ch sh shch', out: 'ж ч ш щ' },
        { keys: 'y', out: 'ы' },
        { keys: 'yo yu ya', out: 'ё ю я' },
        { keys: "e'", out: 'э' },
        { keys: "' ''", out: 'ь ъ', note: 'soft / hard sign' },
      ]
    case 'ar':
      return [
        { keys: 'b t j d r z s f q k l m n h w y', out: 'ب ت ج د ر ز س ف ق ك ل م ن ه و ي' },
        { keys: 'th kh dh sh gh', out: 'ث خ ذ ش غ' },
        { keys: 'S D T Z', out: 'ص ض ط ظ', note: 'capitals = emphatic letters' },
        { keys: '3  7  2', out: 'ع ح ء', note: "chat digits; ' also = ء" },
        { keys: 'aa ii uu', out: 'ا ي و', note: 'double a vowel to write it long (kitaab → كتاب)' },
        { keys: 'a i u (middle)', out: '—', note: 'short vowels are not written' },
        { keys: 'a i u (start)', out: 'ا', note: 'word-initial vowels sit on alif' },
        { keys: 'ah (end)', out: 'ة', note: 'taa marbuta (madrasah → مدرسة)' },
      ]
    case 'he':
      return [
        { keys: 'a b g d h v z y k l m n s p q r t', out: 'א ב ג ד ה ו ז י כ ל מ נ ס פ ק ר ת' },
        { keys: 'sh ts / tz ch kh', out: 'ש צ ח כ' },
        { keys: 'e', out: 'ע', note: 'ayin' },
        { keys: 'T', out: 'ט', note: 'capital T = tet (t = tav)' },
        { keys: 'o u v w', out: 'ו', note: 'vav does duty as o/u/v' },
        { keys: 'i y', out: 'י' },
        { keys: 'k m n p ts (end)', out: 'ך ם ן ף ץ', note: 'final forms appear automatically at the end of a word' },
      ]
    case 'fa':
      return [
        { keys: 'b p t s j d z r f k g l m n v y', out: 'ب پ ت س ج د ز ر ف ک گ ل م ن و ی' },
        { keys: 'kh gh ch sh zh', out: 'خ ق چ ش ژ' },
        { keys: 'h', out: 'ه' },
        { keys: "' / 3", out: 'ع' },
        { keys: 'aa (start)', out: 'آ', note: 'aab → آب' },
        { keys: 'aa ii uu', out: 'ا ی و', note: 'double a vowel to write it long' },
        { keys: 'a e o (middle)', out: '—', note: 'short vowels are not written' },
        { keys: '-', out: '‌', note: 'nim-fasele (ZWNJ): mi-ravam → می‌روم' },
      ]
    case 'el':
      return [
        { keys: 'a v/b g d e z', out: 'α β γ δ ε ζ' },
        { keys: 'h i k l m n', out: 'η ι κ λ μ ν' },
        { keys: 'x o p r s t', out: 'ξ ο π ρ σ τ' },
        { keys: 'u/y f w', out: 'υ φ ω' },
        { keys: 'th ch ps', out: 'θ χ ψ' },
        { keys: 's (end of word)', out: 'ς', note: 'final sigma is automatic' },
      ]
    case 'hi':
      return [
        { keys: 'k g j t d n p b m', out: 'क ग ज त द न प ब म' },
        { keys: 'y r l v s h', out: 'य र ल व स ह' },
        { keys: 'kh gh ch chh jh', out: 'ख घ च छ झ' },
        { keys: 'th dh ph bh sh', out: 'थ ध फ भ श' },
        { keys: 'T D N Th Dh Sh', out: 'ट ड ण ठ ढ ष', note: 'capitals = retroflex/hard letters' },
        { keys: 'z f q', out: 'ज़ फ़ क़', note: 'nuqta loan sounds' },
        { keys: 'a aa i ii u uu', out: 'अ आ इ ई उ ऊ', note: 'double a vowel to lengthen (raam → राम)' },
        { keys: 'e o ai au ri', out: 'ए ओ ऐ औ ऋ' },
        { keys: 'namaste', out: 'नमस्ते', note: 'consonants join automatically; M = ं (anusvara)' },
      ]
    case 'th':
      return [
        { keys: 'k j d t b p f m n r l w s y h', out: 'ก จ ด ต บ ป ฟ ม น ร ล ว ส ย ห' },
        { keys: 'kh ch th ph ng', out: 'ข ช ท พ ง', note: 'add h for the breathy pair' },
        { keys: 'a aa i ii u uu', out: 'ะ า ิ ี ุ ู', note: 'double a vowel to lengthen' },
        { keys: 'e ae o or oe', out: 'เ- แ- โ- -อ เ-อ' },
        { keys: 'ai ao am ia ua uea', out: 'ไ- เ-า -ำ เ-ีย -ัว เ-ือ' },
        { keys: '1 2 3 4', out: '่ ้ ๊ ๋', note: 'tone marks — type the digit after the vowel' },
        { keys: 'maa', out: 'มา', note: 'the vowel wraps itself around the consonant' },
        { keys: 'maa2', out: 'ม้า', note: 'máa (horse) — the tone mark lands on the м' },
        { keys: 'khaao', out: 'เขา', note: 'a leading vowel writes BEFORE the consonant you say it after' },
      ]
    case 'ko':
      return [
        { keys: 'g n d r m b s j h', out: 'ㄱ ㄴ ㄷ ㄹ ㅁ ㅂ ㅅ ㅈ ㅎ' },
        { keys: 'k t p ch', out: 'ㅋ ㅌ ㅍ ㅊ', note: 'the plain stops are the ASPIRATED ones' },
        { keys: 'kk tt pp ss jj', out: 'ㄲ ㄸ ㅃ ㅆ ㅉ', note: 'double it for the tense set' },
        { keys: 'a eo o u eu i', out: 'ㅏ ㅓ ㅗ ㅜ ㅡ ㅣ' },
        { keys: 'ae e ya yeo yo yu', out: 'ㅐ ㅔ ㅑ ㅕ ㅛ ㅠ' },
        { keys: 'wa wo wi oe ui', out: 'ㅘ ㅝ ㅟ ㅚ ㅢ' },
        { keys: 'ng', out: 'ㅇ', note: 'the final ㅇ (sarang → 사랑); a word-initial vowel gets it free' },
        { keys: 'hanguk', out: '한국', note: 'letters stack into blocks by themselves' },
        { keys: 'an', out: '안', note: 'a bare vowel is seated on ㅇ automatically' },
      ]
    default:
      return []
  }
}
