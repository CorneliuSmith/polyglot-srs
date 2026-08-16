# Contrast and hierarchy — why the app read as washed out

Owner feedback: *"the colour is too sparse… the eye is not drawn to the
questions and everything else."*

That turned out to be measurable rather than a matter of taste.

---

## What was actually wrong

Tailwind's grey scale on this app's backgrounds (white cards on `gray-50`):

| Class | Hex | On white | On `gray-50` | Verdict |
| --- | --- | --- | --- | --- |
| `text-gray-300` | `#d1d5db` | 1.47:1 | 1.41:1 | fails even the 3:1 UI floor |
| `text-gray-400` | `#9ca3af` | **2.54:1** | 2.43:1 | **fails even the 3:1 UI floor** |
| `text-gray-500` | `#6b7280` | 4.83:1 | 4.63:1 | passes AA |
| `text-gray-600` | `#4b5563` | 7.56:1 | 7.23:1 | passes |
| `text-gray-700` | `#374151` | 10.31:1 | 9.86:1 | passes |
| `text-gray-900` | `#111827` | 17.74:1 | 16.98:1 | passes |

WCAG AA asks 4.5:1 for body text and 3:1 for non-text UI. **`text-gray-400`
was used 266 times** and sits at 2.54:1 — below even the weaker bar, for
icons let alone words.

That is the whole complaint, mechanically. When a third of the text on a
screen is close to invisible, there is no hierarchy to perceive: the eye
isn't drawn *away* from anything, because the supporting text never
registered in the first place. "Sparse" is what a page looks like when its
second tier has been bleached out.

## Dark mode, checked too

`.dark` remaps the whole grey ramp (`index.css`), so the same utility class
resolves to a different colour there — a sweep in one theme silently moves
the other. Measured against the dark card surface `#1a2130`:

| Class | Hex under `.dark` | On card | Verdict |
| --- | --- | --- | --- |
| `text-gray-300` | `#46526b` | 2.05:1 | fails — disabled controls only |
| `text-gray-400` | `#7f8ba3` | 4.70:1 | passes, barely |
| `text-gray-500` | `#97a3ba` | 6.34:1 | passes comfortably |
| `text-gray-700` | `#cbd4e4` | 10.79:1 | passes |
| `text-gray-900` | `#eef2f9` | 14.34:1 | passes |

The dark ramp was already sound — it is the light one that was broken. The
`400 → 500` sweep moved dark mode from 4.70:1 to 6.34:1 as well, so both
themes improved and neither regressed. Worth re-measuring both any time a
grey moves, because one class means two colours here.

## The change

Every `text-gray-400` became `text-gray-500` — **2.54:1 → 4.83:1**, across
80 component files. No layout, spacing or type-scale changes; the same
design, made legible.

`text-gray-300` (17 uses) was left alone: it marks disabled controls, and
WCAG explicitly exempts disabled elements from the contrast minimum.

## Bringing the language colour in

Contrast alone left the app legible but grey. Every course already has a
palette (`lib/languageColors.ts`) and it was reaching almost nothing — a
border on the picker, a couple of icons.

The reason it could not be used more widely is that `--lang-primary` is a
raw brand hue ranging from Catalan's `#FCDD09` yellow to English navy
`#012169`. As TEXT that is unusable at one end and fine at the other, so it
stayed a fill. Mixing solves it, and the mix direction is the whole rule:

| Token | Mix | Role |
| --- | --- | --- |
| `--lang-tint` | 4% hue + white | card and rail surfaces |
| `--lang-edge` | 22% hue + `#e5e7eb` | borders on those surfaces |
| `--lang-label` | 38% hue + **ink** | eyebrow labels, section headings |

**Colour toward the ground for surfaces; colour toward the ink for type.**
Mixing a label 62% into `#111827` drags every hue into a legible range
while keeping it recognisably that language's colour. Measured across the
palette, label on tint:

| Language | Label | Ratio |
| --- | --- | --- |
| Catalan (yellow) | `#6a631c` | 6.08:1 |
| Xhosa (amber) | `#6b541f` | 7.04:1 |
| Hindi (orange) | `#6b492c` | 7.80:1 |
| Swahili (cyan) | `#0b4d6c` | 8.77:1 |
| Italian (green) | `#0b4432` | 10.55:1 |
| Spanish (red) | `#4c1722` | 13.53:1 |
| English (navy) | `#0b1b40` | 15.61:1 |

Worst case 6.08:1 against a 4.5:1 requirement — so the colour goes up and
the legibility goes up together, which is the point. Dark mode re-mixes the
same three tokens toward its own ground and near-white ink.

## Rules to hold to from here

1. **Never put text below `gray-500`** unless it is a disabled control.
   Anything a learner is meant to read starts at 4.83:1.
2. **Three tiers, not five.** `gray-900` for the thing being asked,
   `gray-700` for what supports it, `gray-500` for metadata. If a screen
   needs a fourth level of grey, it is doing too much.
3. **The accent means "this is the point".** `--lang-primary` (`#4f46e5`)
   is 6.29:1 on white and safe for text — use it on the one element the eye
   should land on first, and nowhere else on that screen.
4. **`--lang-accent` (`#818cf8`) is 2.98:1 — never for text.** Fills,
   borders and bars only.
5. **Contrast before colour.** Adding more hues to a low-contrast screen
   makes it busier, not clearer. Fix the tonal range first; reach for a
   second colour only when the first tier still isn't landing.

## Sources

- WCAG AA: 4.5:1 for normal body text, 3:1 for large text and non-text UI.
- 2026 practice: limit to 2–3 primaries plus 2 accents, and reserve the most
  vibrant accent for primary actions only.
- Contrast is the mechanism behind hierarchy, emphasis and legibility — the
  visual system responds to difference, so high contrast is what pulls the
  eye.
