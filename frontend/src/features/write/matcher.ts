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

// ---------------------------------------------------------------------
// Words and sentences: the learner's ink against a composed template,
// matched progressively (docs/plans/handwriting.md, §4.2).
//
// The whole ink and the whole template become one point sequence each,
// in writing order, and are aligned by dynamic time warping — so a word
// written in one continuous cursive stroke is segmented by where it best
// fits each letter in turn, and a letter drawn in two strokes instead of
// one still lands on its letter. The verdict is per letter: the mean
// aligned distance of the letter's template points, against a tolerance.
// Open-ended alignment (Trace) lets a half-written word match the
// template's prefix, so letters snap solid one at a time.
// ---------------------------------------------------------------------
import type { Composed } from './composer'

export type LetterReason = 'missing' | 'shape'

export interface LetterVerdict {
  index: number
  char: string
  ok: boolean
  /** Whether the ink reached this letter at all (open-ended matching). */
  covered: boolean
  reason?: LetterReason
  score: number
}

export interface ComposedMatch {
  ok: boolean
  score: number
  letters: LetterVerdict[]
}

export interface ComposedOptions {
  tolerance?: number
  /** The canvas frame the template was drawn in (Trace): ink is mapped
   * back through it exactly. Without one (Write), the ink's box is
   * fitted to the template's. */
  frame?: { scale: number; ox: number; oy: number }
  openEnd?: boolean
  /** Box units between resampled points. */
  step?: number
}

function bbox(strokes: Pt[][]) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  for (const s of strokes) for (const [x, y] of s) {
    if (x < minX) minX = x
    if (y < minY) minY = y
    if (x > maxX) maxX = x
    if (y > maxY) maxY = y
  }
  return isFinite(minX) ? { minX, minY, maxX, maxY } : null
}

/** Resample by arc length at a fixed spacing, carrying a tag per point
 * (the owning letter) from the source point each sample falls after. */
function resampleTagged(stroke: Pt[], tags: number[], step: number): { pts: Pt[]; tags: number[] } {
  if (stroke.length === 0) return { pts: [], tags: [] }
  const total = stroke.slice(1).reduce((s, p, i) => s + dist(stroke[i], p), 0)
  const n = Math.max(2, Math.min(96, Math.round(total / step) + 1))
  if (stroke.length === 1 || total === 0) {
    return { pts: [[...stroke[0]], [...stroke[0]]], tags: [tags[0], tags[0]] }
  }
  const pts: Pt[] = [[...stroke[0]]]
  const out: number[] = [tags[0]]
  const seg = total / (n - 1)
  let acc = 0
  let i = 1
  let prev = stroke[0]
  while (pts.length < n - 1 && i < stroke.length) {
    const d = dist(prev, stroke[i])
    if (acc + d >= seg) {
      const t = (seg - acc) / d
      const p = [prev[0] + (stroke[i][0] - prev[0]) * t, prev[1] + (stroke[i][1] - prev[1]) * t]
      pts.push(p)
      out.push(tags[i - 1])
      prev = p
      acc = 0
    } else {
      acc += d
      prev = stroke[i]
      i++
    }
  }
  while (pts.length < n) {
    pts.push([...stroke[stroke.length - 1]])
    out.push(tags[tags.length - 1])
  }
  return { pts, tags: out }
}

export function matchComposed(
  learnerInk: Stroke[],
  composed: Composed,
  opts: ComposedOptions = {},
): ComposedMatch {
  const tolerance = opts.tolerance ?? 0.12
  const openEnd = opts.openEnd ?? false
  const step = opts.step ?? 25
  const limit = tolerance * BOX

  const letters: LetterVerdict[] = composed.letters.map((l, i) => ({
    index: i, char: l.char, ok: false, covered: false, score: 0,
    reason: l.glyph ? undefined : 'missing',
  }))
  const empty = { ok: false, score: 0, letters }
  const inkRaw = learnerInk.filter((s) => s.length >= 1).map((s) => s.map((p) => [p.x, p.y] as Pt))
  if (inkRaw.length === 0 || composed.strokes.length === 0) return empty

  // Into the template's frame.
  let ink: Pt[][]
  if (opts.frame) {
    const { scale, ox, oy } = opts.frame
    ink = inkRaw.map((s) => s.map(([x, y]) => [(x - ox) / scale, (y - oy) / scale]))
  } else {
    const tb = bbox(composed.strokes)!
    const ib = bbox(inkRaw)!
    const tw = Math.max(1, tb.maxX - tb.minX)
    const th = Math.max(1, tb.maxY - tb.minY)
    const iw = Math.max(1, ib.maxX - ib.minX)
    const ih = Math.max(1, ib.maxY - ib.minY)
    // Width and height fitted separately: a hand that writes wide or
    // tall is not wrong. A near-degenerate axis falls back to the other.
    const sy = th / ih
    const sx = iw > ih * 0.15 ? tw / iw : sy
    ink = inkRaw.map((s) => s.map(([x, y]) => [tb.minX + (x - ib.minX) * sx, tb.minY + (y - ib.minY) * sy]))
  }

  // One sequence each.
  const A: Pt[] = []
  for (const s of ink) A.push(...resampleTagged(s, s.map(() => 0), step).pts)
  const B: Pt[] = []
  const owner: number[] = []
  composed.strokes.forEach((s, si) => {
    const r = resampleTagged(s, composed.owners[si], step)
    B.push(...r.pts)
    owner.push(...r.tags)
  })
  const n = A.length
  const m = B.length
  if (n === 0 || m === 0) return empty
  if (n * m > 4_000_000) {
    return matchComposed(learnerInk, composed, { ...opts, step: step * 2 })
  }

  // DTW with a back-pointer per cell: 0 = diagonal, 1 = from above (i-1), 2 = from left (j-1).
  const W = m + 1
  const cost = new Float32Array((n + 1) * W).fill(Infinity)
  const from = new Uint8Array((n + 1) * W)
  cost[0] = 0
  for (let i = 1; i <= n; i++) {
    const a = A[i - 1]
    for (let j = 1; j <= m; j++) {
      const b = B[j - 1]
      const d = Math.hypot(a[0] - b[0], a[1] - b[1])
      const diag = cost[(i - 1) * W + (j - 1)]
      const up = cost[(i - 1) * W + j]
      const left = cost[i * W + (j - 1)]
      let best = diag
      let f = 0
      if (up < best) { best = up; f = 1 }
      if (left < best) { best = left; f = 2 }
      cost[i * W + j] = d + best
      from[i * W + j] = f
    }
  }
  // Where the ink ends on the template.
  let endJ = m
  if (openEnd) {
    let bestNorm = Infinity
    for (let j = Math.max(1, Math.floor(n * 0.5)); j <= m; j++) {
      const c = cost[n * W + j] / Math.max(n, j)
      if (c < bestNorm) { bestNorm = c; endJ = j }
    }
  }
  // Backtrack: per template point, the aligned ink distances.
  const sum = new Float64Array(m)
  const cnt = new Uint16Array(m)
  const inkIdx: Set<number>[] = Array.from({ length: m }, () => new Set())
  let i = n
  let j = endJ
  while (i > 0 && j > 0) {
    const a = A[i - 1]
    const b = B[j - 1]
    sum[j - 1] += Math.hypot(a[0] - b[0], a[1] - b[1])
    cnt[j - 1] += 1
    inkIdx[j - 1].add(i - 1)
    const f = from[i * W + j]
    if (f === 0) { i--; j-- } else if (f === 1) { i-- } else { j-- }
  }

  // Per letter.
  const perLetter = composed.letters.map(() => ({ sum: 0, cnt: 0, total: 0, reached: 0, ink: new Set<number>() }))
  for (let k = 0; k < m; k++) {
    const l = perLetter[owner[k]]
    if (!l) continue
    l.total += 1
    if (k < endJ) {
      l.reached += 1
      if (cnt[k] > 0) {
        l.sum += sum[k] / cnt[k]
        l.cnt += 1
        for (const x of inkIdx[k]) l.ink.add(x)
      }
    }
  }
  // How many letters each ink point serves: a letter whose ink is all
  // shared with its neighbours was skipped — the pen only passed by.
  const inkOwners = new Map<number, number>()
  for (const l of perLetter) for (const x of l.ink) inkOwners.set(x, (inkOwners.get(x) ?? 0) + 1)
  perLetter.forEach((l, idx) => {
    const v = letters[idx]
    if (v.reason === 'missing') return
    v.covered = l.total > 0 && l.reached === l.total
    if (!v.covered || l.cnt === 0) return
    const mean = l.sum / l.cnt
    v.score = Math.max(0, 1 - mean / limit)
    let exclusive = 0
    for (const x of l.ink) if (inkOwners.get(x) === 1) exclusive++
    // Missing: no ink of its own, or nothing anywhere near it (the pen
    // passed by and the alignment stretched a neighbour over the gap).
    if ((exclusive < Math.min(3, l.total) && mean > limit) || mean > 3 * limit) {
      v.ok = false
      v.reason = 'missing'
      v.score = 0
      return
    }
    v.ok = mean <= limit
    v.reason = v.ok ? undefined : 'shape'
  })
  const judged = letters.filter((v) => v.reason !== 'missing' || v.covered)
  const okCount = letters.filter((v) => v.ok).length
  const score = judged.length ? okCount / judged.length : 0
  return { ok: letters.every((v) => v.ok), score, letters }
}
