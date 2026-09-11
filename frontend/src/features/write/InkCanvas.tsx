import { useEffect, useRef, useState } from 'react'
import type { PointerEvent as ReactPointerEvent } from 'react'
import { inkBox } from './ink'
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
 *
 * With `paper`, the surface is a strip of paper wider than the screen —
 * a sentence is long and a phone is not. The strip starts as wide as the
 * expected text needs, grows as ink nears its end, and slides along by
 * itself when a stroke lands near the visible edge, so the writer keeps
 * writing; two fingers (or a mouse wheel) slide it by hand, and a thin
 * overview strip under the canvas shows the whole line with the window
 * in it, draggable. Right-to-left scripts start at the right end and the
 * paper grows on the left. Strokes stay in paper coordinates throughout.
 */
export interface CanvasGuide {
  /** Text drawn faintly behind the ink — the letter an author traces. */
  text: string
  fontFamily?: string
  /** Fraction of the canvas height the glyph is set at. */
  scale?: number
}

/** Paper pixels per expected character, as a first width. */
const PX_PER_CHAR = 46
const EDGE = 0.18
const GROW = 0.6

/** Whether the strip should slide after a stroke ended at `edgeX` (the
 * stroke's leading edge in paper px), and by how much. Pure, for tests. */
export function advanceFor(
  edgeX: number,
  scrollLeft: number,
  viewport: number,
  rtl: boolean,
): number {
  const margin = viewport * EDGE
  if (!rtl && edgeX > scrollLeft + viewport - margin) return viewport * 0.5
  if (rtl && edgeX < scrollLeft + margin) return -viewport * 0.5
  return 0
}

/** How much wider the paper must get (and, for RTL, how far the ink must
 * shift right) when ink nears its end. Pure, for tests. */
export function growthFor(strokes: Stroke[], paperWidth: number, viewport: number, rtl: boolean): number {
  const box = inkBox(strokes)
  if (!box) return 0
  const margin = Math.max(80, viewport * EDGE)
  if (!rtl && box.maxX > paperWidth - margin) return Math.round(viewport * GROW)
  if (rtl && box.minX < margin) return Math.round(viewport * GROW)
  return 0
}

export default function InkCanvas({
  strokes,
  onChange,
  height = 240,
  disabled = false,
  rtl = false,
  className = '',
  guide,
  baseline = true,
  guideStrokes,
  guideDone,
  paper,
}: {
  strokes: Stroke[]
  onChange: (strokes: Stroke[]) => void
  height?: number
  disabled?: boolean
  rtl?: boolean
  className?: string
  guide?: CanvasGuide
  baseline?: boolean
  /** Template strokes drawn faintly under the ink — the Trace step. Each
   * index in `guideDone` is drawn solid (a matched stroke snaps). */
  guideStrokes?: Stroke[]
  guideDone?: number[]
  /** A scrolling strip of paper sized for this many characters. */
  paper?: { expectedLength?: number }
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<HTMLCanvasElement>(null)
  const drawing = useRef<Stroke | null>(null)
  const pointers = useRef(new Map<number, { x: number; y: number }>())
  const pan = useRef<{ startX: number; scrollLeft: number } | null>(null)
  const [paperWidth, setPaperWidth] = useState<number | null>(null)
  const [view, setView] = useState({ scrollLeft: 0, width: 0 })

  // The strip's first width: the viewport, or what the text needs. Set
  // when the canvas is empty (fresh, or cleared); ink in hand keeps its
  // paper.
  const empty = strokes.length === 0
  useEffect(() => {
    if (!paper) {
      setPaperWidth(null)
      return
    }
    if (!empty) return
    const wrap = wrapRef.current
    const viewport = wrap?.clientWidth || 600
    const want = Math.max(viewport, Math.round((paper.expectedLength ?? 0) * PX_PER_CHAR * 1.15))
    setPaperWidth(want)
    setView({ scrollLeft: rtl ? want - viewport : 0, width: viewport })
    if (wrap) {
      requestAnimationFrame?.(() => {
        wrap.scrollLeft = rtl ? wrap.scrollWidth : 0
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paper?.expectedLength, rtl, !!paper, empty])

  // Redraw everything on every change: a few hundred points is nothing,
  // and it keeps undo/clear trivial.
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const dpr = window.devicePixelRatio || 1
    const cssWidth = paperWidth ?? (canvas.clientWidth || 600)
    const cssHeight = height
    if (canvas.width !== Math.round(cssWidth * dpr) || canvas.height !== Math.round(cssHeight * dpr)) {
      canvas.width = Math.round(cssWidth * dpr)
      canvas.height = Math.round(cssHeight * dpr)
    }
    const ctx = canvas.getContext?.('2d')
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, cssWidth, cssHeight)
    if (guide?.text) {
      // The glyph to trace, faint and large, centred. Shaping (Arabic
      // positional forms via joiners) is the font's job, so the author
      // traces a real letterform, not their memory of one. A word is
      // shrunk to fit the width.
      ctx.save()
      ctx.fillStyle = 'rgba(120,120,120,0.22)'
      const family = guide.fontFamily ?? 'sans-serif'
      let size = Math.round(cssHeight * (guide.scale ?? 0.7))
      ctx.font = `${size}px ${family}`
      const w = ctx.measureText?.(guide.text).width ?? 0
      if (w > cssWidth * 0.9) {
        size = Math.max(16, Math.floor(size * (cssWidth * 0.9) / w))
        ctx.font = `${size}px ${family}`
      }
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(guide.text, cssWidth / 2, cssHeight / 2)
      ctx.restore()
    }
    if (guideStrokes && guideStrokes.length > 0) {
      ctx.save()
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      guideStrokes.forEach((gs, i) => {
        if (gs.length === 0) return
        const done = guideDone?.includes(i)
        ctx.strokeStyle = done ? 'rgba(22,163,74,0.45)' : 'rgba(120,120,120,0.25)'
        ctx.lineWidth = done ? 5 : 8
        ctx.beginPath()
        ctx.moveTo(gs[0].x, gs[0].y)
        for (const p of gs) ctx.lineTo(p.x, p.y)
        ctx.stroke()
        // A numbered start point per stroke.
        ctx.fillStyle = done ? 'rgba(22,163,74,0.9)' : 'rgba(120,120,120,0.6)'
        ctx.beginPath()
        ctx.arc(gs[0].x, gs[0].y, 8, 0, Math.PI * 2)
        ctx.fill()
        ctx.fillStyle = '#fff'
        ctx.font = 'bold 10px sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(String(i + 1), gs[0].x, gs[0].y)
      })
      ctx.restore()
    }
    if (baseline) {
      ctx.save()
      ctx.strokeStyle = 'rgba(120,120,120,0.35)'
      ctx.setLineDash([6, 8])
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(0, cssHeight * 0.66)
      ctx.lineTo(cssWidth, cssHeight * 0.66)
      ctx.stroke()
      ctx.restore()
    }
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
  }, [strokes, height, guide, baseline, guideStrokes, guideDone, paperWidth])

  // The overview strip: the whole paper in miniature, the window on it.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !paperWidth) return
    const dpr = window.devicePixelRatio || 1
    const w = map.clientWidth || 600
    const h = 28
    map.width = Math.round(w * dpr)
    map.height = Math.round(h * dpr)
    const ctx = map.getContext?.('2d')
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, w, h)
    const s = w / paperWidth
    ctx.strokeStyle = '#555'
    ctx.lineWidth = 1
    ctx.lineCap = 'round'
    for (const stroke of strokes) {
      if (stroke.length === 0) continue
      ctx.beginPath()
      ctx.moveTo(stroke[0].x * s, (stroke[0].y / height) * h)
      for (const p of stroke) ctx.lineTo(p.x * s, (p.y / height) * h)
      ctx.stroke()
    }
    if (view.width > 0) {
      ctx.fillStyle = 'rgba(79,70,229,0.12)'
      ctx.strokeStyle = 'rgba(79,70,229,0.6)'
      ctx.fillRect(view.scrollLeft * s, 0, view.width * s, h)
      ctx.strokeRect(view.scrollLeft * s + 0.5, 0.5, view.width * s - 1, h - 1)
    }
  }, [strokes, paperWidth, view, height])

  // A mouse wheel slides the paper; React's wheel listener is passive, so
  // the native one is needed to keep the page from scrolling instead.
  useEffect(() => {
    const wrap = wrapRef.current
    if (!wrap || !paper) return
    const onWheel = (e: WheelEvent) => {
      const d = Math.abs(e.deltaY) > Math.abs(e.deltaX) ? e.deltaY : e.deltaX
      if (d === 0) return
      e.preventDefault()
      wrap.scrollLeft += d
    }
    wrap.addEventListener('wheel', onWheel, { passive: false })
    return () => wrap.removeEventListener('wheel', onWheel)
  }, [paper])

  const point = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    return { x: e.clientX - rect.left, y: e.clientY - rect.top, t: e.timeStamp }
  }

  const onScroll = () => {
    const wrap = wrapRef.current
    if (!wrap) return
    setView({ scrollLeft: wrap.scrollLeft, width: wrap.clientWidth })
  }

  const onDown = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    if (disabled) return
    e.preventDefault()
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
    if (paper && pointers.current.size >= 2) {
      // A second finger: this is a slide, not a stroke. Drop the stroke
      // the first finger began.
      if (drawing.current) {
        onChange(strokes.slice(0, -1))
        drawing.current = null
      }
      const xs = [...pointers.current.values()].map((p) => p.x)
      pan.current = { startX: xs.reduce((a, b) => a + b, 0) / xs.length, scrollLeft: wrapRef.current?.scrollLeft ?? 0 }
      return
    }
    e.currentTarget.setPointerCapture?.(e.pointerId)
    drawing.current = [point(e)]
    onChange([...strokes, drawing.current])
  }

  const onMove = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    if (pointers.current.has(e.pointerId)) pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
    if (pan.current && wrapRef.current) {
      e.preventDefault()
      const xs = [...pointers.current.values()].map((p) => p.x)
      const mid = xs.reduce((a, b) => a + b, 0) / Math.max(1, xs.length)
      wrapRef.current.scrollLeft = pan.current.scrollLeft - (mid - pan.current.startX)
      return
    }
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
    pointers.current.delete(e.pointerId)
    if (pan.current) {
      if (pointers.current.size < 2) pan.current = null
      return
    }
    if (!drawing.current) return
    e.currentTarget.releasePointerCapture?.(e.pointerId)
    const stroke = drawing.current
    drawing.current = null
    if (!paper || !paperWidth) return
    const wrap = wrapRef.current
    const viewport = wrap?.clientWidth || 600
    // Grow the paper when the ink nears its end; a right-to-left hand
    // grows it on the left, which means shifting the ink right.
    const all = [...strokes.slice(0, -1), stroke]
    const grow = growthFor(all, paperWidth, viewport, rtl)
    if (grow > 0) {
      setPaperWidth(paperWidth + grow)
      if (rtl) {
        onChange(all.map((s) => s.map((p) => ({ ...p, x: p.x + grow }))))
        if (wrap) requestAnimationFrame?.(() => { wrap.scrollLeft += grow })
      }
    }
    // Slide along when the stroke landed near the visible edge.
    if (wrap && stroke.length > 0) {
      const xs = stroke.map((p) => p.x)
      const edge = rtl ? Math.min(...xs) : Math.max(...xs)
      const by = advanceFor(edge + (rtl && grow > 0 ? grow : 0), wrap.scrollLeft + (rtl && grow > 0 ? grow : 0), viewport, rtl)
      if (by !== 0) {
        requestAnimationFrame?.(() => wrap.scrollBy?.({ left: by, behavior: 'smooth' }))
      }
    }
  }

  // The overview strip: tap or drag to move the window.
  const onMapPointer = (e: ReactPointerEvent<HTMLCanvasElement>) => {
    if (!paperWidth || !wrapRef.current) return
    if (e.type === 'pointermove' && e.buttons === 0) return
    const rect = e.currentTarget.getBoundingClientRect()
    const frac = (e.clientX - rect.left) / Math.max(1, rect.width)
    const wrap = wrapRef.current
    wrap.scrollLeft = frac * paperWidth - wrap.clientWidth / 2
  }

  const canvas = (
    <canvas
      ref={canvasRef}
      data-testid="ink-canvas"
      dir={rtl ? 'rtl' : 'ltr'}
      className={`block ${paper ? '' : 'w-full rounded-2xl border-2 border-gray-200'} bg-white ${
        disabled ? 'opacity-60' : 'cursor-crosshair'
      } ${className}`}
      style={{ height, width: paperWidth ?? undefined, touchAction: 'none' }}
      onPointerDown={onDown}
      onPointerMove={onMove}
      onPointerUp={onUp}
      onPointerCancel={onUp}
      onPointerLeave={onUp}
      aria-label="Writing surface"
    />
  )
  if (!paper) return canvas
  return (
    <div className="space-y-1" data-testid="ink-paper">
      <div
        ref={wrapRef}
        onScroll={onScroll}
        className="overflow-x-auto overflow-y-hidden rounded-2xl border-2 border-gray-200 bg-white"
        style={{ scrollbarWidth: 'thin', touchAction: 'none' }}
      >
        {canvas}
      </div>
      <canvas
        ref={mapRef}
        data-testid="ink-map"
        className="block w-full rounded-lg border border-gray-200 bg-gray-50 cursor-ew-resize"
        style={{ height: 28, touchAction: 'none' }}
        onPointerDown={onMapPointer}
        onPointerMove={onMapPointer}
        aria-label="Overview of the line — drag to move"
      />
    </div>
  )
}
