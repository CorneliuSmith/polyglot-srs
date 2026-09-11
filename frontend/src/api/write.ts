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
  allowance: TutorAllowance
}

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
}): Promise<WriteAssessment> {
  const form = new FormData()
  form.append('image', args.image, 'ink.png')
  form.append('language_id', args.languageId)
  form.append('kind', args.kind)
  if (args.expected) form.append('expected', args.expected)
  if (args.style) form.append('style', args.style)
  const response = await apiClient.post<WriteAssessment>('/api/write/assess', form)
  return response.data
}
