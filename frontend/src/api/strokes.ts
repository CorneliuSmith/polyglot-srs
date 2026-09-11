import apiClient from './client'

/** The stroke library (docs/plans/handwriting.md, §5–6). Strokes are
 * ordered point lists in a 1000×1000 box, [x, y] per point. */
export type GlyphStrokes = number[][][]

export interface AlphabetLetter {
  glyph: string
  romanization: string
  sound: string
  forms: string[]
}

export interface Alphabet {
  code: string
  script: string
  styles: string[]
  letters: AlphabetLetter[]
}

export interface Glyph {
  id: string
  script: string
  glyph: string
  form: string
  style: string
  strokes: GlyphStrokes
  joins: { entry?: number[]; exit?: number[]; joins_next?: boolean }
  hints: string[]
  source: string
  reviewed: boolean
}

export interface Exemplar {
  id: string
  script: string
  language_code: string
  style: string
  text: string
  strokes: GlyphStrokes
  source: string
  reviewed: boolean
}

export interface StrokeManifest {
  script: string
  available: boolean
  expected_forms: number
  alphabet_size: number
  styles: Record<string, { authored: number; reviewed: number; exemplars: number; exemplars_reviewed: number }>
}

export async function getAlphabet(languageId: string): Promise<Alphabet> {
  const r = await apiClient.get<Alphabet>('/api/write/alphabet', { params: { language_id: languageId } })
  return r.data
}

export async function getStrokeManifest(languageId: string): Promise<StrokeManifest> {
  const r = await apiClient.get<StrokeManifest>('/api/write/manifest', { params: { language_id: languageId } })
  return r.data
}

/** Reviewed only — what a learner traces. */
export async function getGlyphs(languageId: string, style?: string) {
  const r = await apiClient.get<{ script: string; glyphs: Glyph[]; exemplars: Exemplar[] }>(
    '/api/write/glyphs', { params: { language_id: languageId, style } },
  )
  return r.data
}

/** Drafts included — the Workshop's grid. */
export async function listStrokes(languageId: string, style?: string) {
  const r = await apiClient.get<{ script: string; glyphs: Glyph[]; exemplars: Exemplar[] }>(
    '/api/contribute/strokes', { params: { language_id: languageId, style } },
  )
  return r.data
}

export async function saveGlyph(args: {
  languageId: string
  glyph: string
  form: string
  style: string
  strokes: GlyphStrokes
  joins?: Glyph['joins']
  hints?: string[]
}): Promise<Glyph> {
  const r = await apiClient.put<Glyph>('/api/contribute/strokes', {
    language_id: args.languageId, glyph: args.glyph, form: args.form, style: args.style,
    strokes: args.strokes, joins: args.joins ?? {}, hints: args.hints ?? [],
  })
  return r.data
}

export async function reviewGlyph(id: string, languageId: string, reviewed = true): Promise<void> {
  await apiClient.post(`/api/contribute/strokes/${id}/review`, null, {
    params: { language_id: languageId, reviewed },
  })
}

export async function deleteGlyph(id: string, languageId: string): Promise<void> {
  await apiClient.delete(`/api/contribute/strokes/${id}`, { params: { language_id: languageId } })
}

export async function saveExemplar(args: {
  languageId: string
  style: string
  text: string
  strokes: GlyphStrokes
}): Promise<Exemplar> {
  const r = await apiClient.put<Exemplar>('/api/contribute/exemplars', {
    language_id: args.languageId, style: args.style, text: args.text, strokes: args.strokes,
  })
  return r.data
}

export async function reviewExemplar(id: string, languageId: string, reviewed = true): Promise<void> {
  await apiClient.post(`/api/contribute/exemplars/${id}/review`, null, {
    params: { language_id: languageId, reviewed },
  })
}

export async function deleteExemplar(id: string, languageId: string): Promise<void> {
  await apiClient.delete(`/api/contribute/exemplars/${id}`, { params: { language_id: languageId } })
}

/** Guided Letters progress (Phase 3): per reviewed form, the learner's
 * attempts and passes from the Write step; known after three passes. */
export interface LetterProgress {
  glyph_id: string
  attempts: number
  passes: number
  best_score: number
  known: boolean
  last_at?: string | null
}

export async function getLettersProgress(languageId: string, style?: string): Promise<LetterProgress[]> {
  const r = await apiClient.get<{ items: LetterProgress[] }>('/api/write/progress', {
    params: { language_id: languageId, style },
  })
  return r.data.items
}

export async function recordLetterAttempt(args: {
  languageId: string
  glyphId: string
  passed: boolean
  score: number
}): Promise<LetterProgress> {
  const r = await apiClient.post<LetterProgress>('/api/write/progress', {
    language_id: args.languageId, glyph_id: args.glyphId, passed: args.passed, score: args.score,
  })
  return r.data
}

/** Several forms at once — a traced word or line's Write step, one
 * attempt per letter form it contains. */
export async function recordLetterAttempts(args: {
  languageId: string
  attempts: { glyphId: string; passed: boolean; score: number }[]
}): Promise<LetterProgress[]> {
  const r = await apiClient.post<{ items: LetterProgress[] }>('/api/write/progress/batch', {
    language_id: args.languageId,
    attempts: args.attempts.map((a) => ({ glyph_id: a.glyphId, passed: a.passed, score: a.score })),
  })
  return r.data.items
}
