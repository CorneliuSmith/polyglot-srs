import { BOX, toGlyphBox } from './glyphBox'
import type { Stroke } from './ink'

/**
 * The stroke matcher (docs/plans/handwriting.md, §4.1): a learner's ink
 * against an authored template, on the device, exact and free.
 *
 * Both are normalised into the same 1000×1000 box (size and placement
 * never matter), resampled to a fixed number of points, and compared
 * stroke by stroke in order: count, direction (is the start nearer the
 * template's start than its end?), shape (dynamic-time-warped mean
 * distance, so a slow start does not skew it), and order (does this
 * stroke fit a different template stroke much better?). Every failure
 * names the stroke and the reason, which is what the guided Trace and
 * Write steps say back.
 *
 * Tolerance is a fraction of the box: Trace is loose, Write tighter.
 */
export type Reason = 'missing' | 'extra' | 'direction' | 'shape' | 'order'

export interface StrokeVerdict {
  index: number
  ok: boolean
  reason?: Reason
  /** 0 (nothing like it) to 1 (identical). */
  score: number
}

export interface MatchResult {
  ok: boolean
  score: number
  strokes: StrokeVerdict[]
  countOk: boolean
}

export interface MatchOptions {
  /** Shape distance allowed, as a fraction of the box; 0.16 for Trace, 0.10 for Write (LettersMode). */
  tolerance?: number
  points?: number
}

const DEFAULTS: Required<MatchOptions> = { tolerance: 0.1, points: 32 }

type Pt = number[]

function dist(a: Pt, b: Pt): number {
  return Math.hypot(a[0] - b[0], a[1] - b[1])
}

/** Evenly spaced points along a stroke, by arc length. */
export function resample(stroke: Pt[], n: number): Pt[] {
  if (stroke.length === 0) return []
  if (stroke.length === 1) return Array.from({ length: n }, () => [...stroke[0]])
  const total = stroke.slice(1).reduce((s, p, i) => s + dist(stroke[i], p), 0)
  if (total === 0) return Array.from({ length: n }, () => [...stroke[0]])
  const out: Pt[] = [[...stroke[0]]]
  const step = total / (n - 1)
  let acc = 0
  let i = 1
  let prev = stroke[0]
  while (out.length < n - 1 && i < stroke.length) {
    const seg = dist(prev, stroke[i])
    if (acc + seg >= step) {
      const t = (step - acc) / seg
      const p = [prev[0] + (stroke[i][0] - prev[0]) * t, prev[1] + (stroke[i][1] - prev[1]) * t]
      out.push(p)
      prev = p
      acc = 0
    } else {
      acc += seg
      prev = stroke[i]
      i++
    }
  }
  while (out.length < n) out.push([...stroke[stroke.length - 1]])
  return out
}

/** Mean point distance under dynamic time warping. */
export function dtw(a: Pt[], b: Pt[]): number {
  const n = a.length
  const m = b.length
  if (n === 0 || m === 0) return Infinity
  const cost = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(Infinity))
  cost[0][0] = 0
  for (let i = 1; i <= n; i++) {
    for (let j = 1; j <= m; j++) {
      const d = dist(a[i - 1], b[j - 1])
      cost[i][j] = d + Math.min(cost[i - 1][j], cost[i][j - 1], cost[i - 1][j - 1])
    }
  }
  return cost[n][m] / Math.max(n, m)
}

/** Template strokes re-normalised into the box (an authored glyph is
 * already there; a learner's ink comes through toGlyphBox). */
export function normaliseBox(strokes: Pt[][]): Pt[][] {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  for (const s of strokes) for (const [x, y] of s) {
    if (x < minX) minX = x
    if (y < minY) minY = y
    if (x > maxX) maxX = x
    if (y > maxY) maxY = y
  }
  if (!isFinite(minX)) return []
  const w = Math.max(1, maxX - minX)
  const h = Math.max(1, maxY - minY)
  const scale = (BOX * 0.9) / Math.max(w, h)
  const ox = (BOX - w * scale) / 2
  const oy = (BOX - h * scale) / 2
  return strokes.map((s) => s.map(([x, y]) => [ox + (x - minX) * scale, oy + (y - minY) * scale]))
}

function compare(learner: Pt[], template: Pt[], tol: number, points: number): { score: number; reason?: Reason } {
  const a = resample(learner, points)
  const b = resample(template, points)
  const forward = dtw(a, b)
  const backward = dtw([...a].reverse(), b)
  const limit = tol * BOX
  if (backward < forward * 0.7 && backward < limit) {
    return { score: Math.max(0, 1 - backward / limit), reason: 'direction' }
  }
  const score = Math.max(0, 1 - forward / limit)
  return forward <= limit ? { score } : { score, reason: 'shape' }
}

export function matchStrokes(
  learnerInk: Stroke[] | Pt[][],
  template: Pt[][],
  opts: MatchOptions = {},
): MatchResult {
  const { tolerance, points } = { ...DEFAULTS, ...opts }
  const learnerRaw =
    learnerInk.length > 0 && typeof (learnerInk[0] as Stroke)[0] === 'object' && !Array.isArray((learnerInk[0] as Stroke)[0])
      ? toGlyphBox(learnerInk as Stroke[])
      : (learnerInk as Pt[][])
  const learner = normaliseBox(learnerRaw)
  const tmpl = normaliseBox(template)
  const verdicts: StrokeVerdict[] = []
  const n = Math.max(learner.length, tmpl.length)
  for (let i = 0; i < n; i++) {
    if (i >= learner.length) {
      verdicts.push({ index: i, ok: false, reason: 'missing', score: 0 })
      continue
    }
    if (i >= tmpl.length) {
      verdicts.push({ index: i, ok: false, reason: 'extra', score: 0 })
      continue
    }
    const own = compare(learner[i], tmpl[i], tolerance, points)
    // Order: does this stroke fit some other template stroke clearly better?
    let best = own.score
    let bestJ = i
    tmpl.forEach((t, j) => {
      if (j === i) return
      const alt = compare(learner[i], t, tolerance, points)
      if (!alt.reason && alt.score > best * 1.25 + 0.05) {
        best = alt.score
        bestJ = j
      }
    })
    if (own.reason && bestJ !== i) {
      verdicts.push({ index: i, ok: false, reason: 'order', score: own.score })
    } else {
      verdicts.push({ index: i, ok: !own.reason, reason: own.reason, score: own.score })
    }
  }
  const countOk = learner.length === tmpl.length
  const okCount = verdicts.filter((v) => v.ok).length
  const score = verdicts.length ? okCount / verdicts.length : 0
  return { ok: countOk && okCount === verdicts.length, score, strokes: verdicts, countOk }
}
