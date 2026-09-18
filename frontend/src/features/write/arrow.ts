import type { Stroke } from './ink'

/**
 * An arrowhead at the end of a stroke, pointing the way the pen went.
 * The numbered dot says where a stroke starts; without this, a static
 * frame cannot show which way it runs — an alif written upward from a
 * join looks the same as one written down (owner: "maybe use arrows").
 * Too short a stroke (a dot, a tick) gets none.
 */
export function drawArrowhead(ctx: CanvasRenderingContext2D, s: Stroke, size: number, color: string): void {
  if (s.length < 2) return
  const end = s[s.length - 1]
  // Direction from a point a little way back, so a wobbly last segment
  // does not swing the head around.
  let k = s.length - 2
  while (k > 0 && Math.hypot(end.x - s[k].x, end.y - s[k].y) < size) k--
  const from = s[k]
  const len = Math.hypot(end.x - from.x, end.y - from.y)
  if (len < size * 1.5) return
  const ux = (end.x - from.x) / len
  const uy = (end.y - from.y) / len
  ctx.save()
  ctx.fillStyle = color
  ctx.beginPath()
  ctx.moveTo(end.x + ux * size * 0.6, end.y + uy * size * 0.6)
  ctx.lineTo(end.x - ux * size * 0.6 - uy * size * 0.55, end.y - uy * size * 0.6 + ux * size * 0.55)
  ctx.lineTo(end.x - ux * size * 0.6 + uy * size * 0.55, end.y - uy * size * 0.6 - ux * size * 0.55)
  ctx.closePath()
  ctx.fill()
  ctx.restore()
}
