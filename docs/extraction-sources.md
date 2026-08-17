# Extraction sources — the owner's library, mapped for in-session extraction

Companion to `docs/resource-library.md` (the calibration index) and
`docs/plans/quality-parity.md`. This file is the working map for the
extraction lane: which file, which language, what may be taken from it.

**Policy (owner decision, 2026-08-17): facts ship, sentences are
regenerated.** From any commercial source below: vocabulary, grammar
structure, paradigms, teaching sequence, and pitfalls may be extracted and
shipped. Verbatim course sentences, dialogues, and drill sentences may NOT
ship — every example/drill sentence is freshly written in-session and
verified by a separate checker pass. Extraction runs in the local Claude
Code session only — never the API (`extra_agent`'s offline schema
validation and emit-merge are used; its API extractor is not).

## Primary per-language assignments (owner-stated, 2026-08-17)

All under `~/Library/CloudStorage/Dropbox/Online Learning/Audible/` unless
noted. The bk_inno files are Innovative Language course books.

| File | Language | Status |
|---|---|---|
| `bk_inno_002213.pdf` | fr | pending |
| `bk_inno_002214.pdf` | es | pending |
| `bk_inno_002216.pdf` | ko | pending |
| `bk_inno_002218.pdf` | de | pending |
| `bk_inno_002219.pdf` | it | pending |
| `bk_inno_002220.pdf` | ru | pending |
| `bk_inno_002224.pdf` | **pt** (owner-stated; a copy sits in `~/Documents/Languages/he/` — confirm content language on first open) | pending |
| `bk_inno_002228.pdf` | el | pending |
| `bk_inno_002229.pdf` | hi | pending |
| `bk_inno_002233.pdf` | tr | pending |
| `bk_inno_002244.pdf` | fa | pending |
| `bk_inno_002245.pdf` | ro | pending |
| `bk_inno_002246.pdf` | sw | **done** — extracted + emitted 2026-07-31 (sentences to be regenerated per policy) |
| `Arabic Made easy - 100 Verbs in Context_Part1.pdf` | ar | pending |
| `Learn Arabic.pdf` | ar | pending |

Rule of thumb for the bk_inno numbers: they do NOT match the folder names
under `~/Documents/Languages/` in at least one case (002224). Trust this
table, and confirm the language from page 1 before extracting.

## Other applicable sources (inventoried 2026-08-17)

| Language | Source | Notes |
|---|---|---|
| ko | `Online Learning/HowtoStudyKorean/` — Unit 1–6 PDFs + 15 worksheets; `~/Documents/Languages/` Units 2–6, Korean Grammar for Beginners | Unit 1 partially extracted (12 of 20 chunks). Units 2–6 = the ko depth path |
| ru | `Online Learning/Red Kalinka/` (159 PDFs + 11 EPUB); BeFluentClass 14 PDFs (verb/prefix lists); `~/Documents/Languages/ru/` (100 PDFs) | ~2,518 vocab entries already extracted and validated in extra-agent `out/Russian.parts` — emit is Phase 5's first move |
| ar | `Online Learning/Arab Academy/` — 10 PDFs + **53 TSVs** + Anki exports | The TSVs are structured data — highest fact-per-page in the library |
| fr | `Online Learning/French Podcasts/` LFBP1–215 PDFs | LFBP1 extracted (vocab/sentences shipped; grammar reverted — fr grammar is contributor-only) |
| pt | `Online Learning/Portuguese Podcasts/LearningGuides/` — 573 PDFs | Largest pool; Brazilian Portuguese, matches the pt register decision |
| de | `Online Learning/Udemy/German/` 9 PDFs | `German Podcasts/pdf/` contains French LFBP duplicates, not German — do not use |
| es | SpanishDict 11 PDFs (both locations) | Reference sheets |
| ha | `Online Learning/Hausa/` — Kraft & Kirk-Greene *Teach Yourself Hausa* (~380pp), ED252096 | THE Hausa reference; already partially mined for §3b |
| he | `Online Learning/Udemy/Hebrew/` 3 PDFs | he has no sentence bank at all — priority |
| fa | `Online Learning/Udemy/Persian/` 4 PDFs + `bk_inno_002244` | fa has no sentence bank at all — priority |
| en | `~/Documents/Languages/en/` — english-an-essential-grammar, bk_inno_002223, MUCLecture (extracted, unemitted) | en grammar is contributor-only; vocabulary/structure only |
| ca | `~/Documents/Languages/ca/` — catalan-comprehensive-grammar, catalan-colloquial | |
| el / hi / tr / ro | `~/Documents/Languages/<code>/` bk_inno copies | Cross-check numbers against the table above |
| mi | Māori Made Easy — audio/video only | **No machine-readable text exists** — mi content stays hand-curated |
| la / id / tl / jam / yo / xh / th / nl | — | No library sources; Tatoeba/kaikki + in-session authoring only |

## Not app languages (do not extract)

Mandarin (Melnyks 1,092, PAVC, Practical Chinese Reader), Japanese (JPLT,
Glossika), Thai *Read Thai in 10 Days* (audio only). Future-expansion
signals only.
