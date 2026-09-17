# ruff: noqa: E741
"""Derive the PROVISIONAL stroke library from real fonts.

The first library (gen_provisional.py) drew letters from primitives, and
the owner's verdict was the right one: "not reflective of much of the
writing I see". A typeface is what people see. So each form is now
rendered with a standard face — Noto Naskh Arabic for naskh, Marck
Script for Russian cursive (propisi), Noto Sans for print scripts,
Dancing Script for Latin cursive — thinned to its centreline, traced
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
supabase/migrations/20261025000000_provisional_strokes_from_fonts.sql,
which UPDATEs only rows still `source = 'provisional'` so a speaker's
tracing is never overwritten.
"""
from __future__ import annotations

import argparse
import json
import math
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
_scripts = _load_assignments(ROOT / "backend" / "services" / "scripts.py", {"STYLES"})
STYLES = _scripts["STYLES"]
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
        return ["lower", "upper"]
    return ["letter"]


def alphabet_for(code: str) -> list[dict]:
    rows = ALPHABETS.get(code, [])
    if not rows:
        rows = [(ch, ch, "") for ch in LATIN_BASE]
    return [{"glyph": g} for g, *_ in rows]

BOX = 1000
EM = 300            # px per em when rendering
CANVAS = 4 * EM     # px
ZWJ = "‍"

# script -> style -> (font file, per-script rules)
FONTS = {
    "arabic":     {"naskh": "NotoNaskhArabic.ttf"},
    "cyrillic":   {"cursive": "MarckScript-Regular.ttf", "print": "NotoSans.ttf"},
    "greek":      {"print": "NotoSans.ttf"},
    "hebrew":     {"print": "NotoSansHebrew.ttf"},
    "devanagari": {"print": "NotoSansDevanagari.ttf"},
    "thai":       {"print": "NotoSansThai.ttf"},
    "hangul":     {"print": "NotoSansKR.ttf"},
    "latin":      {"print": "NotoSans.ttf", "cursive": "DancingScript.ttf"},
}
RTL = {"arabic", "hebrew"}
CURSIVE = {("cyrillic", "cursive"), ("latin", "cursive")}
# One course per script is enough to enumerate the alphabet; Persian adds
# four letters to the Arabic set, so arabic takes both.
COURSES = {
    "arabic": ["ar", "fa"], "cyrillic": ["ru"], "greek": ["el"], "hebrew": ["he"],
    "devanagari": ["hi"], "thai": ["th"], "hangul": ["ko"], "latin": ["es"],
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


def trace_component(g, comp: set, start: tuple) -> list[list[tuple]]:
    """Walk the component into strokes: from *start*, always take the
    straightest unvisited continuation at a junction; a new stroke begins
    at the next unvisited endpoint (or the topmost unvisited pixel)."""
    visited = set()
    strokes = []

    def degree(p):
        return len([q for q in neighbours(g, *p) if q in comp])

    def walk(p):
        path = [p]
        visited.add(p)
        prev = None
        while True:
            nb = [q for q in neighbours(g, *p) if q in comp and q not in visited]
            if not nb:
                break
            if prev is None or len(nb) == 1:
                q = nb[0]
            else:
                # straightest continuation
                dx, dy = p[0] - prev[0], p[1] - prev[1]
                q = max(nb, key=lambda r: (r[0] - p[0]) * dx + (r[1] - p[1]) * dy)
            visited.add(q)
            path.append(q)
            prev, p = p, q
        return path

    strokes.append(walk(start))
    while True:
        left = [p for p in comp if p not in visited]
        if not left:
            break
        ends = [p for p in left if degree(p) == 1]
        # Prefer an endpoint adjacent to what is already drawn (continuing
        # the letter), else the topmost.
        cand = ends or left
        nxt = min(cand, key=lambda p: (p[1], p[0]))
        s = walk(nxt)
        if len(s) >= 3:
            strokes.append(s)
        # Tiny leftovers (junction fragments) are absorbed silently.
        for p in s:
            visited.add(p)
    return strokes


def path_len(path) -> float:
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:]))


def chain(strokes: list[list], tol: float = 3.5) -> list[list]:
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
        for t in out:
            e = t[-1]
            if math.hypot(s[0][0] - e[0], s[0][1] - e[1]) <= tol:
                t.extend(s[1:]); placed = True; break
            if math.hypot(s[-1][0] - e[0], s[-1][1] - e[1]) <= tol:
                t.extend(list(reversed(s))[1:]); placed = True; break
            b = t[0]
            if math.hypot(s[-1][0] - b[0], s[-1][1] - b[1]) <= tol:
                t[:0] = s[:-1]; placed = True; break
            if math.hypot(s[0][0] - b[0], s[0][1] - b[1]) <= tol:
                t[:0] = list(reversed(s))[:-1]; placed = True; break
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
def order_strokes(script: str, style: str, comps_strokes: list[tuple[set, list, bool]], bbox) -> tuple[list[list], int]:
    """Bodies before marks; bodies in writing order; each stroke oriented
    the way a hand starts it. Returns the strokes and how many lead ones
    are bodies (the rest are dots and marks)."""
    x0, y0, x1, y1 = bbox
    area = max(1, (x1 - x0) * (y1 - y0))
    bodies, marks = [], []
    skeleton_px = sum(len(c) for c, _, is_dot in comps_strokes if not is_dot)
    for comp, strokes, is_dot in comps_strokes:
        xs = [p[0] for p in comp]; ys = [p[1] for p in comp]
        cw, ch = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        small = is_dot or (cw * ch) < 0.06 * area or len(comp) < 0.04 * skeleton_px
        (marks if small else bodies).append((comp, strokes, min(xs), max(xs), min(ys)))
    rtl = script in RTL
    key = (lambda c: -c[3]) if rtl else (lambda c: c[2])
    bodies.sort(key=key)
    marks.sort(key=key)
    out = []
    for _comp, strokes, *_ in bodies:
        for s in strokes:
            out.append(orient(script, style, s))
    n_body = len(out)
    for _comp, strokes, *_ in marks:
        for s in strokes:
            out.append(orient(script, style, s))
    return out, n_body


def orient(script: str, style: str, s: list) -> list:
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
        want_first = max((a, b), key=lambda p: (p[0], -p[1]))       # rightmost, then higher
    elif (script, style) in CURSIVE:
        want_first = min((a, b), key=lambda p: (p[0], p[1]))        # leftmost
    else:
        want_first = min((a, b), key=lambda p: (p[1], p[0]))        # topmost, then leftmost
    return s if want_first == a else s[::-1]


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
    prune_spurs(sk, min_len=max(6, EM // 14))
    comps = components(sk)
    cs = []
    for comp in comps:
        if len(comp) < 3:
            continue
        ends = [p for p in comp if len([q for q in neighbours(sk, *p) if q in comp]) == 1]
        # Start rule per script (see orient); the walk just needs a start.
        if ends:
            if script in RTL:
                start = max(ends, key=lambda p: (p[0], -p[1]))
            elif (script, style) in CURSIVE:
                start = min(ends, key=lambda p: (p[0], p[1]))
            else:
                start = min(ends, key=lambda p: (p[1], p[0]))
        else:
            start = min(comp, key=lambda p: (p[1], p[0]))
        strokes = trace_component(sk, comp, start)
        strokes = chain(strokes)
        longest = max(strokes, key=path_len)
        strokes = [t for t in strokes if path_len(t) >= EM / 8] or [longest]
        cs.append((comp, strokes, False))
    for rc in dots:
        cx = sum(p[0] for p in rc) / len(rc)
        cy = sum(p[1] for p in rc) / len(rc)
        r = max(3, EM // 40)
        cs.append((rc, [[(cx - r, cy), (cx + r, cy)]], True))
    ordered, n_body = order_strokes(script, style, cs, (0, 0, x1 - x0 + 2 * m, y1 - y0 + 2 * m))
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
    allpts = [p for s in out for p in s]
    advance = max(p[0] for p in allpts)
    joins = {"advance": advance}
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
    hints = []
    n = len(out)
    for i in range(n):
        if i == 0:
            hints.append({"arabic": "from the right, along the body",
                          "hebrew": "from the right"}.get(script,
                         "from the left, in one flow" if (script, style) in CURSIVE else "from the top"))
        elif i >= body_count:
            hints.append("the dots and marks last")
        else:
            hints.append("next stroke")
    return {"script": script, "glyph": glyph, "form": form, "style": style,
            "strokes": out, "joins": joins, "hints": hints,
            "source": "provisional", "reviewed": True}


# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--only", default=None, help="one script")
    ap.add_argument("--limit", type=int, default=0, help="glyphs per script (debug)")
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
            font = ImageFont.truetype(str(fdir / fname), EM)
            for glyph in letters:
                for form in forms_for(script, glyph):
                    g = extract(font, script, style, glyph, form)
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
    if not args.only and not args.limit:
        sql = ["-- PROVISIONAL stroke library, derived from fonts (scripts/strokes/gen_from_fonts.py).",
               "-- Shapes are the typefaces' (Noto Naskh Arabic, Marck Script, Noto Sans, Dancing",
               "-- Script — all OFL); order and direction are heuristic and marked provisional.",
               "-- Coordinates are the em box, baseline shared per script, with entry/exit joins.",
               "-- Replaces the primitive-drawn rows of 20261023 ONLY where nobody has traced over",
               "-- them: the UPDATE is guarded on source = 'provisional'.",
               "",
               "INSERT INTO script_glyphs (script, glyph, form, style, strokes, joins, hints, source, reviewed) VALUES",
               ",\n".join(rows),
               "ON CONFLICT (script, glyph, form, style) DO UPDATE SET",
               "  strokes = EXCLUDED.strokes, joins = EXCLUDED.joins, hints = EXCLUDED.hints",
               "  WHERE script_glyphs.source = 'provisional';"]
        (ROOT / "supabase" / "migrations" / "20261025000000_provisional_strokes_from_fonts.sql").write_text(
            "\n".join(sql) + "\n", encoding="utf-8")
    print("total", sum(len(v) for v in all_glyphs.values()))


if __name__ == "__main__":
    main()
