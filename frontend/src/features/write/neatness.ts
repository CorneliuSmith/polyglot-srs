import { strokeBox } from './ink'
import type { Stroke } from './ink'

/**
 * Neatness — what the ink itself says, with no template and no model
 * (docs/plans/handwriting.md, §4.3).
 *
 * Four things a writing teacher marks first, each measured from the
 * strokes on the device: how straight the line sits, how even the letters
 * are, how consistent the slant is, how regular the gaps are. Exact and
 * free, so they show for every course from day one; the model's verdict
 * on legibility is a separate, complementary judgement.
 *
 * Every measure is a ratio of the learner's own writing size, so the same
 * hand scores the same on a phone and a monitor.
 */

export type Verdict = 'good' | 'ok' | 'poor' | 'na'

export interface NeatnessReport {
  baseline: Verdict
  size: Verdict
  slant: Verdict
  spacing: Verdict
  /** Ink groups the measures were taken over — roughly letters or joined
   * runs. Exposed so a caller can say "not enough written yet". */
  clusters: number
}

interface Cluster {
  minX: number
  maxX: number
  minY: number
  maxY: number
}

const MIN_CLUSTERS = 3

/** Group strokes that overlap or nearly touch horizontally: a letter's
 * strokes, or a whole joined run, become one cluster. The gap that still
 * counts as "the same letter" scales with the writing's height. */
export function clusterStrokes(strokes: Stroke[]): Cluster[] {
  const boxes = strokes
    .filter((s) => s.length >= 2)
    .map(strokeBox)
    .sort((a, b) => a.minX - b.minX)
  if (boxes.length === 0) return []
  const heights = boxes.map((b) => b.maxY - b.minY).sort((a, b) => a - b)
  const medianHeight = heights[Math.floor(heights.length / 2)] || 1
  const gap = medianHeight * 0.15
  const clusters: Cluster[] = []
  for (const b of boxes) {
    const last = clusters[clusters.length - 1]
    if (last && b.minX <= last.maxX + gap) {
      last.maxX = Math.max(last.maxX, b.maxX)
      last.minY = Math.min(last.minY, b.minY)
      last.maxY = Math.max(last.maxY, b.maxY)
    } else {
      clusters.push({ ...b })
    }
  }
  return clusters
}

function mean(xs: number[]): number {
  return xs.reduce((a, b) => a + b, 0) / xs.length
}

function stddev(xs: number[]): number {
  const m = mean(xs)
  return Math.sqrt(mean(xs.map((x) => (x - m) ** 2)))
}

/** Coefficient of variation, guarded for a zero mean. */
function cv(xs: number[]): number {
  const m = mean(xs)
  return m === 0 ? 0 : stddev(xs) / Math.abs(m)
}

function grade(value: number, good: number, ok: number): Verdict {
  if (value <= good) return 'good'
  if (value <= ok) return 'ok'
  return 'poor'
}

/** Least-squares slope of y over x, in radians. */
function slope(xs: number[], ys: number[]): number {
  const mx = mean(xs)
  const my = mean(ys)
  let num = 0
  let den = 0
  for (let i = 0; i < xs.length; i++) {
    num += (xs[i] - mx) * (ys[i] - my)
    den += (xs[i] - mx) ** 2
  }
  return den === 0 ? 0 : Math.atan(num / den)
}

/** The angle of a stroke's long axis from the vertical, in degrees, by
 * principal component. Only strokes taller than they are wide have a
 * slant worth reading. */
function strokeSlantDeg(stroke: Stroke): number | null {
  const b = strokeBox(stroke)
  const h = b.maxY - b.minY
  const w = b.maxX - b.minX
  if (h < 8 || h < w * 1.2) return null
  const mx = mean(stroke.map((p) => p.x))
  const my = mean(stroke.map((p) => p.y))
  let sxx = 0
  let syy = 0
  let sxy = 0
  for (const p of stroke) {
    sxx += (p.x - mx) ** 2
    syy += (p.y - my) ** 2
    sxy += (p.x - mx) * (p.y - my)
  }
  // Angle of the principal axis, measured from the y axis so an upright
  // stroke is 0 and a forward lean is positive.
  const theta = 0.5 * Math.atan2(2 * sxy, sxx - syy)
  let deg = (theta * 180) / Math.PI - 90
  while (deg <= -90) deg += 180
  while (deg > 90) deg -= 180
  return deg
}

export function neatness(strokes: Stroke[]): NeatnessReport {
  const clusters = clusterStrokes(strokes)
  const na: NeatnessReport = {
    baseline: 'na', size: 'na', slant: 'na', spacing: 'na',
    clusters: clusters.length,
  }
  if (clusters.length < MIN_CLUSTERS) return na

  const heights = clusters.map((c) => c.maxY - c.minY)
  const medianHeight =
    [...heights].sort((a, b) => a - b)[Math.floor(heights.length / 2)] || 1

  // Baseline: the bottoms of the clusters should sit on one level line.
  // Drift is the fitted slope; wobble is how far the bottoms stray from
  // that line relative to the writing's height. The worse of the two.
  const centres = clusters.map((c) => (c.minX + c.maxX) / 2)
  const bottoms = clusters.map((c) => c.maxY)
  const drift = Math.abs(slope(centres, bottoms))
  const fitted = slope(centres, bottoms)
  const mx = mean(centres)
  const my = mean(bottoms)
  const residuals = bottoms.map((y, i) => y - (my + Math.tan(fitted) * (centres[i] - mx)))
  const wobble = stddev(residuals) / medianHeight
  const baselineDrift = grade(drift, 0.035, 0.09)
  const baselineWobble = grade(wobble, 0.12, 0.25)
  const order: Verdict[] = ['good', 'ok', 'poor']
  const baseline = order[Math.max(order.indexOf(baselineDrift), order.indexOf(baselineWobble))]

  // Size: letters of one hand vary (ascenders, descenders), so the bar is
  // generous — a spread of a third of the height is still "even"; past
  // half, the letters are visibly different sizes.
  const size = grade(cv(heights), 0.33, 0.55)

  // Slant: the spread of the tall strokes' lean. Needs a few to read.
  const slants = strokes
    .map(strokeSlantDeg)
    .filter((d): d is number => d !== null)
  const slant = slants.length >= 3 ? grade(stddev(slants), 8, 15) : 'na'

  // Spacing: the gaps between clusters should be alike. Needs a few gaps.
  const gaps: number[] = []
  for (let i = 1; i < clusters.length; i++) {
    gaps.push(Math.max(0, clusters[i].minX - clusters[i - 1].maxX))
  }
  const spacing = gaps.length >= 3 && mean(gaps) > 0 ? grade(cv(gaps), 0.45, 0.8) : 'na'

  return { baseline, size, slant, spacing, clusters: clusters.length }
}
