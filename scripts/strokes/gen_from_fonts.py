# ruff: noqa: E741
"""Derive the PROVISIONAL stroke library from real fonts.

The first library (gen_provisional.py) drew letters from primitives, and
the owner's verdict was the right one: "not reflective of much of the
writing I see". A typeface is what people see. So each form is now
rendered with a standard face — Noto Naskh Arabic for naskh, Marck
Script for Russian cursive (propisi), Noto Sans for print scripts, a
school handwriting model for Latin cursive — thinned to its centreline, traced
into polylines, and ordered by the script's writing rules. The SHAPE is
the font's; the ORDER and DIRECTION are heuristic and marked
provisional, exactly as before.

Coordinates are the font's em box, not a per-glyph fit: 1000 units span
ascender-to-descender, the baseline is at the same y for every glyph of a
script, and x runs from the glyph's left ink edge. That is what lets the
composer join letters — an initial ب's exit stub actually meets a final
ا's entry, and an alif is taller than a ب, as it is on the page. Each
glyph carries `joins.entry`, `joins.exit` (the leftmost/rightmost
skeleton points at the joining side) and `joins.advance` (ink width).

Run (system python — it has Pillow with raqm; the venv does not):
  python3 scripts/strokes/gen_from_fonts.py --fonts <dir> [--only arabic]
Outputs: data/strokes/{script}.json, the bundled frontend copy, and
supabase/migrations/<--migration> (a new file per push),
which UPDATEs only rows still `source = 'provisional'` so a speaker's
tracing is never overwritten.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import struct
import sys
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
# The alphabet module imports the database driver and settings for its
# seeding half; this script only wants the letter lists, and runs on the
# system Python (Pillow with raqm) rather than the venv. So the two small
# tables it needs are executed out of the source files by name, without
# importing the modules around them.
import ast  # noqa: E402


def _load_assignments(path: Path, names: set[str]) -> dict:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        target = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target = node.target.id
        if target in names and node.value is not None:
            out[target] = ast.literal_eval(node.value)
    return out


_alpha = _load_assignments(
    ROOT / "backend" / "services" / "seeder" / "seed_alphabet.py",
    {"RUSSIAN", "GREEK", "ARABIC", "HINDI", "THAI", "HANGUL", "HEBREW", "PERSIAN"},
)
_scripts = _load_assignments(
    ROOT / "backend" / "services" / "scripts.py",
    {"STYLES", "LATIN_EXTRAS", "CASELESS"},
)
STYLES = _scripts["STYLES"]
LATIN_EXTRAS = _scripts["LATIN_EXTRAS"]
CASELESS = _scripts["CASELESS"]
LATIN_BASE = [chr(c) for c in range(ord("a"), ord("z") + 1)]
ALPHABETS = {"ru": _alpha["RUSSIAN"], "el": _alpha["GREEK"], "ar": _alpha["ARABIC"],
             "hi": _alpha["HINDI"], "th": _alpha["THAI"], "ko": _alpha["HANGUL"],
             "he": _alpha["HEBREW"], "fa": _alpha["PERSIAN"]}
NON_JOINING_LEFT = frozenset("اأإآدذرزوةىءؤژ")
CASED = frozenset({"cyrillic", "greek", "latin"})


def forms_for(script: str, glyph: str) -> list[str]:
    if script == "arabic":
        forms = ["isolated", "final"]
        if glyph not in NON_JOINING_LEFT:
            forms += ["initial", "medial"]
        return forms
    if script in CASED:
        return ["lower"] if glyph in CASELESS else ["lower", "upper"]
    return ["letter"]


def alphabet_for(code: str) -> list[dict]:
    rows = ALPHABETS.get(code, [])
    if not rows:
        rows = [(ch, ch, "") for ch in LATIN_BASE + LATIN_EXTRAS.get(code, [])]
    return [{"glyph": g} for g, *_ in rows]

BOX = 1000
EM = 300            # px per em when rendering
TOOTH = EM // 4   # a side branch at most this long, ending free, is a tooth to run up and back
CANVAS = 4 * EM     # px
ZWJ = "‍"

# script -> style -> (font file, per-script rules)
FONTS = {
    "arabic":     {"naskh": "NotoNaskhArabic.ttf"},
    "cyrillic":   {"cursive": "MarckScript-Regular.ttf", "print": "NotoSans.ttf"},
    "greek":      {"print": "NotoSans.ttf"},
    "hebrew":     {"print": "NotoSansHebrew.ttf"},
    "devanagari": {"print": "NotoSansDevanagari.ttf"},
    "thai":       {"print": "NotoSansThaiLooped.ttf"},   # looped: the heads Thai handwriting is taught with
    "hangul":     {"print": "NotoSansKR.ttf"},
    # Latin cursive is a CHAIN, tried in order per glyph: the first face
    # that has the letter draws it. Edu NSW ACT Foundation is an
    # Australian state school handwriting model — a teaching hand, which
    # is what the brief asks a source to be — and it measures far better
    # than Dancing Script against the sourced Zaner-Bloser table (32/52
    # on stroke count against 19, and 31 letters written in ONE stroke
    # against 14, where the table says 40 should be). But it carries 126
    # code points: a-z, A-Z and punctuation, no accented letters at all.
    # Dancing Script is worse as a model and has 559. So a-z come from
    # the teaching hand and á ñ ü ç come from Dancing Script, rather than
    # French and Spanish losing their cursive templates entirely. The
    # seam is real — the two faces do not share an x-height — and is a
    # DEBT entry, not a secret.
    # Also scored, all OFL, all worse: Edu SA Beginner (32/22/27, 29 in
    # one stroke — ties on count, wins on where the stroke ends, loses on
    # the one that matters), Caveat (31/21/26), Edu QLD Beginner
    # (29/25/19), Edu AU VIC WA NT Pre (28/21/24), Edu TAS and Edu VIC
    # (27 each).
    "latin":      {"print": "NotoSans.ttf",
                   "cursive": ["EduNSWACTFoundation.ttf", "DancingScript.ttf"]},
}
RTL = {"arabic", "hebrew"}
CURSIVE = {("cyrillic", "cursive"), ("latin", "cursive")}
# One course per script is enough to enumerate the alphabet; Persian adds
# four letters to the Arabic set, so arabic takes both.
COURSES = {
    "arabic": ["ar", "fa"], "cyrillic": ["ru"], "greek": ["el"], "hebrew": ["he"],
    "devanagari": ["hi"], "thai": ["th"], "hangul": ["ko"],
    # Latin takes every course that adds letters: the bundle is shared, so a
    # French learner and a Yoruba one read the same a-z and each finds their
    # own extras in it. es leads so a-z keeps the front of the list.
    "latin": ["es"] + sorted(LATIN_EXTRAS),
}


# ----------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------
def shaped_text(script: str, glyph: str, form: str) -> str:
    if script == "arabic":
        if form == "initial":
            return glyph + ZWJ
        if form == "medial":
            return ZWJ + glyph + ZWJ
        if form == "final":
            return ZWJ + glyph
        return glyph
    if form == "upper":
        return glyph.upper()
    return glyph


def covered(path: Path) -> set[int]:
    """The code points a face actually maps, read out of its cmap (formats
    4 and 12). PIL will happily draw a .notdef box for a missing glyph and
    the thinner will turn that box into a plausible-looking four-stroke
    letter, so every glyph is checked against this before it is rendered.
    Dancing Script, the Latin cursive face, has no Hausa hooked letters and
    no s-with-dot-below; without this they would ship as rectangles."""
    b = path.read_bytes()
    off = None
    for i in range(struct.unpack(">H", b[4:6])[0]):
        tag, _, o, _ = struct.unpack(">4sIII", b[12 + 16 * i:28 + 16 * i])
        if tag == b"cmap":
            off = o
    if off is None:
        return set()
    cps: set[int] = set()
    for i in range(struct.unpack(">H", b[off + 2:off + 4])[0]):
        _, _, so = struct.unpack(">HHI", b[off + 4 + 8 * i:off + 12 + 8 * i])
        t = off + so
        fmt = struct.unpack(">H", b[t:t + 2])[0]
        if fmt == 4:
            segx2 = struct.unpack(">H", b[t + 6:t + 8])[0]
            seg = segx2 // 2
            ends = struct.unpack(">%dH" % seg, b[t + 14:t + 14 + segx2])
            sp = t + 16 + segx2
            starts = struct.unpack(">%dH" % seg, b[sp:sp + segx2])
            dp = sp + segx2
            deltas = struct.unpack(">%dh" % seg, b[dp:dp + segx2])
            rp = dp + segx2
            ranges = struct.unpack(">%dH" % seg, b[rp:rp + segx2])
            for k in range(seg):
                for c in range(starts[k], min(ends[k], 0xFFFE) + 1):
                    if ranges[k] == 0:
                        g = (c + deltas[k]) & 0xFFFF
                    else:
                        gp = rp + 2 * k + ranges[k] + 2 * (c - starts[k])
                        if gp + 2 > len(b):
                            continue
                        g = struct.unpack(">H", b[gp:gp + 2])[0]
                        if g:
                            g = (g + deltas[k]) & 0xFFFF
                    if g:
                        cps.add(c)
        elif fmt == 12:
            for j in range(struct.unpack(">I", b[t + 12:t + 16])[0]):
                a, e, _ = struct.unpack(">III", b[t + 16 + 12 * j:t + 28 + 12 * j])
                cps.update(range(a, min(e, a + 0x10000) + 1))
    return cps


def render(font: ImageFont.FreeTypeFont, text: str) -> tuple[list[list[int]], int, int, int]:
    """Black-on-white bitmap of *text* as a 0/1 grid, plus the baseline y
    and the ink bbox left/right in pixels."""
    img = Image.new("L", (CANVAS, CANVAS), 255)
    d = ImageDraw.Draw(img)
    ascent, descent = font.getmetrics()
    baseline = CANVAS // 2 + EM // 2
    x0 = CANVAS // 2 - EM
    d.text((x0, baseline), text, font=font, fill=0, anchor="ls")
    px = img.load()
    grid = [[1 if px[x, y] < 128 else 0 for x in range(CANVAS)] for y in range(CANVAS)]
    return grid, baseline, ascent, descent


# ----------------------------------------------------------------------
# Thinning (Zhang–Suen) and pruning, pure Python
# ----------------------------------------------------------------------
def thin(grid: list[list[int]]) -> list[list[int]]:
    h, w = len(grid), len(grid[0])
    g = [row[:] for row in grid]
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            rm = []
            for y in range(1, h - 1):
                row = g[y]
                for x in range(1, w - 1):
                    if row[x] == 0:
                        continue
                    p2 = g[y - 1][x]; p3 = g[y - 1][x + 1]; p4 = row[x + 1]; p5 = g[y + 1][x + 1]
                    p6 = g[y + 1][x]; p7 = g[y + 1][x - 1]; p8 = row[x - 1]; p9 = g[y - 1][x - 1]
                    b = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
                    if b < 2 or b > 6:
                        continue
                    seq = (p2, p3, p4, p5, p6, p7, p8, p9, p2)
                    a = sum(1 for i in range(8) if seq[i] == 0 and seq[i + 1] == 1)
                    if a != 1:
                        continue
                    if step == 0:
                        if p2 * p4 * p6 != 0 or p4 * p6 * p8 != 0:
                            continue
                    else:
                        if p2 * p4 * p8 != 0 or p2 * p6 * p8 != 0:
                            continue
                    rm.append((x, y))
            for x, y in rm:
                g[y][x] = 0
            if rm:
                changed = True
    return g


def neighbours(g, x, y):
    out = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if (dx or dy) and g[y + dy][x + dx]:
                out.append((x + dx, y + dy))
    return out


def minimal(g: list[list[int]]) -> None:
    """Thin the skeleton to one pixel: delete any pixel with two or more
    neighbours that stay connected to each other without it. Zhang–Suen
    leaves two-pixel steps on diagonals and two parallel tracks where a
    stroke was thick, and every walk over those needs a special case —
    a tip that looks like a fork, a leftover that leads the pen back the
    way it came. Removing the redundancy first is cheaper than reasoning
    around it. Endpoints (one neighbour) and true junctions (neighbours
    in separate groups) stay."""
    h, w = len(g), len(g[0])
    changed = True
    while changed:
        changed = False
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                if not g[y][x]:
                    continue
                nb = [(x + i, y + j) for i in (-1, 0, 1) for j in (-1, 0, 1) if (i or j) and g[y + j][x + i]]
                if len(nb) < 2:
                    continue
                if len(branches(nb)) == 1:
                    g[y][x] = 0
                    changed = True

def prune_spurs(g: list[list[int]], min_len: int) -> None:
    """Remove endpoint branches shorter than *min_len* pixels — thinning
    artefacts at serifs and stroke ends, not strokes."""
    h, w = len(g), len(g[0])
    for _ in range(3):
        endpoints = [(x, y) for y in range(1, h - 1) for x in range(1, w - 1)
                     if g[y][x] and len(neighbours(g, x, y)) == 1]
        removed = False
        for x, y in endpoints:
            path = [(x, y)]
            prev = None
            cx, cy = x, y
            while True:
                nb = [p for p in neighbours(g, cx, cy) if p != prev and p not in path]
                if len(nb) != 1:
                    break
                prev = (cx, cy)
                cx, cy = nb[0]
                if len(neighbours(g, cx, cy)) >= 3:
                    break
                path.append((cx, cy))
                if len(path) > min_len:
                    break
            if len(path) <= min_len and len(neighbours(g, cx, cy)) >= 3:
                for px_, py_ in path:
                    g[py_][px_] = 0
                removed = True
        if not removed:
            break


# ----------------------------------------------------------------------
# Skeleton -> graph -> strokes
# ----------------------------------------------------------------------
def components(g):
    h, w = len(g), len(g[0])
    seen = set()
    comps = []
    for y in range(h):
        for x in range(w):
            if g[y][x] and (x, y) not in seen:
                stack = [(x, y)]
                comp = set()
                while stack:
                    p = stack.pop()
                    if p in comp:
                        continue
                    comp.add(p)
                    for q in neighbours(g, *p):
                        if q not in comp:
                            stack.append(q)
                seen |= comp
                comps.append(comp)
    return comps


def branches(pts: list) -> list[list]:
    """Group pixels that touch each other: two unvisited neighbours that
    are themselves adjacent are one way on (a staircase), not a fork."""
    groups: list[list] = []
    for p in pts:
        mine = [grp for grp in groups if any(abs(p[0] - q[0]) <= 1 and abs(p[1] - q[1]) <= 1 for q in grp)]
        if not mine:
            groups.append([p])
        else:
            mine[0].append(p)
            for grp in mine[1:]:
                mine[0].extend(grp)
                grp.clear()
    return [grp for grp in groups if grp]


def head_ring(ink: list[list[int]], sk: list[list[int]], comp: set) -> tuple[list, tuple] | None:
    """A Thai letter's head: the smallest enclosed hole in the ink, and the
    ring of skeleton pixels around it. Returns (ring pixels, hole centre)
    or None. Found on the ink, not the skeleton graph: at this size a head
    is a ring a few pixels across, and a cycle search through its fork
    keeps finding the two-pixel short cut instead."""
    h, w = len(ink), len(ink[0])
    outside = set()
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    stack = [p for p in stack if not ink[p[1]][p[0]]]
    while stack:
        x, y = stack.pop()
        if (x, y) in outside:
            continue
        outside.add((x, y))
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not ink[ny][nx] and (nx, ny) not in outside:
                stack.append((nx, ny))
    holes = []
    seen = set()
    for y in range(h):
        for x in range(w):
            if ink[y][x] or (x, y) in outside or (x, y) in seen:
                continue
            hole = set()
            stack = [(x, y)]
            while stack:
                p = stack.pop()
                if p in hole:
                    continue
                hole.add(p)
                for q in ((p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)):
                    if 0 <= q[0] < w and 0 <= q[1] < h and not ink[q[1]][q[0]] and q not in outside and q not in hole:
                        stack.append(q)
            seen |= hole
            if 2 <= len(hole) <= (EM // 8) ** 2:
                holes.append(hole)
    if not holes:
        return None
    hole = min(holes, key=len)
    cx = sum(p[0] for p in hole) / len(hole)
    cy = sum(p[1] for p in hole) / len(hole)
    dist = {p: min(max(abs(p[0] - q[0]), abs(p[1] - q[1])) for q in hole) for p in comp}
    dmin = min(dist.values())
    if dmin > EM // 10:
        return None
    ring = {p for p in comp if dist[p] <= dmin + 3}
    # The ring proper is the part of that band which encircles the hole:
    # keep the connected piece nearest the hole.
    pieces = []
    left = set(ring)
    while left:
        start = left.pop()
        piece = {start}
        stack = [start]
        while stack:
            p = stack.pop()
            for q in neighbours(sk, *p):
                if q in left:
                    left.discard(q)
                    piece.add(q)
                    stack.append(q)
        pieces.append(piece)
    ring = max(pieces, key=len)
    if len(ring) < 6:
        return None
    return sorted(ring), (cx, cy)


def is_tip(g, comp: set, p: tuple) -> bool:
    """A stroke end on the skeleton: one neighbour, or two that both lie
    ahead (a thinned diagonal ends in a two-pixel step). Two neighbours on
    opposite sides is the inside of a line."""
    nb = [q for q in neighbours(g, *p) if q in comp]
    if len(nb) == 1:
        return True
    if len(nb) == 2:
        (a, b) = nb
        return (a[0] - p[0]) * (b[0] - p[0]) + (a[1] - p[1]) * (b[1] - p[1]) > 0
    return False


def vertical_prefix(path: list) -> int:
    """How many pixels from the start of *path* run more tall than wide
    before it turns — the length of a stem, whatever hangs off its foot."""
    a = path[0]
    best = 0
    for i, p in enumerate(path):
        dx, dy = abs(p[0] - a[0]), abs(p[1] - a[1])
        if dy >= 2 * dx:
            best = i
        elif i > 4:
            break
    return best


def run_from(g, comp: set, e: tuple, avoid: set, cap: int) -> list:
    """The pixels from *e* following the skeleton while it does not fork,
    at most *cap* long."""
    path = [e]
    seen = set(avoid) | {e}
    p = e
    while len(path) <= cap:
        nb = [q for q in neighbours(g, *p) if q in comp and q not in seen]
        grps = branches(nb)
        if len(grps) != 1:
            break
        p = grps[0][0]
        seen.update(grps[0])
        path.append(p)
    return path


def unit(frm, to):
    dx, dy = to[0] - frm[0], to[1] - frm[1]
    n = math.hypot(dx, dy) or 1.0
    return dx / n, dy / n


JUNCTION = 4        # px: the ring a junction's limbs are told apart on
REACH = 16          # px: how far along each limb its direction is measured


def arms(g, comp: set, p: tuple, blocked: set,
         radius: int = JUNCTION, reach: int = REACH) -> list[list]:
    """The distinct limbs of the letter leaving *p*, each as the path from
    *p* out along it, up to *reach* pixels.

    This exists because thinning leaves a junction as a cluster two or
    three pixels across, so the first pixel of the crossbar's left arm,
    the first of its right arm and the first of the stem all touch one
    another — `branches` groups pixels that touch, so it calls them two
    ways on, not three, and the stem is absorbed into whichever group
    claims it. That is why `crossing` never fired: walking down the f's
    hook it was offered "left" and "right" and never saw the stem, so it
    turned along the crossbar and the stem became a second stroke.

    Two distances, because one cannot do both jobs. *radius* is small, a
    circle close enough in that each limb still crosses it exactly once —
    that is what tells the limbs apart. *reach* is long, so a limb's
    direction is the direction of its run and not of the two pixels
    nearest the cluster, which all point much the same way. Tried with a
    single radius first: 4 split the f correctly and left the t turning
    along its crossbar, 12 did the reverse.

    A limb shorter than *radius* never crosses the circle and is left out;
    that is wanted, since a stub is not an arm of a crossing."""
    parent = {p: None}
    depth = {p: 0}
    ring: list = []
    frontier = [p]
    for step in range(1, reach + 1):
        nxt = []
        for q in frontier:
            for r in neighbours(g, *q):
                if r in parent or r not in comp or r in blocked:
                    continue
                parent[r], depth[r] = q, step
                nxt.append(r)
                if step == radius:
                    ring.append(r)
        frontier = nxt
        if not frontier:
            break
    if not ring:
        return []
    group_of = {}
    for i, grp in enumerate(branches(ring)):
        for q in grp:
            group_of[q] = i
    # Each pixel past the ring belongs to the limb it grew from; the
    # farthest one in a limb gives that limb its direction.
    far: dict[int, tuple] = {}
    for q, d in depth.items():
        if d <= radius:
            continue
        a = q
        while depth[a] > radius:
            a = parent[a]
        i = group_of.get(a)
        if i is None:
            continue
        if i not in far or d > depth[far[i]]:
            far[i] = q
    out = []
    for i in sorted(set(group_of.values())):
        end = far.get(i)
        if end is None:
            end = next(q for q in ring if group_of[q] == i)
        path = []
        q = end
        while q is not None and q != p:
            path.append(q)
            q = parent[q]
        if path:
            out.append(list(reversed(path)))
    return out


def crossing(ways: list, p: tuple, incoming: tuple):
    """Where a bar crosses a stem (f t A E ж х ф), the two arms of the bar
    are one stroke and the stem is another. Two of the ways out lie nearly
    opposite each other — that pair is the crossing stroke — so a walk
    arriving on neither of them carries on through the junction on the
    remaining way, leaving the pair to be drawn as its own stroke.
    Returns the way to take, or None when this is not a crossing."""
    if len(ways) < 3:
        return None
    n = math.hypot(*incoming) or 1.0
    inc = (incoming[0] / n, incoming[1] / n)
    dirs = [unit(p, r) for r in ways]
    pair = None
    best = -0.75
    for i in range(len(ways)):
        for j in range(i + 1, len(ways)):
            d = dirs[i][0] * dirs[j][0] + dirs[i][1] * dirs[j][1]
            if d < best:
                best, pair = d, (i, j)
    if pair is None:
        return None
    # Arriving along the crossing stroke itself: carry on along it.
    aligned = [k for k in pair if abs(inc[0] * dirs[k][0] + inc[1] * dirs[k][1]) > 0.75]
    rest = [k for k in range(len(ways)) if k not in pair]
    if aligned:
        return ways[max(pair, key=lambda k: inc[0] * dirs[k][0] + inc[1] * dirs[k][1])]
    if not rest:
        return None
    return ways[max(rest, key=lambda k: inc[0] * dirs[k][0] + inc[1] * dirs[k][1])]


def upright_end(g, comp: set, e: tuple) -> bool:
    """Whether endpoint *e* is the free end of an upright that hangs at a
    fork: a run down from it more tall than wide for longer than a tooth,
    whose foot meets the letter in two directions (the stem of ط on its
    loop). A stem that simply turns into the base (ك) is the start of one
    stroke, and an alif is vertical all the way: neither is a stem."""
    path = run_from(g, comp, e, set(), 3 * TOOTH)
    v = vertical_prefix(path)
    if v <= TOOTH:
        return False
    foot = path[v]
    stem = set(path[: v + 1])
    around = [q for q in comp if q not in stem and max(abs(q[0] - foot[0]), abs(q[1] - foot[1])) <= 2]
    if len(branches(around)) >= 2:
        return True
    # Or the letter goes on to the RIGHT after the foot — back under the
    # body, into a loop (initial ط): a stem hung on a bowl. A stem whose
    # base runs on leftwards (ك) is the start of one stroke.
    ahead = path[min(v + 10, len(path) - 1)]
    return ahead[0] > foot[0] + 4


def trace_component(g, comp: set, start: tuple, teeth: bool = False,
                    second: tuple | None = None, loop: set | None = None,
                    joined: bool = False) -> list[list[tuple]]:
    """Walk the component into strokes: from *start*, always take the
    straightest unvisited continuation at a fork; a new stroke begins at
    the next unvisited endpoint (or the topmost unvisited pixel).

    With *teeth* (Arabic), a short branch off a fork that ends free — the
    teeth of س ش, the notches of ب ت in the middle of a word — is run up
    and back down as part of the same stroke, the way the hand does it,
    instead of being left for a stroke of its own.

    With *second* the first step is forced (which way round a head goes);
    with *loop*, a walk that dead-ends next to its own start hops back to
    the start and carries on — a head circled fully, then the body."""
    visited = set()
    swallowed = set()   # leftover parallel tracks: out of play, but not "drawn"
    strokes = []
    forks_seen = 0

    def degree(p):
        return 1 if is_tip(g, comp, p) else 2

    def at_fork(p):
        # Three or more ways out counting visited ones: a real junction of
        # the skeleton, where an upright may hang off. Checked before the
        # costly upright() walk, which must not run at every pixel.
        return len(branches([q for q in neighbours(g, *p) if q in comp])) >= 3

    def near(p, d=2):
        return [(p[0] + i, p[1] + j) for i in range(-d, d + 1) for j in range(-d, d + 1) if (i or j)]

    recent: list = []   # the last few pixels of the current walk

    def forks(p, prev):
        """The ways on from *p*: unvisited pixels within two of it, grouped
        by adjacency. Two pixels out, not one, because thinning leaves the
        junctions as small clusters that a walk can pass beside — the tooth
        of ـبـ hangs off a pixel next to the path, not on it."""
        # A way on touches only the last few pixels of the walk (a tight
        # turn touches three or four); a pixel that also touches older
        # drawn pixels is a leftover parallel track of the thinning, and
        # following it walks the letter backwards.
        tail = set(recent[-5:]) | {p, prev}

        def fresh(q):
            return not any(v in visited and v not in tail for v in neighbours(g, *q))
        nb = [q for q in near(p) if q in comp and q not in visited and q not in swallowed and fresh(q)]
        grps = branches(nb)
        # Each group's representative: the member nearest p, then the straightest.
        out = []
        for grp in grps:
            dmin = min(max(abs(r[0] - p[0]), abs(r[1] - p[1])) for r in grp)
            close = [r for r in grp if max(abs(r[0] - p[0]), abs(r[1] - p[1])) == dmin]
            if prev is None:
                rep = close[0]
            else:
                dx, dy = p[0] - prev[0], p[1] - prev[1]
                rep = max(close, key=lambda r: (r[0] - p[0]) * dx + (r[1] - p[1]) * dy)
            if shadow_branch(rep, p):
                continue            # a leftover track beside what is drawn, not a way on
            out.append(rep)
        return out

    def shadow_branch(r, frm):
        """Follow the branch from *r* for up to a tooth's length: if every
        pixel of it lies within two of something already drawn, it only
        shadows the path (thinning left the base two pixels thick) and
        walking it would draw the letter backwards."""
        path = [r]
        seen = {frm, r}
        p = r
        while len(path) <= TOOTH:
            nb = [q for q in neighbours(g, *p) if q in comp and q not in seen and q not in visited and q not in swallowed]
            grps = branches(nb)
            if len(grps) != 1:
                break
            p = grps[0][0]
            seen.update(grps[0])
            path.append(p)
        # The first pixels of any branch sit next to the path it leaves;
        # only the far part tells a leftover track from a real way on.
        far = path[3:]
        if len(far) < 3:
            return False
        return all(any(v in visited for v in near(q)) for q in far)

    def shadows(path):
        # Every pixel within two of something already drawn: a leftover
        # parallel track of the thinning, not a branch of the letter.
        return all(any(v in visited for v in near(q)) for q in path)

    def dead_end(r, frm, cap=None):
        """The pixels from *r* to a free end if the branch forks nowhere
        and is at most *cap* (a tooth) long; else None."""
        cap = TOOTH if cap is None else cap
        path = [r]
        seen = {frm, r}
        prev, p = frm, r
        while len(path) <= cap:
            nb = [q for q in neighbours(g, *p) if q in comp and q not in seen and q not in visited and q not in swallowed]
            grps = branches(nb)
            if not grps:
                return path
            if len(grps) > 1:
                return None
            dx, dy = p[0] - prev[0], p[1] - prev[1]
            q = max(grps[0], key=lambda t: (t[0] - p[0]) * dx + (t[1] - p[1]) * dy)
            seen.update(grps[0])
            path.append(q)
            prev, p = p, q
        return None

    def returns(r, frm):
        """Whether the branch from *r* closes back onto what is already
        drawn — the far side of a loop (ص, ه). The hand finishes the loop
        before it moves on to the bowl."""
        path = run_from(g, comp, r, visited | swallowed | {frm}, 3 * TOOTH)
        end = path[-1]
        return len(path) > 8 and any(v in visited and v != frm for v in near(end))

    def upright(r, frm):
        """True if the branch from *r* is an upright: a run more tall than
        wide for longer than a tooth, ending free — the stem of ط ظ ك. The
        hand writes it as a stroke of its own, top down, after the bowl,
        so the walk must not run on into it."""
        path = run_from(g, comp, r, visited | swallowed | {frm}, 3 * TOOTH)
        if len(path) > 3 * TOOTH:
            return False
        nb = [q for q in neighbours(g, *path[-1]) if q in comp and q not in visited and q not in swallowed and q not in path]
        if branches(nb):
            return False          # it goes on into something: not a free-ended stem
        v = vertical_prefix(path)
        return v > TOOTH and v >= 0.8 * len(path)   # a stem, not a stem that turns into a base

    def walk(p):
        nonlocal forks_seen
        path = [p]
        visited.add(p)
        recent.clear()
        recent.append(p)
        first = p
        prev = None
        while True:
            ways = forks(p, prev)
            if not ways and loop and p != first and abs(p[0] - first[0]) <= 1 and abs(p[1] - first[1]) <= 1:
                # Back round to where the head began: close it and go on.
                path.append(first)
                prev, p = p, first
                ways = forks(p, prev)
            if not ways:
                break
            if prev is None and second in ways:
                q = second
            elif len(ways) > 1 and teeth:
                # At the first fork after a join the hand retraces what
                # hangs there — the hook of ـد, the tooth of ـبـ — up and
                # back, however long within reason, before going on.
                cap = 3 * TOOTH if (joined and forks_seen == 0) else None
                forks_seen += 1
                ends = {r: dead_end(r, p, cap) for r in ways}
                for r, e in list(ends.items()):
                    if e and shadows(e):
                        swallowed.update(e)    # a parallel leftover: out of play, not drawn
                        ways = [w for w in ways if w != r]
                        del ends[r]
                if not ways:
                    break
                if len(ways) == 1:
                    q = ways[0]
                    visited.add(q)
                    path.append(q)
                    recent.append(q)
                    prev, p = p, q
                    continue
                through = [r for r in ways if ends[r] is None and not upright(r, p)]
                if not through:
                    ups = [r for r in ways if ends[r] is None]   # what goes on is only uprights
                    if ups and (not joined or forks_seen > 1) and len(path) > 5:
                        # Teeth here are still retraced; then the walk ends —
                        # the upright is written on its own, top down.
                        for r in ways:
                            if ends[r]:
                                visited.update(ends[r])
                                path.extend(ends[r])
                                path.extend(reversed(ends[r][:-1]))
                                path.append(p)
                        break
                    through = ups
                # Continue on a branch that goes somewhere; if every branch
                # ends free, on the straightest — the rest are teeth.
                if len(through) > 1:
                    # A way that comes back round to this fork is a loop of
                    # the letter (ص, ه): the hand draws it before moving on.
                    loops = [r for r in through if returns(r, p)]
                    if loops:
                        through = loops
                if through:
                    q = through[0] if prev is None else max(
                        through, key=lambda r: (r[0] - p[0]) * (p[0] - prev[0]) + (r[1] - p[1]) * (p[1] - prev[1]))
                elif joined and forks_seen == 1:
                    # Everything at the join's fork ends free (the hook and
                    # the base of ـد): the way on is the one that ends
                    # nearest the exit, leftmost; the rest are retraced.
                    q = min(ways, key=lambda r: ends[r][-1][0])
                else:
                    q = ways[0] if prev is None else max(
                        ways, key=lambda r: (r[0] - p[0]) * (p[0] - prev[0]) + (r[1] - p[1]) * (p[1] - prev[1]))
                for r in ways:
                    if r != q and ends[r]:
                        visited.update(ends[r])
                        path.extend(ends[r])
                        path.extend(reversed(ends[r][:-1]))
                        path.append(p)
            elif len(ways) > 1 and prev is not None:
                dx, dy = p[0] - prev[0], p[1] - prev[1]
                q = None
                # Ask the ring first: at a crossing the ways next to the
                # walk under-count the limbs (see arms), and the whole
                # point of crossing() is to carry the pen through.
                limbs = arms(g, comp, p, visited | swallowed)
                if len(limbs) >= 3:
                    # Over a run, not a pixel: the limbs' directions are
                    # measured over REACH, and an incoming measured over
                    # one step is not comparable with them. The f arrives
                    # at its crossbar on a hook that is still curving, and
                    # a one-pixel reading of it points down-LEFT — enough
                    # for crossing() to call it "already on the bar" and
                    # turn the pen along the bar, which is the whole fault
                    # being fixed here.
                    back = recent[-(REACH + 1)] if len(recent) > REACH else recent[0]
                    reps = [lm[-1] for lm in limbs]
                    pick = crossing(reps, p, (p[0] - back[0], p[1] - back[1]))
                    if pick is not None:
                        lm = limbs[reps.index(pick)]
                        for r in lm[:-1]:       # across the junction cluster
                            visited.add(r)
                            path.append(r)
                            recent.append(r)
                        if len(lm) > 1:
                            p = lm[-2]
                        q = pick
                if q is None:
                    q = crossing(ways, p, (dx, dy))
                if q is None:
                    q = max(ways, key=lambda r: (r[0] - p[0]) * dx + (r[1] - p[1]) * dy)
            elif (teeth and not joined and len(path) > TOOTH
                  and vertical_prefix(path) < len(path) - 5 and upright(ways[0], p)):
                break   # a body is drawn (not just a stem so far) and only an upright is left: it is written on its own
            else:
                q = ways[0]
            visited.add(q)
            path.append(q)
            recent.append(q)
            prev, p = p, q
        return path

    strokes.append(walk(start))
    while True:
        left = [p for p in comp if p not in visited and p not in swallowed]
        if not left:
            break
        ends = [p for p in left if degree(p) == 1]
        cand = ends or left
        nxt = min(cand, key=lambda p: (p[1], p[0]))
        s = walk(nxt)
        if len(s) >= 3:
            strokes.append(s)
        # Tiny leftovers (junction fragments) are absorbed silently.
        for p in s:
            visited.add(p)
    return strokes


def headline_last(out: list[list], kinds: list[str]) -> tuple[list[list], list[str]]:
    """Devanagari: the shirorekha is written after the body — and after the
    whole word, so it is deferred like a mark. The walk starts at the top
    and often fuses the headline with the stem it meets; a body stroke
    whose leading or trailing run lies along the top edge and spans most
    of the letter is cut there, the headline pieces run left to right,
    and they go after the bodies, before the dots."""
    pts = [p for s in out for p in s]
    top = min(p[1] for p in pts)
    gh = max(1, max(p[1] for p in pts) - top)
    gw = max(1, max(p[0] for p in pts) - min(p[0] for p in pts))
    band = top + 0.10 * gh

    def on_top(p):
        return p[1] <= band

    def is_line(seg):
        return len(seg) >= 2 and (max(p[0] for p in seg) - min(p[0] for p in seg)) >= 0.45 * gw

    bodies, heads, marks = [], [], []
    for s, kind in zip(out, kinds):
        if kind != "body":
            marks.append(s)
            continue
        if all(on_top(p) for p in s) and is_line(s):
            heads.append(s)
            continue
        k = 0
        while k < len(s) and on_top(s[k]):
            k += 1
        if is_line(s[:k]) and len(s) - k >= 1:
            heads.append(s[:k + 1] if k < len(s) else s[:k])
            s = s[k:] if k < len(s) else []
        if len(s) >= 2:
            j = len(s)
            while j > 0 and on_top(s[j - 1]):
                j -= 1
            if is_line(s[j:]) and j >= 1:
                heads.append(s[j - 1:])
                s = s[:j]
        if len(s) >= 2:
            bodies.append(s)
    heads = [h if h[0][0] <= h[-1][0] else h[::-1] for h in heads]
    heads.sort(key=lambda h: h[0][0])
    return bodies + heads + marks, ["body"] * len(bodies) + ["headline"] * len(heads) + ["mark"] * len(marks)


def path_len(path) -> float:
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:]))


def merge_to(strokes: list, target: int, cap: float) -> list:
    """Join strokes at their nearest ends until there are *target*.

    The mirror of `split_to`, and needed for the same reason from the
    other side. Thai measured 18/44 on stroke count, and its gap is the
    opposite shape to Cyrillic print's: **39 of the 44 taught letters are
    a single movement and ours managed 18, drawing MORE strokes than
    taught for 26 letters and fewer for none.** A Thai consonant is one
    continuous line from its head loop, but the skeleton forks where the
    line crosses itself and the walk stops at each fork. `split_to` can
    do nothing there — it only adds.

    Joins the closest pair of ends first, trying both orientations, and
    only when they lie within *cap*. A letter whose pieces are genuinely
    far apart keeps them and shows up in the checker as a disagreement,
    which is the honest outcome: this is for re-joining a line the walk
    cut, not for drawing a bridge between two parts of a letter that a
    hand really does lift between. Like `split_to` it only runs for a
    letter with a sourced row."""
    out = [list(t) for t in strokes]
    while len(out) > target and len(out) > 1:
        best = None
        for i in range(len(out)):
            for j in range(len(out)):
                if i == j:
                    continue
                for rev in (False, True):
                    b = out[j][::-1] if rev else out[j]
                    d = math.hypot(b[0][0] - out[i][-1][0], b[0][1] - out[i][-1][1])
                    if best is None or d < best[0]:
                        best = (d, i, j, rev)
        if best is None or best[0] > cap:
            break
        _, i, j, rev = best
        b = out[j][::-1] if rev else out[j]
        joined = out[i] + b
        keep = min(i, j)
        out = [t for k, t in enumerate(out) if k not in (i, j)]
        out.insert(keep, joined)
    return out


ZONES = {"top-left": (0, 0), "top": (1, 0), "top-right": (2, 0),
         "left": (0, 1), "centre": (1, 1), "right": (2, 1),
         "bottom-left": (0, 2), "bottom": (1, 2), "bottom-right": (2, 2),
         "baseline-left": (0, 2), "baseline-right": (2, 2), "baseline": (1, 2)}


def zone_at(p, box) -> tuple:
    """Which ninth of the glyph's ink box a point falls in, as (col, row)."""
    x0, y0, x1, y1 = box
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    return (int(min(2, max(0, (p[0] - x0) * 3 // w))),
            int(min(2, max(0, (p[1] - y0) * 3 // h))))


def fit_taught(strokes: list, taught: list) -> list:
    """Put the strokes in the taught order, each running the taught way.

    The generator already splits and merges to the number of strokes a
    letter is taught in. This settles the other two thirds of the
    question: which stroke comes first, and which way round each one
    runs. Both were heuristics, and the owner found three letters where
    the heuristic lost — uppercase B drawn bowls-then-stem where it is
    taught stem-then-bowls, lowercase a ending mid-letter going up where
    it is taught ending at the baseline coming down, and d starting at
    the stem where it is taught starting at the bowl.

    Every stroke keeps its shape; only the order of the list and the
    direction of each path change. It is an assignment problem — match
    our strokes to the taught ones so the total distance between where
    each starts and ends and where the source says it should is as small
    as it can be — and with at most a handful of strokes per letter the
    permutations can simply be enumerated.

    Safe for the composer: `joins.entry` and `joins.exit` are the
    leftmost and rightmost points of the ink, not the first and last
    points of a stroke, so neither moves when a stroke is reversed."""
    n = len(strokes)
    if n == 0 or n > len(taught):
        return strokes
    pts = [p for s in strokes for p in s]
    box = (min(p[0] for p in pts), min(p[1] for p in pts),
           max(p[0] for p in pts), max(p[1] for p in pts))

    def miss(p, name):
        z = ZONES.get(name or "")
        if z is None:
            return 0.0
        c, r = zone_at(p, box)
        return abs(c - z[0]) + abs(r - z[1])

    # cost[i][j] = (best cost of using our stroke j for taught stroke i, reversed?)
    cost = []
    for i in range(n):
        want = taught[i]
        row = []
        for j in range(n):
            s = strokes[j]
            fwd = miss(s[0], want.get("from")) + miss(s[-1], want.get("to"))
            rev = miss(s[-1], want.get("from")) + miss(s[0], want.get("to"))
            row.append((fwd, False) if fwd <= rev else (rev, True))
        cost.append(row)

    best = None
    if n <= 7:
        for perm in itertools.permutations(range(n)):
            total = sum(cost[i][perm[i]][0] for i in range(n))
            if best is None or total < best[0]:
                best = (total, perm)
        perm = best[1]
    else:                                   # rare; greedy is close enough
        perm, used = [], set()
        for i in range(n):
            j = min((j for j in range(n) if j not in used), key=lambda j: cost[i][j][0])
            perm.append(j)
            used.add(j)
    out = []
    for i, j in enumerate(perm):
        s = strokes[j]
        out.append(list(reversed(s)) if cost[i][j][1] else list(s))
    return out


def zone_heading(a: str, b: str):
    """The direction a taught stroke runs, read off its two zone names,
    or None when they are the same zone and say nothing about it."""
    za, zb = ZONES.get(a or ""), ZONES.get(b or "")
    if za is None or zb is None or za == zb:
        return None
    dx, dy = zb[0] - za[0], zb[1] - za[1]
    n = math.hypot(dx, dy) or 1.0
    return dx / n, dy / n


def runs_with(path: list, aim: tuple) -> bool:
    """Whether *path* travels, end to end, the way *aim* points."""
    dx, dy = path[-1][0] - path[0][0], path[-1][1] - path[0][1]
    n = math.hypot(dx, dy)
    return n < 1 or (dx / n) * aim[0] + (dy / n) * aim[1] > 0


def start_ring_where_taught(strokes: list, taught: list) -> list:
    """Move a closed stroke's first point to where the source starts it.

    Where a stroke comes back to where it began, *where* it began is an
    artifact of the walk — the trace had to enter the ring somewhere —
    and not a fact about the letter. It is a fact about the letter to
    the teacher, though: a Russian о is started at two o'clock and taken
    anticlockwise, and a printed o in a Zaner-Bloser book the same. So
    for a closed stroke, and only a closed one, rotate the point list to
    start nearest the taught zone and run it whichever way agrees with
    the taught direction.

    `fit_taught` cannot do this. It chooses which stroke and which way
    round, but a ring is the same ring from either end; only rotation
    moves the pen's starting point around it. Seventeen letters across
    six tables fail on a closed stroke and nothing else; this reaches
    the five whose ring stands alone (o, о, ο and the letters built on
    them). The other twelve — the bowls of ь and ы, م in two of its
    forms — close against a neighbouring stroke, and there the starting
    point is the join and is not ours to move."""
    # Which JUNCTION-sized cells each stroke passes through, and the ring
    # of cells around them: two strokes that share one are touching. Done
    # on a grid rather than by comparing every pair of points, which is
    # quadratic in the length of a traced outline.
    def cellsof(t):
        c = {(int(x // JUNCTION), int(y // JUNCTION)) for x, y in t}
        return {(cx + dx, cy + dy) for cx, cy in c for dx in (-1, 0, 1) for dy in (-1, 0, 1)}

    cells = [cellsof(t) for t in strokes]
    out = []
    for i, s in enumerate(strokes):
        want = taught[i] if i < len(taught) else None
        span = max(math.dist(a, b) for a in (s[0], s[-1]) for b in s) if len(s) > 1 else 0
        shut = math.dist(s[0], s[-1])
        if want is None or len(s) < 5 or shut > max(2.0, 0.02 * span):
            out.append(s)                   # open stroke: its ends are real
            continue
        # A ring that touches another stroke is not free: Р's bowl starts
        # where it meets the stem, and rotating it round to the taught
        # zone moved a start that was already right. Only a ring that
        # stands alone has an arbitrary starting point.
        if any(j != i and cells[i] & cells[j] for j in range(len(strokes))):
            out.append(s)
            continue
        ring = s[:-1] if shut < 1 else list(s)
        pts = [p for t in strokes for p in t]
        box = (min(p[0] for p in pts), min(p[1] for p in pts),
               max(p[0] for p in pts), max(p[1] for p in pts))

        def miss(p, name):
            z = ZONES.get(name or "")
            if z is None:
                return 0.0
            c, r = zone_at(p, box)
            return abs(c - z[0]) + abs(r - z[1])

        aim = zone_heading(want.get("from"), want.get("to"))
        best = None
        for back in (False, True):
            loop = list(reversed(ring)) if back else ring
            for k in range(len(loop)):
                # NOT closed back onto loop[k]: rdp() simplifies against
                # the line from the first point to the last, and a path
                # whose ends are the same point has no such line — it
                # collapses to two points and the letter is dropped as
                # inkless. The walk leaves a ring open by one step too.
                cand = loop[k:] + loop[:k]
                cost = miss(cand[0], want.get("from")) + miss(cand[-1], want.get("to"))
                # Zones alone leave a near-closed bowl free to run either
                # way round — ь's bowl scored the same backwards. Half a
                # zone of penalty breaks that tie the taught way without
                # ever outvoting where the stroke starts.
                if aim and not runs_with(cand, aim):
                    cost += 0.5
                if best is None or cost < best[0]:
                    best = (cost, cand)
        out.append(best[1])
    return out


def _taught() -> dict:
    """The strokes each sourced rule gives a letter, keyed by
    (script, style, glyph, form). The tables are written by
    scripts/strokes/ingest_rules.py from teaching sources; a letter with
    no row is absent and is left exactly as the walk drew it."""
    out: dict = {}
    d = ROOT / "scripts" / "strokes" / "rules"
    for f in sorted(d.glob("*.jsonl")) if d.is_dir() else []:
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            out[(r["script"], r["style"], r["glyph"], r["form"])] = r["strokes"]
    return out


TAUGHT_STROKES = _taught()
TAUGHT = {k: len(v) for k, v in TAUGHT_STROKES.items()}


def turn(path: list, i: int, span: int) -> float:
    """How sharply *path* turns at index *i*, as 1 - cos(angle), measured
    over *span* pixels either side so a single jagged pixel cannot pass
    for a corner. 0 is straight on, 1 is a right angle, 2 is a reversal."""
    a, b, c = path[max(0, i - span)], path[i], path[min(len(path) - 1, i + span)]
    u, v = unit(a, b), unit(b, c)
    return 1.0 - (u[0] * v[0] + u[1] * v[1])


def split_to(strokes: list, target: int, span: int, floor: float = 0.30) -> list:
    """Cut strokes at their sharpest turns until there are *target*.

    A print letter is built from separate strokes meeting at corners —
    Cyrillic и is a stem, a diagonal and a stem — but thinning joins them
    into one connected skeleton, so the walk runs straight through and
    draws the whole letter in one movement. Measured against the sourced
    propisi table, the generated library drew FEWER strokes than taught
    for 21 of 32 Cyrillic print letters and more for only two: sixteen of
    ours were a single stroke where the taught model uses five. That is
    not a font's fault — Noto Sans has the right shapes — it is the walk
    not lifting where a hand lifts.

    Where a rule says how many strokes a letter has, the corners are
    where the pen lifts, so the sharpest turn is cut first and the next
    sharpest after it. *floor* stops it short of cutting a smooth curve
    just to reach a number: a letter that runs out of corners keeps the
    strokes it has and shows up in the checker as a disagreement, which
    is the honest outcome. This only ever ADDS strokes, and only for a
    letter with a sourced row."""
    out = [list(s) for s in strokes]
    while len(out) < target:
        best = None
        for i, s in enumerate(out):
            if len(s) < 2 * span + 3:
                continue
            for j in range(span + 1, len(s) - span - 1):
                t = turn(s, j, span)
                if best is None or t > best[0]:
                    best = (t, i, j)
        if best is None or best[0] < floor:
            break
        _, i, j = best
        s = out.pop(i)
        out[i:i] = [s[:j + 1], s[j:]]
    return out


def heading(path: list, at_end: bool, span: int = REACH) -> tuple:
    """Which way the pen is travelling at one end of *path*, measured over
    a run so one pixel's jitter cannot decide it. Both ends point the way
    the path is drawn, so a tail and the head that continues it agree."""
    if len(path) < 2:
        return (0.0, 0.0)
    if at_end:
        return unit(path[max(0, len(path) - 1 - span)], path[-1])
    return unit(path[0], path[min(len(path) - 1, span)])


def runs_on(before: list, after: list, tol: float, far: float) -> bool:
    """Whether *after* carries on from *before*: ends close enough to be
    the same movement, and going the same way.

    Two tolerances, because there are two cases. Ends that all but touch
    (*tol*) are a walk the fork split and need no further argument. A
    wider gap (*far*) is only a continuation if the pen is still heading
    the same way across it — which is what a junction another stroke has
    already been drawn through leaves behind: the pixels just past the
    junction touch that stroke, the walk rejects them as a thinning
    artefact and stops, and the rest of the stem becomes a second stroke.
    The Cyrillic ж lost its stem that way, cut in two at the crossing the
    upper diagonals are drawn through.

    *far* is three times the junction ring, which is what it takes to
    close the widest of these cuts — the crossbar of a cursive H, whose
    halves are walked head-on towards each other from the two stems, so
    one of them has to be reversed before it reads as a continuation and
    the two ends are further apart than the cut itself. Wider than that
    changes nothing, which is the sign it is measuring a real gap and not
    a tuned one."""
    gap = math.hypot(after[0][0] - before[-1][0], after[0][1] - before[-1][1])
    if gap <= tol:
        return True
    if gap > far:
        return False
    a, b = heading(before, True), heading(after, False)
    return a[0] * b[0] + a[1] * b[1] > 0.9


def chain(strokes: list[list], tol: float = 3.5, keep_start: bool = False,
          far: float = 3 * JUNCTION) -> list[list]:
    """Re-join walks that a junction split: a stroke whose start (or end)
    sits on the end of an earlier stroke continues it. The loop-closing
    fragments of cursive letters (the tail of an а, the bowl of в) come back
    into one stroke this way, which is how the hand makes them."""
    out: list[list] = []
    for s in strokes:
        if not out:
            out.append(list(s))
            continue
        placed = False
        rev = list(reversed(s))
        for t in out:
            if runs_on(t, s, tol, far):
                t.extend(s[1:]); placed = True; break
            if runs_on(t, rev, tol, far):
                t.extend(rev[1:]); placed = True; break
            if keep_start and t is out[0]:
                continue
            if runs_on(s, t, tol, far):
                t[:0] = s[:-1]; placed = True; break
            if runs_on(rev, t, tol, far):
                t[:0] = rev[:-1]; placed = True; break
        if not placed:
            out.append(list(s))
    return out


def resample(path, step):
    if len(path) < 2:
        return [list(p) for p in path]
    out = [list(path[0])]
    acc = 0.0
    for a, b in zip(path, path[1:]):
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        acc += d
        if acc >= step:
            out.append([b[0], b[1]])
            acc = 0.0
    if out[-1] != [path[-1][0], path[-1][1]]:
        out.append([path[-1][0], path[-1][1]])
    return out


def smooth(pts, k=2):
    if len(pts) < 5:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        lo, hi = max(0, i - k), min(len(pts), i + k + 1)
        xs = [p[0] for p in pts[lo:hi]]; ys = [p[1] for p in pts[lo:hi]]
        out.append([sum(xs) / len(xs), sum(ys) / len(ys)])
    out.append(pts[-1])
    return out


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    norm = math.hypot(dx, dy) or 1e-9
    dmax, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * (pts[i][0] - a[0]) - dx * (pts[i][1] - a[1])) / norm
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        return rdp(pts[: idx + 1], eps)[:-1] + rdp(pts[idx:], eps)
    return [a, b]


# ----------------------------------------------------------------------
# Ordering rules
# ----------------------------------------------------------------------
def order_strokes(script: str, style: str, comps_strokes: list[tuple[set, list, bool, tuple | None]], bbox, form: str = "isolated") -> tuple[list[list], int]:
    """Bodies before marks; bodies in writing order; each stroke oriented
    the way a hand starts it — except a stroke pinned to start at a Thai
    head. Returns the strokes and how many lead ones are bodies (the rest
    are dots and marks)."""
    x0, y0, x1, y1 = bbox
    area = max(1, (x1 - x0) * (y1 - y0))
    bodies, marks = [], []
    skeleton_px = sum(len(c) for c, _, is_dot, _p in comps_strokes if not is_dot)
    bodies_only = [c for c, _, is_dot, _p in comps_strokes if not is_dot]
    biggest = max([len(c) for c in bodies_only] or [0])
    main = max(bodies_only, key=len) if bodies_only else set()
    main_y = (min(p[1] for p in main), max(p[1] for p in main)) if main else (0, 0)
    for comp, strokes, is_dot, pinned in comps_strokes:
        xs = [p[0] for p in comp]; ys = [p[1] for p in comp]
        cw, ch = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        # A mark is a dot, or a component much smaller than the largest
        # one. The bbox test alone once made a lone thin stem (l, ㅢ, the
        # bars of Ξ) a "mark", leaving a letter with no body at all. In
        # Arabic a piece wholly above or below the main body — the hamza
        # of أ إ, the madda of آ — is a mark too, written after it.
        small = is_dot or len(comp) < 0.04 * skeleton_px or (
            len(comp) < 0.25 * biggest and (cw * ch) < 0.06 * area) or (
            script == "arabic" and comp is not main and (max(ys) < main_y[0] or min(ys) > main_y[1]))
        (marks if small else bodies).append((comp, strokes, min(xs), max(xs), min(ys), pinned))
    rtl = script in RTL
    key = (lambda c: -c[3]) if rtl else (lambda c: c[2])
    bodies.sort(key=key)
    marks.sort(key=key)
    out = []
    for _comp, strokes, *_rest, pinned in bodies:
        for s in strokes:
            # Only the very first body stroke of a medial/final form is
            # entered from the join; the rest start where the pen comes down.
            joined = not out
            out.append(s if pinned is not None and s[0] == pinned else orient(script, style, s, form, joined))
    n_body = len(out)
    for _comp, strokes, *_ in marks:
        for s in strokes:
            out.append(orient(script, style, s, form, False))
    return out, n_body


def rtl_first(a, b, form: str, joined: bool):
    """Which end an Arabic (or Hebrew) stroke starts at.

    A form that is entered from a join (medial, final) starts at the
    join: the rightmost end, at the baseline — so a final alif runs UP
    from ب. Anything else starts where the pen comes down: the TOP end of
    a stroke that is more tall than wide (an isolated alif goes down, the
    upright of ط and ك too), otherwise the rightmost end (the tip of ب,
    the head of ج, the first tooth of س), higher if tied. From the
    Ibnulyemen chart the owner supplied and the Write it in Arabic
    convention: isolated letters start top-right; joins start at the
    join."""
    if joined and form in ("medial", "final"):
        return max((a, b), key=lambda p: (p[0], p[1]))            # rightmost, then LOWER (the baseline join)
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    if dy > dx * 1.2:
        return min((a, b), key=lambda p: (p[1], -p[0]))           # top, then rightmost
    return max((a, b), key=lambda p: (p[0], -p[1]))               # rightmost, then higher


def span(s: list) -> tuple[float, float]:
    xs = [p[0] for p in s]; ys = [p[1] for p in s]
    return max(xs) - min(xs), max(ys) - min(ys)


def flat(s: list) -> bool:
    """A bar: the whole path stays in a thin horizontal band."""
    w, h = span(s)
    return w > 3 * h and w > 0.04 * EM


def upright(s: list) -> bool:
    """A stem: the whole path stays in a thin vertical band."""
    w, h = span(s)
    return h > 3 * w and h > 0.04 * EM


def orient(script: str, style: str, s: list, form: str = "isolated", joined: bool = False) -> list:
    a, b = s[0], s[-1]
    closed = math.hypot(a[0] - b[0], a[1] - b[1]) < 6 and len(s) > 20
    if closed:
        # A loop: start at the top, go leftwards first (anticlockwise on
        # screen — o, ه, the bowls of cursive a/d).
        i = min(range(len(s)), key=lambda k: (s[k][1], s[k][0]))
        s = s[i:] + s[:i]
        if len(s) > 2 and s[1][0] > s[0][0]:
            s = [s[0]] + s[1:][::-1]
        return s
    if script in RTL:
        want_first = rtl_first(a, b, form, joined)
    elif flat(s):
        # A bar is written in the reading direction, always: the crossbar
        # of f t A H, the arms of E Ξ ц ш. The old rule was "topmost end,
        # ties to the left", and on a level bar a pixel of thinning noise
        # decided it — which drew f's crossbar right to left (owner,
        # 18 Sep). Judged on the whole path's box, not its two ends: the
        # legs of A end level too, and that is not a bar.
        want_first = min((a, b), key=lambda p: p[0])
    elif upright(s):
        want_first = min((a, b), key=lambda p: p[1])                # a stem goes down
    elif (script, style) in CURSIVE:
        want_first = min((a, b), key=lambda p: (p[0], p[1]))        # leftmost
    elif abs(a[1] - b[1]) < 0.35 * max(1, span(s)[1]):
        # Both ends at much the same height: the hand starts at the left
        # one. The same tie the bar rule broke, one axis over — it was
        # sending v w x y off their right-hand end (the Zaner-Bloser rules
        # table, 19 Sep, disagreed with all four).
        want_first = min((a, b), key=lambda p: p[0])
    else:
        want_first = min((a, b), key=lambda p: (p[1], p[0]))        # topmost, then leftmost
    return s if want_first == a else s[::-1]


def stroke_hint(script: str, style: str, s: list, kind: str, index: int) -> str:
    """What to say about one stroke. Derived from the stroke itself, not
    from its position in the list: "next stroke" told a learner nothing
    about the crossbar of an f, and a hint that does not match the arrow
    is worse than none."""
    if kind == "mark":
        return "the dots and marks last"
    if kind == "headline":
        return "the headline last, left to right — across the whole word"
    a, b = s[0], s[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    w, h = span(s)
    if math.hypot(dx, dy) < BOX * 0.12 and len(s) > 6 and w > BOX * 0.1:
        return "round, back to where it started"
    if w > 3 * h and w > BOX * 0.1:
        return "across, right to left" if script in RTL else "across, left to right"
    if h > 3 * w and h > BOX * 0.1:
        return "straight down" if dy > 0 else "straight up"
    if index == 0:
        return {"arabic": "from the right, along the body",
                "hebrew": "from the right"}.get(
            script, "from the left, in one flow" if (script, style) in CURSIVE else "from the top")
    return "down and " + ("left" if dx < 0 else "right") if dy > 0 else "up and " + ("left" if dx < 0 else "right")


# ----------------------------------------------------------------------
# One glyph
# ----------------------------------------------------------------------
def extract(font, script, style, glyph, form):
    text = shaped_text(script, glyph, form)
    grid, baseline, ascent, descent = render(font, text)
    ink = [(x, y) for y in range(CANVAS) for x in range(CANVAS) if grid[y][x]]
    if not ink:
        return None
    xs = [p[0] for p in ink]; ys = [p[1] for p in ink]
    bbox = (min(xs), min(ys), max(xs), max(ys))
    # Crop with a margin so thinning has room, then thin.
    x0, y0, x1, y1 = bbox
    m = 3
    sub = [row[x0 - m: x1 + m + 1] for row in grid[y0 - m: y1 + m + 1]]
    # Dots and small marks are found on the INK, before thinning: a dot
    # thins to one or two pixels (or nothing, once spurs are pruned), which
    # is how ب ت ث once came out identical. Each becomes one short tick at
    # its centre, drawn after the bodies.
    # A dot is a small blob that thins to (almost) nothing: a filled disc
    # leaves a point, where a tooth or a hamza the same size leaves a
    # curve. Size alone cannot tell them apart (the dot of ب is bigger
    # than the body of medial ب).
    sk = thin(sub)
    dots = []
    for rc in components(sub):
        xs = [p[0] for p in rc]; ys = [p[1] for p in rc]
        if max(max(xs) - min(xs), max(ys) - min(ys)) + 1 >= EM // 5:
            continue
        if sum(1 for x, y in rc if sk[y][x]) <= EM // 12:
            dots.append(rc)
    for rc in dots:
        for x, y in rc:
            sk[y][x] = 0
    prune_spurs(sk, min_len=max(6, EM // 20))
    minimal(sk)
    comps = components(sk)
    cs = []
    for comp in comps:
        if len(comp) < 3:
            continue
        ends = [p for p in comp if is_tip(sk, comp, p)]
        # Start rule per script (see orient); the walk just needs a start.
        second = None
        head = head_ring(sub, sk, comp) if script == "thai" else None
        loop = None
        if head:
            # Thai: begin at the head, where it meets the body, circle it
            # clockwise (Verbacard: "most consonants begin with a clockwise
            # circular motion"), then carry on into the body.
            ring, (cx, cy) = head
            loop = ring
            ringset = set(ring)
            attached = [p for p in ring if any(q in comp and q not in ringset for q in neighbours(sk, *p))]
            start = attached[0] if attached else min(ring, key=lambda p: (p[1], p[0]))
            around = [q for q in neighbours(sk, *start) if q in ringset]
            if around:
                # Clockwise on screen (y down) is a positive cross product
                # about the hole's centre.
                second = max(around, key=lambda q: (start[0] - cx) * (q[1] - start[1]) - (start[1] - cy) * (q[0] - start[0]))
        elif ends:
            if script in RTL:
                # The walk begins at the join for a joined form, else at the
                # rightmost tip (the bowl of ط before its upright, which then
                # becomes its own top-down stroke); each stroke's direction
                # is settled afterwards by orient().
                if form in ("medial", "final"):
                    start = max(ends, key=lambda p: (p[0], p[1]))
                else:
                    # Not at the top of an upright (ط's stem is written after
                    # its bowl): an endpoint whose branch runs tall to a fork
                    # is left for a later stroke.
                    cand = [e for e in ends if not upright_end(sk, comp, e)] or ends
                    start = max(cand, key=lambda p: (p[0], -p[1]))
            elif (script, style) in CURSIVE:
                start = min(ends, key=lambda p: (p[0], p[1]))
            else:
                start = min(ends, key=lambda p: (p[1], p[0]))
        else:
            start = min(comp, key=lambda p: (p[1], p[0]))
        joined_form = script == "arabic" and form in ("medial", "final")
        strokes = trace_component(sk, comp, start, teeth=script == "arabic",
                                  second=second, loop=set(loop) if loop else None,
                                  joined=joined_form)
        # Arabic's walk settles its own continuity (teeth, retraces,
        # uprights kept apart); chaining would glue the stem of ط back onto
        # its bowl. Elsewhere chain() re-joins what a fork split.
        if script != "arabic":
            strokes = chain(strokes)
        longest = max(strokes, key=path_len)
        strokes = [t for t in strokes if path_len(t) >= EM / 8] or [longest]
        cs.append((comp, strokes, False, start if loop else None))
    for rc in dots:
        cx = sum(p[0] for p in rc) / len(rc)
        cy = sum(p[1] for p in rc) / len(rc)
        r = max(3, EM // 40)
        cs.append((rc, [[(cx - r, cy), (cx + r, cy)]], True, None))
    ordered, n_body = order_strokes(script, style, cs, (0, 0, x1 - x0 + 2 * m, y1 - y0 + 2 * m), form)
    want = TAUGHT.get((script, style, glyph, form))
    if want is not None:
        marks = len(ordered) - n_body
        body = split_to(ordered[:n_body], want - marks, span=max(3, EM // 30))
        body = merge_to(body, want - marks, cap=4 * JUNCTION)
        body = fit_taught(body, TAUGHT_STROKES[(script, style, glyph, form)])
        body = start_ring_where_taught(body, TAUGHT_STROKES[(script, style, glyph, form)])
        ordered, n_body = body + ordered[n_body:], len(body)
    # Pixel -> em box. y: 0 at the top of the em (ascender), 1000 at the
    # bottom (descender) — the same frame for every glyph of the script.
    em_top = baseline - ascent
    scale = BOX / (ascent + descent)
    left = x0 - m
    top = y0 - m

    def to_box(p):
        return [(p[0] + left - (x0)) * scale, (p[1] + top - em_top) * scale]

    out = []
    body_count = 0
    for k, s in enumerate(ordered):
        pts = resample(s, step=max(2, EM / 60))
        pts = smooth(pts)
        pts = rdp(pts, eps=EM / 150)
        pts = [to_box(p) for p in pts]
        pts = [[int(round(min(BOX, max(0, x)))), int(round(min(BOX, max(0, y))))] for x, y in pts]
        dedup = [pts[0]]
        for p in pts[1:]:
            if p != dedup[-1]:
                dedup.append(p)
        if len(dedup) >= 2:
            out.append(dedup)
            if k < n_body:
                body_count += 1
    if not out:
        return None
    kinds = ["body"] * body_count + ["mark"] * (len(out) - body_count)
    if script == "devanagari":
        out, kinds = headline_last(out, kinds)
        body_count = kinds.count("body")
    allpts = [p for s in out for p in s]
    advance = max(p[0] for p in allpts)
    # `marks` is how many trailing strokes are dots and marks: a composed
    # word writes every letter's bodies first and comes back for these.
    joins = {"advance": advance, "marks": len(out) - body_count}
    # Joins come from the bodies only: a dot under the first tooth of ب
    # must not become its exit.
    bodypts = [p for s in out[:body_count] for p in s] or allpts
    body = [p for s in out[:1] for p in s] or allpts
    if script == "arabic":
        joins["joins_next"] = form in ("initial", "medial")
        if form in ("initial", "medial"):
            joins["exit"] = min(bodypts, key=lambda p: (p[0], -p[1]))
        if form in ("medial", "final"):
            joins["entry"] = max(bodypts, key=lambda p: (p[0], -p[1]))
    elif (script, style) in CURSIVE:
        joins["joins_next"] = True
        joins["entry"] = min(body, key=lambda p: (p[0], p[1]))
        joins["exit"] = max(bodypts, key=lambda p: (p[0], p[1]))
    hints = [stroke_hint(script, style, out[i], kinds[i], i) for i in range(len(out))]
    return {"script": script, "glyph": glyph, "form": form, "style": style,
            "strokes": out, "joins": joins, "hints": hints,
            "source": "provisional", "reviewed": True}


# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--only", default=None, help="one script")
    ap.add_argument("--limit", type=int, default=0, help="glyphs per script (debug)")
    ap.add_argument("--migration", default="20261026000000_provisional_strokes_marks.sql",
                    help="file under supabase/migrations to write; a NEW name each time one is pushed")
    args = ap.parse_args()
    fdir = Path(args.fonts)
    all_glyphs: dict[str, list] = {}
    for script, styles in FONTS.items():
        if args.only and script != args.only:
            continue
        letters = []
        seen = set()
        for code in COURSES[script]:
            for row in alphabet_for(code):
                if row["glyph"] not in seen:
                    seen.add(row["glyph"])
                    letters.append(row["glyph"])
        if args.limit:
            letters = letters[: args.limit]
        for style, fname in styles.items():
            if style not in STYLES.get(script, ["print"]):
                continue
            chain = [fname] if isinstance(fname, str) else list(fname)
            fonts = [(f, ImageFont.truetype(str(fdir / f), EM), covered(fdir / f))
                     for f in chain]
            for glyph in letters:
                for form in forms_for(script, glyph):
                    text = shaped_text(script, glyph, form)
                    need = [c for c in text if c != ZWJ]
                    pick = next((t for t in fonts
                                 if all(ord(c) in t[2] for c in need)), None)
                    if pick is None:
                        absent = "".join(c for c in need
                                         if not any(ord(c) in t[2] for t in fonts))
                        print("  skip %s %s: no face has %s"
                              % (glyph, form, absent), file=sys.stderr)
                        continue
                    if pick[0] != chain[0]:
                        print("  %s %s from %s (%s has it not)"
                              % (glyph, form, pick[0], chain[0]), file=sys.stderr)
                    g = extract(pick[1], script, style, glyph, form)
                    if g:
                        all_glyphs.setdefault(script, []).append(g)
                    else:
                        print(f"  no ink: {script} {glyph} {form} {style}", file=sys.stderr)
            print(f"{script}/{style}: {sum(1 for g in all_glyphs.get(script, []) if g['style']==style)} forms")
    (ROOT / "data" / "strokes").mkdir(parents=True, exist_ok=True)
    fe = ROOT / "frontend" / "src" / "features" / "write" / "strokes"
    fe.mkdir(parents=True, exist_ok=True)
    rows = []
    for script, glyphs in all_glyphs.items():
        doc = {"script": script, "glyphs": glyphs, "exemplars": []}
        text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
        (ROOT / "data" / "strokes" / f"{script}.json").write_text(text + "\n", encoding="utf-8")
        (fe / f"{script}.json").write_text(text + "\n", encoding="utf-8")
        for g in glyphs:
            def q(v):
                return "'" + json.dumps(v, ensure_ascii=False, separators=(",", ":")).replace("'", "''") + "'"
            rows.append(f"  ('{script}', '{g['glyph']}', '{g['form']}', '{g['style']}', {q(g['strokes'])}::jsonb, "
                        f"{q(g['joins'])}::jsonb, {q(g['hints'])}::jsonb, 'provisional', true)")
    # --limit renders a debug subset of each alphabet, so its rows would upsert
    # a partial library over a whole one. --only is a whole script and its rows
    # upsert only that script, so it writes a migration like any other run.
    if not args.limit:
        sql = ["-- PROVISIONAL stroke library, derived from fonts (scripts/strokes/gen_from_fonts.py).",
               "-- Shapes are the typefaces' (Noto Naskh Arabic, Marck Script, Noto Sans, Dancing",
               "-- Script — all OFL); order and direction are heuristic and marked provisional.",
               "-- Coordinates are the em box, baseline shared per script, with entry/exit joins.",
               "-- Replaces earlier provisional rows ONLY where nobody has traced over them:",
               "-- the UPDATE is guarded on source = 'provisional'.",
               "",
               "INSERT INTO script_glyphs (script, glyph, form, style, strokes, joins, hints, source, reviewed) VALUES",
               ",\n".join(rows),
               "ON CONFLICT (script, glyph, form, style) DO UPDATE SET",
               "  strokes = EXCLUDED.strokes, joins = EXCLUDED.joins, hints = EXCLUDED.hints",
               "  WHERE script_glyphs.source = 'provisional';"]
        (ROOT / "supabase" / "migrations" / args.migration).write_text(
            "\n".join(sql) + "\n", encoding="utf-8")
    print("total", sum(len(v) for v in all_glyphs.values()))


if __name__ == "__main__":
    main()
