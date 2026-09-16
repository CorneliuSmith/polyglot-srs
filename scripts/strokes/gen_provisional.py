"""Generate the PROVISIONAL stroke library — schematic stroke order for
Arabic (naskh) and Russian cursive, drawn from geometric primitives in
the 1000×1000 glyph box (docs/plans/handwriting.md, §13).

These are not a speaker's hand. They are the textbook order and
direction of each letter's strokes, in a plain schematic shape, so that
the guided Letters mode and the learning path teach *something true*
about order and direction before a speaker has traced the script. Every
form is marked source='provisional', reviewed=true, and the Workshop's
Strokes panel shows them as such; a speaker's traced form replaces one
by saving over it (the upsert resets it to their draft).

Outputs (all committed):
  data/strokes/{arabic,cyrillic}.json            — the seeder's format
  frontend/src/features/write/strokes/*.json     — the bundled fallback
  supabase/migrations/20261023000000_provisional_strokes.sql

Run: python scripts/strokes/gen_provisional.py
"""
# ruff: noqa: N802, E741
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOX = 1000
Pt = list[int]

# ----------------------------------------------------------------------
# Primitives. All in box units, y down.
# ----------------------------------------------------------------------

def L(a, b, n=6):
    return [[a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n] for i in range(n + 1)]


def B(p0, p1, p2, p3, n=14):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        x = u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]
        out.append([x, y])
    return out


def A(cx, cy, rx, ry, a0, a1, n=None):
    """Elliptical arc from angle a0 to a1 (degrees, screen coords: 0 = right,
    90 = down). a1 < a0 sweeps counter-clockwise on screen."""
    if n is None:
        n = max(6, int(abs(a1 - a0) / 15))
    out = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        out.append([cx + rx * math.cos(a), cy + ry * math.sin(a)])
    return out


def arc_pt(cx, cy, rx, ry, a):
    a = math.radians(a)
    return [cx + rx * math.cos(a), cy + ry * math.sin(a)]


def path(*segs):
    """One stroke from segments laid end to end; a gap between segments is
    bridged, so authoring mistakes show rather than vanish."""
    out: list = []
    for s in segs:
        if out and s and (abs(out[-1][0] - s[0][0]) < 2 and abs(out[-1][1] - s[0][1]) < 2):
            out.extend(s[1:])
        else:
            out.extend(s)
    return out


def dot(x, y):
    return L((x - 18, y), (x + 18, y), 2)


def dots(n, x, y, gap=60):
    if n == 1:
        return [dot(x, y)]
    if n == 2:
        return [dot(x - gap / 2, y), dot(x + gap / 2, y)]
    return [dot(x, y - 55), dot(x - gap / 2, y + 15), dot(x + gap / 2, y + 15)]


def shear(strokes, k=0.16, pivot=700):
    """Slant a glyph (cursive): x shifts right the higher the point."""
    return [[[x + (pivot - y) * k, y] for x, y in s] for s in strokes]


def finish(strokes):
    """Round, clamp, drop degenerate strokes."""
    out = []
    for s in strokes:
        pts = [[int(round(min(BOX, max(0, x)))), int(round(min(BOX, max(0, y))))] for x, y in s]
        dedup = [pts[0]]
        for p in pts[1:]:
            if p != dedup[-1]:
                dedup.append(p)
        if len(dedup) >= 2:
            out.append(dedup)
    return out


GLYPHS: list[dict] = []


def add(script, glyph, form, style, strokes, hints, joins=None, slant=False):
    if slant:
        strokes = shear(strokes)
    strokes = finish(strokes)
    assert strokes, (glyph, form)
    hints = list(hints) + [""] * (len(strokes) - len(hints))
    GLYPHS.append({
        "script": script, "glyph": glyph, "form": form, "style": style,
        "strokes": strokes, "joins": joins or {}, "hints": hints[:len(strokes)],
        "source": "provisional", "reviewed": True,
    })


# ======================================================================
# ARABIC — naskh. Baseline y = 620. Right to left: a letter starts at the
# right. The joining stroke is part of the form: entry at the right edge
# (950, 620), exit at the left edge (60, 620).
# ======================================================================
BASE = 620
ENTRY = [950, BASE]
EXIT = [60, BASE]
DOT_ABOVE = 360
DOT_BELOW = 790

def entry_to(x):
    return L(ENTRY, [x, BASE])

def exit_from(x):
    return L([x, BASE], EXIT)

def tooth(x, h=95, w=55):
    """A tooth rising and falling on the baseline, centred on x, from the right."""
    return path(L([x + w, BASE], [x, BASE - h], 3), L([x, BASE - h], [x - w, BASE], 3))

def bowl_shallow(x0, depth=80, left=170):
    """ب's boat from x0 on the baseline leftwards and up."""
    return path(B([x0, BASE - 90], [x0 + 20, BASE + depth], [x0 - 150, BASE + depth + 10], [x0 - 300, BASE + depth]),
                B([x0 - 300, BASE + depth], [x0 - 460, BASE + depth], [left, BASE + 20], [left + 20, BASE - 110]))

def bowl_deep(x0, left=190):
    """ن's bowl: a near half-circle under the line."""
    return path(B([x0, BASE - 160], [x0 + 60, BASE + 140], [left - 40, BASE + 150], [left + 30, BASE - 100]),
                L([left + 30, BASE - 100], [left + 50, BASE - 170], 2))

def hook_tail(x0):
    """ي's tail: left under the line and back to the right."""
    return path(B([x0, BASE - 90], [x0 + 20, BASE + 90], [x0 - 260, BASE + 110], [x0 - 380, BASE + 70]),
                B([x0 - 380, BASE + 70], [x0 - 560, BASE + 30], [x0 - 560, BASE + 240], [x0 - 300, BASE + 230]))

def loop_head(cx, cy, rx=85, ry=70):
    """ف's small loop, drawn from the bottom, round and back."""
    return A(cx, cy, rx, ry, 90, 450)

def jeem_head(x_right=780):
    """The head of ج: from the right, a small arch to the left, then down."""
    return B([x_right, BASE - 140], [x_right - 180, BASE - 260], [x_right - 380, BASE - 200], [x_right - 340, BASE - 100])

def jeem_bowl(x0, y0):
    return path(B([x0, y0], [x0 + 280, y0 + 60], [x0 + 260, BASE + 260], [x0 - 40, BASE + 260]),
                B([x0 - 40, BASE + 260], [x0 - 260, BASE + 260], [x0 - 300, BASE + 60], [x0 - 150, BASE + 10]))

def ain_head():
    return path(B([760, BASE - 220], [600, BASE - 300], [460, BASE - 240], [500, BASE - 120]),
                L([500, BASE - 120], [580, BASE - 100], 3))

def ain_head_medial(x_right):
    return path(L([x_right, BASE], [x_right - 60, BASE - 140], 3), L([x_right - 60, BASE - 140], [x_right - 240, BASE - 140], 3),
                L([x_right - 240, BASE - 140], [x_right - 260, BASE], 3))

def sad_eye(x_right=900):
    """ص's eye on the line, from the right, over the top and back."""
    return path(B([x_right - 340, BASE - 10], [x_right - 320, BASE - 150], [x_right + 10, BASE - 150], [x_right, BASE - 20]),
                B([x_right, BASE - 20], [x_right - 20, BASE + 20], [x_right - 320, BASE + 20], [x_right - 340, BASE - 10]))

def seen_teeth(x_right=880):
    pts = []
    x = x_right
    for _ in range(3):
        pts.append([x, BASE])
        pts.append([x - 40, BASE - 95])
        x -= 80
    pts.append([x, BASE])
    out = []
    for a, b in zip(pts, pts[1:]):
        out.extend(L(a, b, 3)[:-1])
    out.append(pts[-1])
    return out

def alif(x=520, top=150):
    return L([x, top], [x, BASE + 30])

S = "arabic"
N = "naskh"


def arabic():
    # ---- ا
    add(S, "ا", "isolated", N, [alif()], ["one stroke, top to bottom"])
    add(S, "ا", "final", N, [entry_to(560), alif(560)], ["along the line", "then the alif, top down to meet it"])

    # ---- the ب family: bowl letters with a tooth in the middle of a word
    def bowl_letter(g, n_dots, above):
        y = DOT_ABOVE if above else DOT_BELOW
        yi = DOT_ABOVE - 30 if above else DOT_BELOW - 40
        add(S, g, "isolated", N, [path(L([830, BASE - 150], [830, BASE - 90], 2), bowl_shallow(830))] + dots(n_dots, 500, y),
            ["from the top right, down and along the boat, up at the left", "the dots last"])
        add(S, g, "initial", N, [path(tooth(700), exit_from(645))] + dots(n_dots, 700, yi),
            ["a tooth from the right, then on along the line", "the dots last"])
        add(S, g, "medial", N, [path(entry_to(555), tooth(500), exit_from(445))] + dots(n_dots, 500, yi),
            ["along the line, a tooth, and on", "the dots last"])
        add(S, g, "final", N, [path(entry_to(775), L([775, BASE], [720, BASE - 90], 3), bowl_shallow(720))] + dots(n_dots, 450, y),
            ["along the line, up the tooth, down the boat, up at the left", "the dots last"])
    bowl_letter("ب", 1, False)
    bowl_letter("ت", 2, True)
    bowl_letter("ث", 3, True)
    bowl_letter("پ", 3, False)

    # ---- ن: deep bowl alone and at the end
    add(S, "ن", "isolated", N, [bowl_deep(760)] + dots(1, 500, DOT_ABOVE - 30), ["from the top right, round the bowl, up the left", "the dot last"])
    add(S, "ن", "initial", N, [path(tooth(700), exit_from(645))] + dots(1, 700, DOT_ABOVE - 30), ["a tooth, then on", "the dot last"])
    add(S, "ن", "medial", N, [path(entry_to(555), tooth(500), exit_from(445))] + dots(1, 500, DOT_ABOVE - 30), ["along, a tooth, and on", "the dot last"])
    add(S, "ن", "final", N, [path(entry_to(760), L([760, BASE], [720, BASE - 160], 3), bowl_deep(720))] + dots(1, 450, DOT_ABOVE - 30),
        ["along the line, up, then round the deep bowl", "the dot last"])

    # ---- ي and ى
    for g, nd in (("ي", 2), ("ى", 0)):
        iso = [hook_tail(800)] + (dots(nd, 520, 880) if nd else [])
        add(S, g, "isolated", N, iso, ["from the top right, down and left, then the tail under and back", "two dots below" if nd else ""])
        fin = [path(entry_to(775), L([775, BASE], [740, BASE - 90], 3), hook_tail(740))] + (dots(nd, 520, 880) if nd else [])
        add(S, g, "final", N, fin, ["along the line, up the tooth, then the tail under and back", "two dots below" if nd else ""])
    add(S, "ي", "initial", N, [path(tooth(700), exit_from(645))] + dots(2, 700, DOT_BELOW - 40), ["a tooth, then on", "two dots below"])
    add(S, "ي", "medial", N, [path(entry_to(555), tooth(500), exit_from(445))] + dots(2, 500, DOT_BELOW - 40), ["along, a tooth, and on", "two dots below"])

    # ---- ج ح خ چ
    def jeem(g, n_dots, above):
        extra = (dots(n_dots, 600, 300) if above else dots(n_dots, 470, BASE + 90)) if n_dots else []
        add(S, g, "isolated", N, [path(jeem_head(), jeem_bowl(440, BASE - 100))] + extra,
            ["the head from the right, then down into the bowl and round", "the dot(s) last"])
        add(S, g, "initial", N, [path(jeem_head(), L([440, BASE - 100], [470, BASE], 3), exit_from(470))] + (dots(n_dots, 600, 300) if above else dots(n_dots, 560, BASE + 120) if n_dots else []),
            ["the head, then down to the line and on", "the dot(s) last"])
        add(S, g, "medial", N, [path(entry_to(800), L([800, BASE], [780, BASE - 140], 3), jeem_head(780), L([440, BASE - 100], [470, BASE], 3), exit_from(470))]
            + (dots(n_dots, 600, 300) if above else dots(n_dots, 560, BASE + 120) if n_dots else []),
            ["along the line and up, the head, down to the line and on", "the dot(s) last"])
        add(S, g, "final", N, [path(entry_to(800), L([800, BASE], [780, BASE - 140], 3), jeem_head(780), jeem_bowl(440, BASE - 100))] + extra,
            ["along the line and up, the head, then round the bowl", "the dot(s) last"])
    jeem("ج", 1, False)
    jeem("ح", 0, False)
    jeem("خ", 1, True)
    jeem("چ", 3, False)

    # ---- د ذ
    dal = path(L([740, BASE - 220], [340, BASE - 20]), L([340, BASE - 20], [720, BASE + 30]))
    for g, nd in (("د", 0), ("ذ", 1)):
        add(S, g, "isolated", N, [dal] + (dots(nd, 560, 300) if nd else []), ["from the top right down to the point, then right along the line", "the dot last"])
        add(S, g, "final", N, [path(entry_to(760), L([760, BASE], [730, BASE - 210], 3), L([730, BASE - 210], [340, BASE - 20]), L([340, BASE - 20], [700, BASE + 30]))] + (dots(nd, 560, 300) if nd else []),
            ["along the line, up, down to the point, then right along the line", "the dot last"])

    # ---- ر ز ژ
    ra = B([600, BASE - 160], [630, BASE + 40], [420, BASE + 210], [200, BASE + 150])
    for g, nd in (("ر", 0), ("ز", 1), ("ژ", 3)):
        add(S, g, "isolated", N, [ra] + (dots(nd, 560, 330) if nd else []), ["from the top, down and sweep left under the line", "the dot(s) last"])
        add(S, g, "final", N, [path(entry_to(640), L([640, BASE], [600, BASE - 130], 3), B([600, BASE - 130], [640, BASE + 60], [420, BASE + 220], [200, BASE + 160]))] + (dots(nd, 560, 330) if nd else []),
            ["along the line, up, then down and sweep left under the line", "the dot(s) last"])

    # ---- س ش
    for g, nd in (("س", 0), ("ش", 3)):
        d = dots(nd, 760, 340) if nd else []
        add(S, g, "isolated", N, [path(seen_teeth(880), bowl_deep(640, left=180))] + d, ["three teeth from the right, then round the bowl", "three dots above"])
        add(S, g, "initial", N, [path(seen_teeth(880), exit_from(640))] + d, ["three teeth, then on", "three dots above"])
        add(S, g, "medial", N, [path(entry_to(880), seen_teeth(880), exit_from(640))] + d, ["along, three teeth, and on", "three dots above"])
        add(S, g, "final", N, [path(entry_to(880), seen_teeth(880), bowl_deep(640, left=180))] + d, ["along, three teeth, then round the bowl", "three dots above"])

    # ---- ص ض
    for g, nd in (("ص", 0), ("ض", 1)):
        d = dots(nd, 740, 340) if nd else []
        add(S, g, "isolated", N, [path(sad_eye(900), L([560, BASE - 10], [555, BASE], 1), tooth(500), bowl_deep(445, left=170))] + d,
            ["the eye from the left corner over and back, a tooth, then round the bowl", "the dot last"])
        add(S, g, "initial", N, [path(sad_eye(900), L([560, BASE - 10], [555, BASE], 1), tooth(500), exit_from(445))] + d, ["the eye, a tooth, then on", "the dot last"])
        add(S, g, "medial", N, [path(entry_to(900), sad_eye(900), L([560, BASE - 10], [555, BASE], 1), tooth(500), exit_from(445))] + d, ["along, the eye, a tooth, and on", "the dot last"])
        add(S, g, "final", N, [path(entry_to(900), sad_eye(900), L([560, BASE - 10], [555, BASE], 1), tooth(500), bowl_deep(445, left=170))] + d, ["along, the eye, a tooth, then round the bowl", "the dot last"])

    # ---- ط ظ
    for g, nd in (("ط", 0), ("ظ", 1)):
        d = dots(nd, 520, 280) if nd else []
        bar = L([790, BASE - 400], [790, BASE - 10])
        add(S, g, "isolated", N, [sad_eye(800), bar] + d, ["the eye first", "then the tall stroke, top to bottom", "the dot last"])
        add(S, g, "initial", N, [path(sad_eye(800), exit_from(460)), bar] + d, ["the eye, then on along the line", "the tall stroke", "the dot last"])
        add(S, g, "medial", N, [path(entry_to(800), sad_eye(800), exit_from(460)), bar] + d, ["along, the eye, and on", "the tall stroke", "the dot last"])
        add(S, g, "final", N, [path(entry_to(800), sad_eye(800)), bar] + d, ["along the line, then the eye", "the tall stroke", "the dot last"])

    # ---- ع غ
    for g, nd in (("ع", 0), ("غ", 1)):
        d = dots(nd, 600, 250) if nd else []
        add(S, g, "isolated", N, [path(ain_head(), B([580, BASE - 100], [700, BASE + 40], [620, BASE + 260], [400, BASE + 260]), B([400, BASE + 260], [200, BASE + 260], [160, BASE + 80], [300, BASE + 20]))] + d,
            ["the open head from the right, then down into the bowl and round", "the dot last"])
        add(S, g, "initial", N, [path(ain_head(), L([580, BASE - 100], [560, BASE], 3), exit_from(560))] + d, ["the open head, down to the line, and on", "the dot last"])
        add(S, g, "medial", N, [path(entry_to(760), ain_head_medial(760), exit_from(500))] + d, ["along, up into the closed head, down, and on", "the dot last"])
        add(S, g, "final", N, [path(entry_to(760), ain_head_medial(760), B([500, BASE], [700, BASE + 40], [620, BASE + 260], [400, BASE + 260]), B([400, BASE + 260], [200, BASE + 260], [160, BASE + 80], [300, BASE + 20]))] + d,
            ["along, the closed head, then round the bowl", "the dot last"])

    # ---- ف ق
    for g, nd, deep in (("ف", 1, False), ("ق", 2, True)):
        d = dots(nd, 650, 300)
        bowl = bowl_deep(640, left=190) if deep else bowl_shallow(660)
        add(S, g, "isolated", N, [path(loop_head(650, 480), L([650, 550], [660, BASE - 90], 2), bowl)] + d, ["the loop from the bottom, round, then down into the boat", "the dot(s) last"])
        add(S, g, "initial", N, [path(loop_head(650, 480), L([650, 550], [620, BASE], 3), exit_from(620))] + d, ["the loop, down to the line, and on", "the dot(s) last"])
        add(S, g, "medial", N, [path(entry_to(720), L([720, BASE], [650, 550], 3), loop_head(650, 480), L([650, 550], [580, BASE], 3), exit_from(580))] + d, ["along, up into the loop, down, and on", "the dot(s) last"])
        add(S, g, "final", N, [path(entry_to(720), L([720, BASE], [650, 550], 3), loop_head(650, 480), L([650, 550], [660, BASE - 90], 2), bowl)] + d, ["along, the loop, then round the bowl", "the dot(s) last"])

    # ---- ك گ
    for g, extra_bar in (("ك", False), ("گ", True)):
        mark = [L([520, 470], [430, 520])]
        cap = [L([780, 220], [440, 290])]
        top2 = [L([760, 130], [420, 200])] if extra_bar else []
        add(S, g, "isolated", N, [path(L([700, 200], [700, BASE]), bowl_shallow(700))] + mark + top2, ["the tall stroke, top to bottom, then the boat", "the small mark inside", "the second bar"])
        add(S, g, "initial", N, [path(L([760, 220], [600, BASE - 20]), exit_from(600))] + cap + top2, ["the slanted stroke down to the line, and on", "the cap across the top", "the second bar"])
        add(S, g, "medial", N, [path(entry_to(620), L([620, BASE], [720, 240])), path(L([720, 240], [400, 300]), L([400, 300], [520, BASE]), exit_from(520))] + top2,
            ["along the line and up the slant", "the cap, then down to the line and on", "the second bar"])
        add(S, g, "final", N, [entry_to(720), path(L([720, 200], [720, BASE]), bowl_shallow(720))] + mark + top2, ["along the line", "the tall stroke from the top, then the boat", "the small mark inside", "the second bar"])

    # ---- ل
    add(S, "ل", "isolated", N, [path(L([700, 180], [700, BASE - 160]), bowl_deep(700, left=190))], ["top to bottom, then round the deep bowl"])
    add(S, "ل", "initial", N, [path(L([700, 180], [700, BASE]), exit_from(700))], ["top to bottom, then on along the line"])
    add(S, "ل", "medial", N, [path(entry_to(560), L([560, BASE], [545, 200]), L([545, 200], [525, BASE]), exit_from(525))], ["along, up the tall stroke and back down, and on"])
    add(S, "ل", "final", N, [entry_to(720), path(L([720, 180], [720, BASE - 160]), bowl_deep(720, left=190))], ["along the line", "the tall stroke from the top, then round the bowl"])

    # ---- م
    meem_iso = path(A(560, 560, 110, 65, 0, 450), L([560, 625], [560, 900]))
    add(S, "م", "isolated", N, [meem_iso], ["the loop from the right, round, then straight down"])
    add(S, "م", "initial", N, [path(A(700, 555, 100, 65, 90, 450), exit_from(700))], ["the loop from the bottom, round, then on along the line"])
    add(S, "م", "medial", N, [path(entry_to(800), A(700, 555, 100, 65, 90, 450), exit_from(700))], ["along, the loop, and on"])
    add(S, "م", "final", N, [path(entry_to(760), A(660, 555, 100, 65, 90, 450), L([660, 620], [660, 900]))], ["along, the loop, then straight down"])

    # ---- ه ة
    circle = A(500, 560, 150, 110, 270, -90)
    add(S, "ه", "isolated", N, [circle], ["one round, from the top, anticlockwise"])
    add(S, "ه", "initial", N, [path(A(700, 540, 90, 70, 0, 360), L([790, 540], [760, BASE], 3), exit_from(760))], ["a loop from the right, round, down to the line, and on"])
    add(S, "ه", "medial", N, [path(entry_to(760), A(690, 520, 80, 80, 180, 540), A(640, 640, 70, 60, 0, -360), L([710, 640], [700, BASE], 2), exit_from(700))], ["along, up round the top eye, round the bottom eye, and on"])
    add(S, "ه", "final", N, [path(entry_to(700), B([700, BASE], [720, 420], [500, 420], [480, 560]), B([480, 560], [470, 700], [680, 700], [700, BASE]))], ["along, then the teardrop, up and round"])
    add(S, "ة", "isolated", N, [circle] + dots(2, 500, 380), ["one round, from the top", "two dots above"])
    add(S, "ة", "final", N, [path(entry_to(700), B([700, BASE], [720, 420], [500, 420], [480, 560]), B([480, 560], [470, 700], [680, 700], [700, BASE]))] + dots(2, 590, 360), ["along, then the teardrop", "two dots above"])

    # ---- و ؤ
    waw_tail = B([640, 590], [640, 700], [430, 820], [220, 760])
    add(S, "و", "isolated", N, [path(loop_head(620, 520, 90, 75), L([620, 595], [640, 590], 1), waw_tail)], ["the loop from the bottom, round, then sweep left under the line"])
    add(S, "و", "final", N, [path(entry_to(720), L([720, BASE], [640, 595], 3), loop_head(640, 520, 90, 75), waw_tail)], ["along, up into the loop, round, then sweep left"])

    # ---- ء hamza (isolated only in the alphabet's terms)
    hamza = path(L([600, 380], [450, 380], 3), L([450, 380], [520, 500], 3), L([520, 500], [420, 580], 3))
    add(S, "ء", "isolated", N, [hamza], ["right to left, down, and a flick to the left"])
    add(S, "ء", "final", N, [hamza], ["right to left, down, and a flick to the left"])
    add(S, "أ", "isolated", N, [alif(), path(L([620, 90], [520, 90], 2), L([520, 90], [570, 180], 2))], ["the alif, top to bottom", "the hamza above"])
    add(S, "أ", "final", N, [entry_to(560), alif(560), path(L([660, 90], [560, 90], 2), L([560, 90], [610, 180], 2))], ["along the line", "the alif", "the hamza above"])
    add(S, "إ", "isolated", N, [alif(), path(L([620, 730], [520, 730], 2), L([520, 730], [570, 820], 2))], ["the alif, top to bottom", "the hamza below"])
    add(S, "إ", "final", N, [entry_to(560), alif(560), path(L([660, 730], [560, 730], 2), L([560, 730], [610, 820], 2))], ["along the line", "the alif", "the hamza below"])
    add(S, "آ", "isolated", N, [alif(x=520, top=230), B([380, 150], [450, 60], [600, 60], [670, 150])], ["the alif, top to bottom", "the madda across the top"])
    add(S, "آ", "final", N, [entry_to(560), alif(560, top=230), B([420, 150], [490, 60], [640, 60], [710, 150])], ["along the line", "the alif", "the madda"])
    add(S, "ؤ", "isolated", N, [path(loop_head(620, 520, 90, 75), L([620, 595], [640, 590], 1), waw_tail), path(L([700, 300], [600, 300], 2), L([600, 300], [650, 390], 2))], ["the waw", "the hamza above"])
    add(S, "ؤ", "final", N, [path(entry_to(720), L([720, BASE], [640, 595], 3), loop_head(640, 520, 90, 75), waw_tail), path(L([720, 300], [620, 300], 2), L([620, 300], [670, 390], 2))], ["along, the waw", "the hamza above"])


# ======================================================================
# CYRILLIC — Russian cursive (propisi). Baseline y = 700, x-height top
# y = 430, ascender y = 150, descender y = 900. Left to right: entry
# rising from the left, exit rising to the right at (900, 560). Sheared
# 16% for the slant. Capitals: the same construction, taller.
# ======================================================================
C = "cyrillic"
CU = "cursive"
BL = 700
XH = 430
ASC = 150
DESC = 900
EXIT_PT = [900, 560]

def ent(to):
    return L([100, 660], to, 4)

def ext(frm):
    return B(frm, [frm[0] + 30, frm[1] + 50], [760, 640], EXIT_PT)

def oval_a(cx=430, cy=570, rx=150, ry=130):
    """The oval of а/б/д/ф, anticlockwise from the upper right, back to it."""
    return A(cx, cy, rx, ry, -30, -390)

def stem_down(x, top, bottom):
    return L([x, top], [x, bottom], 5)

def u_shape(x0, x1, top=XH):
    """и's construction: down, round the bottom, up, down again."""
    return path(L([x0, top], [x0, BL - 50], 4), B([x0, BL - 50], [x0 + 10, BL + 20], [x1 - 20, BL + 20], [x1, BL - 50]),
                L([x1, BL - 50], [x1, top], 4), L([x1, top], [x1, BL - 20], 4))

def lower():
    a_start = arc_pt(430, 570, 150, 130, -30)
    add(C, "а", "lower", CU, [path(ent(a_start), oval_a(), B(a_start, [600, 560], [600, 650], [590, BL]), ext([590, BL]))],
        ["up to the top right, round the oval, down the side, and on"], joins={"joins_next": True}, slant=True)
    add(C, "б", "lower", CU, [path(ent(a_start), oval_a(), B(a_start, [600, 400], [590, 250], [560, 170]), L([560, 170], [720, 150], 3))],
        ["round the oval, then up the tall stroke and flick right"], joins={"joins_next": False}, slant=True)
    add(C, "в", "lower", CU, [path(ent([330, 640]), L([330, 640], [500, 160], 5), B([500, 160], [560, 120], [560, 260], [480, 300]), L([480, 300], [400, BL], 5),
                                   B([400, BL], [600, BL], [620, 520], [430, 540]), ext([430, 540]))],
        ["up the tall stroke, a small loop at the top, down, then the bump, and on"], joins={"joins_next": True}, slant=True)
    add(C, "г", "lower", CU, [path(ent([450, 450]), B([450, 450], [560, 420], [600, 470], [560, 520]), L([560, 520], [500, BL], 4), ext([500, BL]))],
        ["up, a curl at the top, straight down, and on"], joins={"joins_next": True}, slant=True)
    add(C, "д", "lower", CU, [path(ent(a_start), oval_a(), B(a_start, [600, 600], [590, BL], [560, 800]), B([560, 800], [520, 930], [380, 920], [430, 820]), L([430, 820], EXIT_PT, 5))],
        ["round the oval, down below the line, loop back, and on"], joins={"joins_next": True}, slant=True)
    e_body = path(B([430, 560], [560, 540], [580, 430], [450, 430]), B([450, 430], [300, 440], [280, 690], [440, BL]))
    add(C, "е", "lower", CU, [path(ent([430, 560]), e_body, ext([440, BL]))], ["up to the middle, loop over the top, round the bottom, and on"], joins={"joins_next": True}, slant=True)
    add(C, "ё", "lower", CU, [path(ent([430, 560]), e_body, ext([440, BL])), dot(400, 300), dot(520, 300)], ["as е", "two dots above"], joins={"joins_next": True}, slant=True)
    add(C, "ж", "lower", CU, [B([330, 460], [160, 440], [160, 720], [340, BL]), L([500, XH], [500, BL], 4), path(B([670, 460], [840, 440], [840, 720], [660, BL]), ext([660, BL]))],
        ["the left curve", "the middle stroke, down", "the right curve, and on"], joins={"joins_next": True}, slant=True)
    add(C, "з", "lower", CU, [path(B([300, 470], [470, 400], [620, 450], [520, 560]), B([520, 560], [700, 600], [560, 780], [320, 720]))],
        ["like a 3: round the top, then round the bottom"], joins={"joins_next": False}, slant=True)
    add(C, "и", "lower", CU, [path(ent([280, XH]), u_shape(280, 540), ext([540, BL - 20]))], ["down, round the bottom, up, down again, and on"], joins={"joins_next": True}, slant=True)
    add(C, "й", "lower", CU, [path(ent([280, XH]), u_shape(280, 540), ext([540, BL - 20])), B([330, 300], [400, 380], [500, 380], [560, 300])], ["as и", "the breve above"], joins={"joins_next": True}, slant=True)
    add(C, "к", "lower", CU, [path(ent([260, XH]), stem_down(260, XH, BL)), path(B([260, 580], [400, 440], [480, 480], [430, 560]), B([430, 560], [560, 600], [560, 720], [600, BL]), ext([600, BL]))],
        ["the stroke down", "from the middle: out and up, back, then the leg, and on"], joins={"joins_next": True}, slant=True)
    add(C, "л", "lower", CU, [path(B([150, BL], [200, 560], [300, 470], [380, 440]), L([380, 440], [560, BL], 5), ext([560, BL]))],
        ["a curl up from the line, over the top, down, and on"], joins={"joins_next": True}, slant=True)
    add(C, "м", "lower", CU, [path(B([150, BL], [200, 560], [280, 470], [330, 440]), L([330, 440], [450, BL], 4), L([450, BL], [570, 440], 4), L([570, 440], [690, BL], 4), ext([690, BL]))],
        ["a curl up, two peaks, and on"], joins={"joins_next": True}, slant=True)
    add(C, "н", "lower", CU, [path(ent([260, XH]), stem_down(260, XH, BL), B([260, BL], [280, 560], [500, 560], [560, 470]), L([560, 470], [560, BL], 4), ext([560, BL]))],
        ["down, up through the middle to the second top, down, and on"], joins={"joins_next": True}, slant=True)
    add(C, "о", "lower", CU, [path(ent([300, 570]), A(450, 570, 150, 130, 180, -90), B([450, 440], [600, 440], [760, 560], EXIT_PT))],
        ["round the oval from the left, and off from the top"], joins={"joins_next": True}, slant=True)
    add(C, "п", "lower", CU, [path(ent([260, XH]), stem_down(260, XH, BL), L([260, BL], [260, 480], 4), B([260, 480], [400, 430], [560, 440], [560, 480]), L([560, 480], [560, BL], 4), ext([560, BL]))],
        ["down, back up, over the top, down, and on"], joins={"joins_next": True}, slant=True)
    add(C, "р", "lower", CU, [path(ent([300, XH]), stem_down(300, XH, DESC), L([300, DESC], [300, 560], 5), B([300, 560], [340, 430], [560, 430], [560, 560]), B([560, 560], [560, 720], [340, 720], [320, 620]), L([320, 620], [520, BL], 3), ext([520, BL]))],
        ["down below the line, back up, round the bowl, and on"], joins={"joins_next": True}, slant=True)
    c_start = arc_pt(450, 580, 150, 130, -40)
    add(C, "с", "lower", CU, [path(A(450, 580, 150, 130, -40, -320), ext(arc_pt(450, 580, 150, 130, 40)))], ["from the top right, round, and on"], joins={"joins_next": True, "entry": [int(c_start[0]), int(c_start[1])]}, slant=True)
    add(C, "т", "lower", CU, [path(L([160, BL], [260, 450], 4), L([260, 450], [330, BL], 4), L([330, BL], [430, 450], 4), L([430, 450], [500, BL], 4), L([500, BL], [600, 450], 4), L([600, 450], [670, BL], 4), ext([670, BL])), L([260, 330], [640, 330], 3)],
        ["three peaks like an m, and on", "the bar above"], joins={"joins_next": True}, slant=True)
    add(C, "у", "lower", CU, [path(ent([260, XH]), L([260, XH], [260, 650], 4), B([260, 650], [270, 720], [480, 720], [500, 650]), L([500, 650], [520, XH], 3), L([520, XH], [480, 850], 5), B([480, 850], [450, 960], [300, 930], [360, 820]), L([360, 820], EXIT_PT, 5))],
        ["down, round, up, then down below the line, loop, and on"], joins={"joins_next": True}, slant=True)
    add(C, "ф", "lower", CU, [A(450, 570, 150, 130, 180, -180), L([450, ASC], [450, DESC], 6)], ["the oval", "the tall stroke through it"], joins={"joins_next": False}, slant=True)
    add(C, "х", "lower", CU, [B([260, 470], [430, 500], [430, 680], [260, BL]), path(B([640, 470], [470, 500], [470, 680], [640, BL]), ext([640, BL]))], ["the left curve", "the right curve, and on"], joins={"joins_next": True}, slant=True)
    add(C, "ц", "lower", CU, [path(ent([280, XH]), u_shape(280, 540), L([540, BL - 20], [580, BL], 2), L([580, BL], [580, 820], 3), B([580, 820], [580, 860], [520, 860], [520, 800]), L([520, 800], EXIT_PT, 5))],
        ["as и, then the little hook below, and on"], joins={"joins_next": True}, slant=True)
    add(C, "ч", "lower", CU, [path(ent([260, XH]), L([260, XH], [270, 600], 3), B([270, 600], [280, 660], [520, 660], [560, 560]), L([560, 560], [560, XH], 3), L([560, XH], [560, BL], 4), ext([560, BL]))],
        ["down to the middle, across and up, then down the stroke, and on"], joins={"joins_next": True}, slant=True)
    sh = path(L([240, XH], [240, BL - 50], 4), B([240, BL - 50], [250, BL + 20], [380, BL + 20], [400, BL - 50]), L([400, BL - 50], [400, XH], 4), L([400, XH], [400, BL - 50], 4),
              B([400, BL - 50], [410, BL + 20], [540, BL + 20], [560, BL - 50]), L([560, BL - 50], [560, XH], 4), L([560, XH], [560, BL - 20], 4))
    add(C, "ш", "lower", CU, [path(ent([240, XH]), sh, ext([560, BL - 20]))], ["down, round, up, down, round, up, down, and on"], joins={"joins_next": True}, slant=True)
    add(C, "щ", "lower", CU, [path(ent([240, XH]), sh, L([560, BL - 20], [600, BL], 2), L([600, BL], [600, 820], 3), B([600, 820], [600, 860], [540, 860], [540, 800]), L([540, 800], EXIT_PT, 5))],
        ["as ш, then the little hook below, and on"], joins={"joins_next": True}, slant=True)
    add(C, "ъ", "lower", CU, [path(L([300, 440], [440, 440], 3), L([440, 440], [440, BL], 5), B([440, 600], [600, 560], [620, 720], [440, BL]), ext([440, BL]))],
        ["the hook at the top, down, the bump, and on"], joins={"joins_next": True}, slant=True)
    add(C, "ы", "lower", CU, [path(ent([260, XH]), stem_down(260, XH, BL), B([260, BL], [420, 720], [440, 570], [270, 590])), path(L([600, XH], [600, BL], 5), ext([600, BL]))],
        ["down and the bump", "the second stroke down, and on"], joins={"joins_next": True}, slant=True)
    add(C, "ь", "lower", CU, [path(ent([300, XH]), stem_down(300, XH, BL), B([300, BL], [450, 720], [470, 580], [320, 590]), ext([470, 650]))],
        ["down, the bump, and on"], joins={"joins_next": True}, slant=True)
    add(C, "э", "lower", CU, [A(450, 580, 150, 130, 220, 500), L([450, 580], [590, 580], 3)], ["round from the top left, clockwise", "the bar in the middle"], joins={"joins_next": False}, slant=True)
    add(C, "ю", "lower", CU, [path(ent([220, XH]), stem_down(220, XH, BL), L([220, BL], [230, 590], 3), L([230, 590], [370, 585], 3), A(520, 585, 150, 120, 180, -90), B([520, 465], [680, 470], [780, 560], EXIT_PT))],
        ["down, back to the middle, across, round the oval, and off from the top"], joins={"joins_next": True}, slant=True)
    add(C, "я", "lower", CU, [path(B([300, BL], [340, 520], [400, 440], [560, 440]), L([560, 440], [560, BL], 5), ext([560, BL])), B([560, 460], [400, 430], [320, 580], [540, 590])],
        ["up and over to the top, down the stroke, and on", "the loop on the left"], joins={"joins_next": True}, slant=True)


def upper():
    """Capitals: the lowercase construction, taller, for the shapes Russian
    cursive keeps; its own construction for the ones it does not."""
    tall = {l["glyph"]: l for l in GLYPHS if l["script"] == C and l["form"] == "lower"}
    same = "жзийклмнопстфхцчшщыьэюя"
    for g in same:
        src = tall[g]
        strokes = []
        for s in src["strokes"]:
            # Stretch from the baseline: points above it rise 1.45×.
            strokes.append([[x, BL - (BL - y) * 1.45 if y < BL else y] for x, y in s])
        GLYPHS.append({**src, "form": "upper", "strokes": finish(strokes), "hints": src["hints"]})
    add(C, "а", "upper", CU, [path(L([120, BL], [560, 200], 5), L([560, 200], [640, BL], 5), ext([640, BL])), L([330, 520], [560, 500], 3)],
        ["up the long stroke, down the other, and on", "the bar across"], joins={"joins_next": True}, slant=True)
    add(C, "б", "upper", CU, [path(L([300, 180], [300, BL], 5), B([300, BL], [620, 720], [620, 470], [300, 500])), L([300, 180], [660, 180], 3)],
        ["down the tall stroke, then the bump", "the bar across the top"], joins={"joins_next": False}, slant=True)
    add(C, "в", "upper", CU, [path(L([300, 180], [300, BL], 5), B([300, BL], [620, 720], [620, 470], [300, 470]), B([300, 470], [580, 470], [580, 180], [300, 180]))],
        ["down the tall stroke, the lower bump, the upper bump"], joins={"joins_next": True}, slant=True)
    add(C, "г", "upper", CU, [path(L([300, BL], [300, 180], 5), B([300, 180], [500, 150], [620, 170], [660, 240]))], ["up the tall stroke, then the top curls right"], joins={"joins_next": True}, slant=True)
    add(C, "д", "upper", CU, [path(L([300, 180], [300, BL], 5), B([300, BL], [700, 720], [700, 160], [300, 180]), L([300, BL], [200, 820], 2), L([200, 820], [520, 820], 3), L([520, 820], EXIT_PT, 4))],
        ["down, round the big bowl, back to the foot, the base, and on"], joins={"joins_next": True}, slant=True)
    for g, extra in (("е", []), ("ё", [dot(400, 90), dot(540, 90)])):
        add(C, g, "upper", CU, [path(A(450, 440, 200, 290, -40, -320), ext(arc_pt(450, 440, 200, 290, 40))), L([450, 440], [600, 440], 3)] + extra,
            ["from the top right, round, and on", "the bar in the middle"] + (["two dots above"] if extra else []), joins={"joins_next": True}, slant=True)
    add(C, "р", "upper", CU, [path(L([300, BL], [300, 180], 5), B([300, 180], [640, 160], [640, 480], [300, 470]))], ["up the tall stroke, then the bowl round"], joins={"joins_next": True}, slant=True)
    add(C, "у", "upper", CU, [path(L([200, 200], [450, 560], 4), L([450, 560], [700, 180], 4)), path(L([450, 560], [340, DESC], 4), B([340, DESC], [300, 960], [200, 940], [230, 860]))],
        ["down to the middle and up to the other top", "down below the line and loop"], joins={"joins_next": False}, slant=True)
    add(C, "ъ", "upper", CU, [path(L([260, 200], [440, 200], 3), L([440, 200], [440, BL], 5), B([440, 600], [640, 560], [660, 720], [440, BL]), ext([440, BL]))],
        ["the hook at the top, down, the bump, and on"], joins={"joins_next": True}, slant=True)


def cyrillic():
    lower()
    upper()


# ======================================================================
def main():
    arabic()
    cyrillic()
    by_script: dict[str, list] = {}
    for g in GLYPHS:
        by_script.setdefault(g["script"], []).append(g)
    (ROOT / "data" / "strokes").mkdir(parents=True, exist_ok=True)
    (ROOT / "frontend" / "src" / "features" / "write" / "strokes").mkdir(parents=True, exist_ok=True)
    sql = ["-- PROVISIONAL stroke library (generated by scripts/strokes/gen_provisional.py).",
           "-- Schematic stroke order for Arabic naskh and Russian cursive so the guided",
           "-- modes teach order and direction before a speaker has traced the script.",
           "-- source = 'provisional'; a speaker's save in the Workshop replaces a row.",
           "-- Never re-applied over a speaker's work: ON CONFLICT DO NOTHING.",
           "",
           "INSERT INTO script_glyphs (script, glyph, form, style, strokes, joins, hints, source, reviewed) VALUES"]
    rows = []
    for script, glyphs in by_script.items():
        doc = {"script": script, "glyphs": glyphs, "exemplars": []}
        text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
        (ROOT / "data" / "strokes" / f"{script}.json").write_text(text + "\n", encoding="utf-8")
        (ROOT / "frontend" / "src" / "features" / "write" / "strokes" / f"{script}.json").write_text(text + "\n", encoding="utf-8")
        for g in glyphs:
            def q(v):
                return "'" + json.dumps(v, ensure_ascii=False, separators=(",", ":")).replace("'", "''") + "'"
            rows.append(f"  ('{script}', '{g['glyph']}', '{g['form']}', '{g['style']}', {q(g['strokes'])}::jsonb, "
                        f"{q(g['joins'])}::jsonb, {q(g['hints'])}::jsonb, 'provisional', true)")
    sql.append(",\n".join(rows))
    sql.append("ON CONFLICT (script, glyph, form, style) DO NOTHING;")
    (ROOT / "supabase" / "migrations" / "20261023000000_provisional_strokes.sql").write_text("\n".join(sql) + "\n", encoding="utf-8")
    counts = {s: len(g) for s, g in by_script.items()}
    print("forms:", counts, "total", len(GLYPHS))


if __name__ == "__main__":
    main()
