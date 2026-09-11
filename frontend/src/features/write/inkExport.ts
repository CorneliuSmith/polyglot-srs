import { inkBox } from './ink'
import type { Stroke } from './ink'

/** Render the strokes to a clean PNG for the reader: white ground, black
 * ink, tight crop with a margin, upscaled so a phone canvas still arrives
 * with letters the model can resolve. Separate from the on-screen canvas
 * so the picture never depends on the theme or the device's pixel ratio.
 * Resolves null where the platform has no canvas (a test runner). */
export async function renderInkToPng(
  strokes: Stroke[],
  opts: { maxWidth?: number; lineWidth?: number } = {},
): Promise<Blob | null> {
  const box = inkBox(strokes)
  if (!box || typeof document === 'undefined') return null
  const margin = 24
  const width = Math.max(1, box.maxX - box.minX) + margin * 2
  const height = Math.max(1, box.maxY - box.minY) + margin * 2
  const maxWidth = opts.maxWidth ?? 1400
  const scale = Math.min(2, maxWidth / width)
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(width * scale)
  canvas.height = Math.round(height * scale)
  const ctx = canvas.getContext?.('2d')
  if (!ctx) return null
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.scale(scale, scale)
  ctx.translate(margin - box.minX, margin - box.minY)
  ctx.strokeStyle = '#111111'
  ctx.lineWidth = opts.lineWidth ?? 3
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  for (const stroke of strokes) {
    if (stroke.length === 0) continue
    ctx.beginPath()
    ctx.moveTo(stroke[0].x, stroke[0].y)
    if (stroke.length === 1) ctx.lineTo(stroke[0].x + 0.1, stroke[0].y)
    for (let i = 1; i < stroke.length; i++) ctx.lineTo(stroke[i].x, stroke[i].y)
    ctx.stroke()
  }
  if (typeof canvas.toBlob !== 'function') return null
  return new Promise((resolve) => canvas.toBlob((b) => resolve(b), 'image/png'))
}
