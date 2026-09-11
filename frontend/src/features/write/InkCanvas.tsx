import { useEffect, useRef } from 'react'
import type { PointerEvent as ReactPointerEvent } from 'react'
import type { Stroke } from './ink'

/**
 * The writing surface. One pointer API for finger, mouse and pen;
 * `touch-action: none` so a phone draws instead of scrolling; strokes are
 * kept in CSS-pixel space so the neatness measures and the export never
 * care about the device's pixel ratio.
 *
 * A dashed baseline sits at two-thirds height as the line to write on —
 * the same line the baseline measure reads from, though nothing forces the
 * learner onto it.
 */
export default function InkCanvas({
  strokes,
  onChange,
  height = 240,
  disabled = false,
  rtl = false,
  className = '',
}: {
  strokes: Stroke[]
  onChange: (strokes: Stroke[]) => void
  height?: number
  disabled?: boolean
  rtl?: boolean
  className?: string
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const drawing = useRef<Stroke | null>(null)

  // Redraw everything on every change: a few hundred points is nothing,
  // and it keeps undo/clear trivial.
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const dpr = window.devicePixelRatio || 1
    const cssWidth = canvas.clientWidth || 600
    const cssHeight = height
    if (canvas.width !== Math.round(cssWidth * dpr) || canvas.height !== Math.round(cssHeight * dpr)) {
      canvas.width = Math.round(cssWidth * dpr)
      canvas.height = Math.round(cssHeight * dpr)
    }
    const ctx = canvas.getContext?.('2d')
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, cssWidth, cssHeight)
    ctx.save()
    ctx.strokeStyle = 'rgba(120,120,120,0.35)'
    ctx.setLineDash([6, 8])
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, cssHeight * 0.66)
    ctx.lineTo(cssWidth, cssHeight * 0.66)
    ctx.stroke()
    ctx.restore()
    ctx.strokeStyle = '#111111'
    ctx.lineWidth = 3
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
  }, [strokes, height])

  const point = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    return { x: e.clientX - rect.left, y: e.clientY - rect.top, t: e.timeStamp }
  }

  const onDown = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    if (disabled) return
    e.preventDefault()
    e.currentTarget.setPointerCapture?.(e.pointerId)
    drawing.current = [point(e)]
    onChange([...strokes, drawing.current])
  }

  const onMove = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    if (!drawing.current) return
    e.preventDefault()
    // Coalesced events carry the points the browser batched between
    // frames — a fast pen stroke is a curve, not a polygon.
    const native = e.nativeEvent as PointerEvent & {
      getCoalescedEvents?: () => PointerEvent[]
    }
    const rect = e.currentTarget.getBoundingClientRect()
    const extra = native.getCoalescedEvents?.() ?? []
    const pts = extra.length
      ? extra.map((ev) => ({ x: ev.clientX - rect.left, y: ev.clientY - rect.top, t: ev.timeStamp }))
      : [point(e)]
    drawing.current.push(...pts)
    onChange([...strokes.slice(0, -1), drawing.current])
  }

  const onUp = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    if (!drawing.current) return
    e.currentTarget.releasePointerCapture?.(e.pointerId)
    drawing.current = null
  }

  return (
    <canvas
      ref={canvasRef}
      data-testid="ink-canvas"
      dir={rtl ? 'rtl' : 'ltr'}
      className={`block w-full rounded-2xl border-2 border-gray-200 bg-white ${
        disabled ? 'opacity-60' : 'cursor-crosshair'
      } ${className}`}
      style={{ height, touchAction: 'none' }}
      onPointerDown={onDown}
      onPointerMove={onMove}
      onPointerUp={onUp}
      onPointerCancel={onUp}
      onPointerLeave={onUp}
      aria-label="Writing surface"
    />
  )
}
