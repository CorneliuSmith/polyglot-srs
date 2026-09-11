import { useEffect, useRef, useState } from 'react'
import { fromGlyphBox } from './glyphBox'

/**
 * A stored glyph, drawn stroke by stroke: the Learn animation of the
 * guided Letters mode and the Strokes panel's "does this look right?"
 * preview. Numbered start points, a faint finished form behind, and the
 * strokes in order at a hand's pace.
 */
export default function StrokePreview({
  strokes,
  size = 160,
  playing = true,
  onDone,
}: {
  strokes: number[][][]
  size?: number
  playing?: boolean
  onDone?: () => void
}) {
  const ref = useRef<HTMLCanvasElement>(null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const dpr = window.devicePixelRatio || 1
    canvas.width = size * dpr
    canvas.height = size * dpr
    const ctx = canvas.getContext?.('2d')
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    const paths = fromGlyphBox(strokes, size)
    const total = paths.reduce((n, s) => n + s.length, 0)
    let shown = playing ? 0 : total
    let raf = 0
    let last = 0
    const draw = () => {
      ctx.clearRect(0, 0, size, size)
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      // The finished form, faint, under the animation.
      ctx.strokeStyle = 'rgba(120,120,120,0.25)'
      ctx.lineWidth = 3
      for (const s of paths) {
        ctx.beginPath()
        ctx.moveTo(s[0].x, s[0].y)
        for (const p of s) ctx.lineTo(p.x, p.y)
        ctx.stroke()
      }
      // The strokes so far, solid, with a numbered start point each.
      let left = shown
      ctx.strokeStyle = '#111'
      ctx.lineWidth = 4
      paths.forEach((s, i) => {
        if (left <= 0) return
        const n = Math.min(left, s.length)
        ctx.beginPath()
        ctx.moveTo(s[0].x, s[0].y)
        for (let k = 1; k < n; k++) ctx.lineTo(s[k].x, s[k].y)
        ctx.stroke()
        ctx.fillStyle = 'var(--color-lang, #4f46e5)'
        ctx.beginPath()
        ctx.arc(s[0].x, s[0].y, 7, 0, Math.PI * 2)
        ctx.fill()
        ctx.fillStyle = '#fff'
        ctx.font = 'bold 9px sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(String(i + 1), s[0].x, s[0].y)
        left -= s.length
      })
    }
    const step = (ts: number) => {
      if (ts - last > 18) {
        shown = Math.min(total, shown + 2)
        last = ts
        draw()
      }
      if (shown < total) raf = requestAnimationFrame(step)
      else onDone?.()
    }
    draw()
    if (playing && total > 0 && typeof requestAnimationFrame === 'function') {
      raf = requestAnimationFrame(step)
    }
    return () => {
      if (raf) cancelAnimationFrame(raf)
    }
  }, [strokes, size, playing, tick, onDone])

  return (
    <canvas
      ref={ref}
      data-testid="stroke-preview"
      width={size}
      height={size}
      style={{ width: size, height: size }}
      className="rounded-xl border border-gray-200 bg-white cursor-pointer"
      onClick={() => setTick((n) => n + 1)}
      aria-label="Stroke order preview — tap to replay"
    />
  )
}
