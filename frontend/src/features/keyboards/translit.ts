/**
 * QWERTY transliteration input ("type privet, get привет").
 *
 * For the non-Latin-script languages a learner without a Russian/Arabic/Greek
 * keyboard can type standard romanization on QWERTY and the answer blank
 * converts as they type. Schemes follow the common conventions
 * (translit.ru-style for Russian, chat-alphabet digits for Arabic, Greeklish
 * for Greek) and every mapping is viewable in the in-app key guide.
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
 */

export const TRANSLIT_LANGS = ['ru', 'ar', 'el', 'hi'] as const

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
    case 'hi':
      return convertHi(text, false)
    default:
      return text
  }
}

/** Resolve anything left pending (Arabic trailing vowels, Hindi trailing
 * consonants) at submit time. */
export function finalizeTranslit(code: string, text: string): string {
  if (code === 'ar') return convertAr(text, true)
  if (code === 'hi') return convertHi(text, true)
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
    default:
      return []
  }
}
