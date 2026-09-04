/**
 * The part of a grammar-point title that is in the language being studied.
 *
 * Titles are written for the eye, mixing the course language with English:
 * "Il y a — there is / there are", "Subject pronouns (ik, jij, u…)",
 * "Zijn — present (ben, bent, is, zijn)". The speaker button read the whole
 * string in the course voice, so "there is / there are" came out in a
 * French accent (owner, 4 Sep 2026). Speak only the target-language piece.
 *
 * Nothing here knows what language a word is in; it reads the CONVENTIONS
 * the titles follow (data/grammar, ~1,260 points):
 *   1. "(…)" holds course-language forms or an example — speak that; if it
 *      carries its own " — gloss", speak what precedes the dash.
 *   2. "target — gloss": speak what precedes the dash.
 *   3. "English: a, b, c…" lists forms after the colon — speak them; a
 *      colon followed by a clause ("Word order: the verb comes second") is
 *      English and is not spoken.
 *   4. A plain English title has nothing to say: null, and the caller
 *      hides the button rather than mispronounce a description.
 * Vocabulary titles are the word itself and never come through here.
 */
export function spokenTitle(title: string): string | null {
  const t = title.trim()
  if (!t) return null

  const paren = /\(([^()]+)\)/.exec(t)
  if (paren) {
    const inner = paren[1].trim()
    const before = inner.split(/\s+[—–-]\s+/)[0].trim()
    return clean(before)
  }
  if (/\s[—–]\s/.test(t)) {
    return clean(t.split(/\s[—–]\s/)[0])
  }
  const colon = t.indexOf(':')
  if (colon !== -1) {
    const after = t.slice(colon + 1).trim()
    // A list of forms, or a single word — not an English clause.
    if (after.includes(',') || !/\s/.test(after)) return clean(after)
  }
  return null
}

function clean(s: string): string | null {
  const out = s.replace(/[…]+$/g, '').trim()
  return out || null
}
