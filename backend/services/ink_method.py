"""The METHOD of a piece of handwriting — not what it says, how it was
made (docs/plans/handwriting.md, §11).

The canvas records strokes as timed point lists. From those, without any
model, we can say how many strokes were used, which way they ran, whether
the pen was lifted between letters or carried through (joined writing),
and how fast the hand moved. Two uses:

1. **Told to the reader.** A hamza drawn as its own stroke, an alif drawn
   bottom-to-top, a word written in one continuous movement — these are
   facts about the writing the image alone can only guess at, and they
   change what a shape means.
2. **Kept with the sample.** The writer's method is as much their hand as
   their letterforms; it is what the stroke matcher's personal tolerance
   (Phase D) will be built from.

Coordinates are whatever the client sends (CSS pixels); every measure is
relative, so scale does not matter. Strokes with fewer than two points
are taps and are ignored.
"""
from __future__ import annotations

import math

MAX_POINTS_PER_STROKE = 64
MAX_STROKES = 400


def compact(strokes) -> list[list[list[int]]]:
    """Strokes as the sample stores them: integer [x, y, t] triples,
    resampled to at most MAX_POINTS_PER_STROKE per stroke, at most
    MAX_STROKES strokes. Anything malformed is dropped rather than raised —
    this is a kept detail, never a reason to refuse a Check."""
    out: list[list[list[int]]] = []
    for stroke in (strokes or [])[:MAX_STROKES]:
        pts: list[list[int]] = []
        for p in stroke or []:
            try:
                if isinstance(p, dict):
                    x, y, t = p.get("x"), p.get("y"), p.get("t", 0)
                else:
                    x, y = p[0], p[1]
                    t = p[2] if len(p) > 2 else 0
                pts.append([int(round(float(x))), int(round(float(y))),
                            int(round(float(t or 0)))])
            except (TypeError, ValueError, IndexError):
                continue
        if len(pts) < 2:
            continue
        if len(pts) > MAX_POINTS_PER_STROKE:
            step = (len(pts) - 1) / (MAX_POINTS_PER_STROKE - 1)
            pts = [pts[int(round(i * step))] for i in range(MAX_POINTS_PER_STROKE)]
        out.append(pts)
    return out


def _direction(p0, p1) -> str | None:
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    if abs(dx) < 1 and abs(dy) < 1:
        return None
    if abs(dy) >= abs(dx):
        return "down" if dy > 0 else "up"
    return "right" if dx > 0 else "left"


def summarize_method(strokes) -> dict:
    """Facts about how the ink was made. Empty dict for no usable ink."""
    st = compact(strokes)
    if not st:
        return {}
    directions: dict[str, int] = {"down": 0, "up": 0, "left": 0, "right": 0}
    lengths: list[float] = []
    heights: list[float] = []
    for s in st:
        d = _direction(s[0], s[-1])
        if d:
            directions[d] += 1
        length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(s, s[1:]))
        lengths.append(length)
        heights.append(max(p[1] for p in s) - min(p[1] for p in s))
    median_height = sorted(heights)[len(heights) // 2] or 1.0
    # A "long" stroke runs several letters' worth — a joined run. Lifts
    # are the gaps between strokes; joined writing has few, long strokes.
    joined = sum(1 for length in lengths if length > 3 * median_height)
    total_len = sum(lengths)
    t0 = min(s[0][2] for s in st)
    t1 = max(s[-1][2] for s in st)
    duration_ms = max(0, t1 - t0)
    dominant = max(directions, key=directions.get) if any(directions.values()) else None
    horizontal = directions["left"] + directions["right"]
    return {
        "strokes": len(st),
        "lifts": max(0, len(st) - 1),
        "joined_runs": joined,
        "dominant_direction": dominant,
        "reads_right_to_left": directions["left"] > directions["right"] and horizontal > 0,
        "duration_ms": duration_ms,
        "speed_px_per_s": round(total_len / (duration_ms / 1000), 1) if duration_ms > 0 else None,
    }


def method_line(summary: dict) -> str:
    """One plain sentence for the reader. Empty when there is nothing."""
    if not summary:
        return ""
    n = summary["strokes"]
    parts = [f"written in {n} stroke{'s' if n != 1 else ''}"]
    if summary.get("joined_runs"):
        parts.append("with letters carried through without lifting the pen")
    elif n > 1:
        parts.append("with the pen lifted between strokes")
    d = summary.get("dominant_direction")
    if d:
        parts.append(f"strokes mostly running {d}")
    if summary.get("duration_ms", 0) > 0:
        parts.append(f"over {summary['duration_ms'] / 1000:.1f} s")
    return ", ".join(parts) + "."
