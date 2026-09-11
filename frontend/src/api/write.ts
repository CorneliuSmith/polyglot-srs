import apiClient from './client'
import type { TutorAllowance } from './tutor'

/** Something to write. `prompt` is in the learner's own language (the
 * support-locale meaning line); `answer` is the course-language text the
 * assessor will expect. `source` says whether it came from their own cards
 * or the course's beginner lines. */
export interface WritePrompt {
  prompt: string
  answer: string
  source: 'own' | 'course'
}

export type WriteKind = 'sentence' | 'word' | 'free'
export type WriteStyle = 'print' | 'cursive'

export interface WriteStatus {
  available: boolean
  allowance: TutorAllowance | null
}

export interface WordDiff {
  expected: string
  written: string
  note: string
}

export interface LetterformNote {
  letter: string
  note: string
}

/** What the reader saw. `transcription` is always present — it is how a
 * misread shows itself as a misread rather than as a fail. */
export interface WriteAssessment {
  transcription: string
  matches_target: boolean
  word_diffs: WordDiff[]
  legibility: number
  letterform_notes: LetterformNote[]
  confidence: 'low' | 'medium' | 'high'
  expected: string | null
  /** Whether the reader is learning this writer's hand (the Account
   * toggle, and the migration being present). Decides whether a confirm
   * button is offered. */
  adapt: boolean
  /** How many times each noted letter had been noted before — "your д
   * again, third time" — for letters with a history. */
  again: Record<string, number>
  allowance: TutorAllowance
}

/** The accuracy line and the letters to watch, by the writer's verdicts. */
export interface HandReadout {
  right: number
  wrong: number
  total: number
  letters_to_watch: { letter: string; count: number }[]
  legibility_mean: number | null
  history: number[]
  /** The writer's usual, from their baseline session — the yardstick
   * the neatness panel uses when present (§12 D). */
  baseline_neatness?: {
    drift: number
    wobble: number
    sizeCv: number
    slantSd: number | null
    spacingCv: number | null
    clusters: number
  } | null
}

export interface Misread {
  wrote: string
  read: string
}

/** What the reader knows about one writer in one language. */
export interface HandProfile {
  available: boolean
  adapt: boolean
  habits: { letter: string; note: string; count: number; confirmed_ok: boolean }[]
  stats: { n?: number; legibility_mean?: number }
  samples: number
  confirmed: number
  readout: HandReadout
}

/** Strokes as the server keeps them: integer [x, y, t] triples. */
export type CompactStrokes = number[][][]

export async function getWriteStatus(languageId: string): Promise<WriteStatus> {
  const response = await apiClient.get<WriteStatus>('/api/write/status', {
    params: { language_id: languageId },
  })
  return response.data
}

export async function getWritePrompts(
  languageId: string,
  kind: 'sentence' | 'word',
): Promise<WritePrompt[]> {
  const response = await apiClient.get<{ kind: string; items: WritePrompt[] }>(
    '/api/write/prompts',
    { params: { language_id: languageId, kind, limit: 20 } },
  )
  return response.data.items
}

export async function assessWriting(args: {
  languageId: string
  image: Blob
  expected: string | null
  kind: WriteKind
  style: WriteStyle | null
  /** How the ink was made — kept with a sample and told to the reader. */
  strokes?: CompactStrokes
}): Promise<WriteAssessment> {
  const form = new FormData()
  form.append('image', args.image, 'ink.png')
  form.append('language_id', args.languageId)
  form.append('kind', args.kind)
  if (args.expected) form.append('expected', args.expected)
  if (args.style) form.append('style', args.style)
  if (args.strokes?.length) form.append('strokes', JSON.stringify(args.strokes))
  const response = await apiClient.post<WriteAssessment>('/api/write/assess', form)
  return response.data
}

/** "I wrote this": the canvas becomes a confirmed sample of the writer's
 * hand and the flagged letters become known-fine. Costs nothing. */
export interface ConfirmResult {
  kept: boolean
  samples: number
  reason?: string
  /** Present when `read` was sent: the writer's verdict on that reading. */
  right?: boolean
  misread?: Misread[]
  readout?: HandReadout
}

export async function confirmWriting(args: {
  languageId: string
  image: Blob
  text: string
  letters: string[]
  strokes?: CompactStrokes
  /** What the reader had said — so the server can record right / wrong
   * and count the misread letters. */
  read?: string
  /** 'baseline' during a baseline session: kept as such, preferred as a
   * reference and replaced by a redo. */
  source?: 'confirm' | 'baseline'
}): Promise<ConfirmResult> {
  const form = new FormData()
  form.append('image', args.image, 'ink.png')
  form.append('language_id', args.languageId)
  form.append('text', args.text)
  if (args.letters.length) form.append('letters', args.letters.join(','))
  if (args.strokes?.length) form.append('strokes', JSON.stringify(args.strokes))
  if (args.read !== undefined) form.append('read', args.read)
  if (args.source) form.append('source', args.source)
  const response = await apiClient.post<ConfirmResult>('/api/write/confirm', form)
  return response.data
}

export async function getHandProfile(languageId: string): Promise<HandProfile> {
  const response = await apiClient.get<HandProfile>('/api/write/profile', {
    params: { language_id: languageId },
  })
  return response.data
}

export async function setHandAdapt(adapt: boolean): Promise<void> {
  await apiClient.put('/api/write/profile', { adapt })
}

export async function resetHand(languageId?: string): Promise<void> {
  await apiClient.post('/api/write/profile/reset', { language_id: languageId ?? null })
}

/** The baseline session (§12.2): the prompts, how much of the script
 * they cover, and whether one may run today. */
export interface WriteBaseline {
  available: boolean
  allowed: boolean
  adapt: boolean
  last: string | null
  prompts: WritePrompt[]
  covered: number
  total: number
}

export async function getWriteBaseline(languageId: string): Promise<WriteBaseline> {
  const response = await apiClient.get<WriteBaseline>('/api/write/baseline', {
    params: { language_id: languageId },
  })
  return response.data
}

export async function finishWriteBaseline(args: {
  languageId: string
  covered: number
  total: number
  /** The average of the eight lines' raw neatness measures — the writer's usual. */
  neatness?: HandReadout['baseline_neatness']
}): Promise<{ baseline_at: string | null; baselines: number }> {
  const response = await apiClient.post<{ baseline_at: string | null; baselines: number }>(
    '/api/write/baseline/done',
    {
      language_id: args.languageId, covered: args.covered, total: args.total,
      neatness: args.neatness ?? null,
    },
  )
  return response.data
}

