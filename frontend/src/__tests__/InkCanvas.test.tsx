import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import InkCanvas, { advanceFor, growthFor } from '../features/write/InkCanvas'
import type { Stroke } from '../features/write/ink'

HTMLCanvasElement.prototype.getContext = (() => null) as unknown as typeof HTMLCanvasElement.prototype.getContext
if (typeof window !== 'undefined' && !('PointerEvent' in window)) {
  class PointerEventShim extends MouseEvent {
    pointerId: number
    constructor(type: string, init: PointerEventInit = {}) {
      super(type, init)
      this.pointerId = init.pointerId ?? 0
    }
  }
  ;(window as unknown as { PointerEvent: typeof PointerEventShim }).PointerEvent = PointerEventShim
}

const s = (...pts: [number, number][]): Stroke => pts.map(([x, y], i) => ({ x, y, t: i }))

describe('the scrolling paper', () => {
  it('slides half a screen when a stroke lands near the visible edge, in the writing direction', () => {
    // Viewport 400 wide, showing paper 0–400: a stroke ending at 350 is in the edge zone.
    expect(advanceFor(350, 0, 400, false)).toBe(200)
    expect(advanceFor(200, 0, 400, false)).toBe(0)
    // Right to left: the window shows 600–1000; ink at 640 is near the left edge.
    expect(advanceFor(640, 600, 400, true)).toBe(-200)
    expect(advanceFor(900, 600, 400, true)).toBe(0)
  })

  it('grows the paper when ink nears its end', () => {
    expect(growthFor([s([100, 50], [950, 60])], 1000, 400, false)).toBe(240)
    expect(growthFor([s([100, 50], [500, 60])], 1000, 400, false)).toBe(0)
    expect(growthFor([s([900, 50], [40, 60])], 1000, 400, true)).toBe(240)
    expect(growthFor([], 1000, 400, false)).toBe(0)
  })

  it('renders the strip and the overview only as paper', () => {
    const { rerender } = render(<InkCanvas strokes={[]} onChange={() => {}} />)
    expect(screen.queryByTestId('ink-map')).not.toBeInTheDocument()
    rerender(<InkCanvas strokes={[]} onChange={() => {}} paper={{ expectedLength: 60 }} />)
    expect(screen.getByTestId('ink-paper')).toBeInTheDocument()
    expect(screen.getByTestId('ink-map')).toBeInTheDocument()
    // Sized for the text: 60 characters need more than a phone's width.
    expect(parseInt(screen.getByTestId('ink-canvas').style.width, 10)).toBeGreaterThan(600)
  })

  it('a second finger slides instead of drawing, and drops the stroke the first began', () => {
    const onChange = vi.fn()
    render(<InkCanvas strokes={[]} onChange={onChange} paper={{}} />)
    const canvas = screen.getByTestId('ink-canvas')
    fireEvent.pointerDown(canvas, { pointerId: 1, clientX: 10, clientY: 10 })
    expect(onChange).toHaveBeenLastCalledWith([expect.any(Array)])
    fireEvent.pointerDown(canvas, { pointerId: 2, clientX: 60, clientY: 10 })
    expect(onChange).toHaveBeenLastCalledWith([])
    fireEvent.pointerMove(canvas, { pointerId: 2, clientX: 80, clientY: 10 })
    expect(onChange).toHaveBeenCalledTimes(2)
  })
})
