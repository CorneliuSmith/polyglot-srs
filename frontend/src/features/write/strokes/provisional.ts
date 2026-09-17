import type { Glyph } from '../../../api/strokes'
import arabic from './arabic.json'
import cyrillic from './cyrillic.json'
import devanagari from './devanagari.json'
import greek from './greek.json'
import hangul from './hangul.json'
import hebrew from './hebrew.json'
import latin from './latin.json'
import thai from './thai.json'

/**
 * The PROVISIONAL stroke library (docs/plans/handwriting.md, §13): each
 * letter form's centreline, traced from a standard font of the script's
 * teaching hand (Noto Naskh for Arabic, Marck Script for Russian cursive,
 * Dancing Script for Latin cursive, Noto Sans for the print faces) by
 * scripts/strokes/gen_from_fonts.py, with a textbook stroke order and
 * direction guessed by rule. Bundled so the guided modes teach a shape
 * that looks like the writing learners actually meet before a speaker
 * has traced the script — and before migration 20261025 has put the
 * same rows in the database. A form the server knows always wins; a
 * bundled one has an id the server will not accept, so nothing is
 * recorded against it.
 */
interface Bundle { script: string; glyphs: Omit<Glyph, 'id'>[] }
const BUNDLES: Record<string, Bundle> = {
  arabic: arabic as Bundle,
  cyrillic: cyrillic as Bundle,
  devanagari: devanagari as Bundle,
  greek: greek as Bundle,
  hangul: hangul as Bundle,
  hebrew: hebrew as Bundle,
  latin: latin as Bundle,
  thai: thai as Bundle,
}

export function isProvisionalId(id: string): boolean {
  return id.startsWith('prov:')
}

/** Server glyphs first; bundled forms fill the gaps for this style. */
export function withProvisional(script: string, style: string, glyphs: Glyph[]): Glyph[] {
  const bundle = BUNDLES[script]
  if (!bundle) return glyphs
  const have = new Set(glyphs.map((g) => `${g.glyph}|${g.form}`))
  const extra = bundle.glyphs
    .filter((g) => g.style === style && !have.has(`${g.glyph}|${g.form}`))
    .map((g) => ({ ...g, id: `prov:${script}|${g.glyph}|${g.form}|${style}` } as Glyph))
  return extra.length ? [...glyphs, ...extra] : glyphs
}
