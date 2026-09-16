# Arabic: keeping it MSA, and a local model for it (16 Sep 2026)

The owner's ask: *a next step that is looking necessary for Arabic — local
LLM versions built on generic models to support MSA, how to integrate one
once the dialect-control review is done, and whether some other AI would be
better than Claude for MSA, because "I know I have prompted for MSA — maybe
I missed a spot."*

Short answers first, then the detail.

1. **You did miss spots — most of them.** "Modern Standard Arabic" reaches
   the model through one sentence in `tutor_skills/ar/SKILL.md`, and that
   file is loaded by **8 of the 35 model calls** in `backend/services`. The
   other 27 say only "Arabic" (the `languages.name` value) or name no
   variety at all. The worst is **Speak**: "You are a
   friendly Arabic conversation partner … Reply ONLY in Arabic" is, to any
   model, an invitation to Egyptian or Levantine, because that is what
   friendly spoken Arabic *is*. The sentence **harvester's checker** and the
   **sentence/drill reviewers** are unpinned too — which is why the three
   register defects in `docs/quality/ar.md` (بكرة, وانتا, يلا) got through:
   the gate they passed does not know MSA is the standard. §1 lists every
   site with the fix. It is a one-day change and it comes **before** any
   local model, because a model switch cannot fix a prompt that never asked.
2. **No, another frontier model is not the answer to MSA leakage.** Claude,
   GPT-5.x and Gemini 3 all write MSA fluently when asked and all drift when
   the prompt says "Arabic" and "friendly". The Arabic-native open models
   (Jais 2, Falcon-H1-Arabic, Fanar 2, ALLaM) lead the *Arabic-native*
   leaderboards on Arabic knowledge and culture, but the tasks this app
   pays for — explaining Arabic grammar to an English speaker, grading
   under a long rubric, emitting a JSON schema, reading handwriting — are
   where frontier models still win. §2 has the evidence and the one place a
   different model genuinely helps: as a cheap **second judge of register**.
3. **A local MSA model is worth building, in this order:** fix the prompts →
   an eval harness that measures dialect leakage (we already own the
   instruments) → the OpenAI-compatible endpoint plumbing the roadmap
   already planned (ROADMAP (b)) → shadow-run an Arabic-native 7–8B model
   on Speak → a LoRA adapter trained on the app's own curated MSA corpus
   with an explicit `<msa>` register tag → switch per task only when the
   eval says so. §3–§6.

Nothing in this document was measured by running a model. Leaderboard
figures are the sources' own, cited, and move month to month; the eval in
§4 is how to get numbers that are ours.

---

## 1. The audit: where MSA is pinned, and where it is not

**How the pin works today.** `backend/services/tutor_skills/ar/SKILL.md`
opens with `Language: Modern Standard Arabic.` and ends with a register
sentence ("distinguish MSA from dialect … tell the learner when MSA would
sound stilted"). `ERRORS.md` adds "Dialect bleed" as a learner error to
coach. `quality_rules.language_brief(code)` appends SKILL.md to a prompt.
`docs/quality/ar.md` says MSA is the authoritative variety and dialect is
out of scope everywhere but a labelled `culture_note`. The content audit
(`quality/audit_content.py`, check `ar_register`) greps the corpus for 18
dialect markers. The grader (`nlp/arabic.py`) analyses against
calima-msa, so a colloquial form usually has no analysis. That is the
whole of the dialect control, and it is good — where it is applied.

**Where it is applied** (loads SKILL.md or calls `language_brief`):

| Site | How |
|---|---|
| `tutor.py` chat (both constructions, 917 and 1008) | `_load_skill` at 510 → `build_system_blocks` |
| `generate.py:178` drill maker | `language_brief` |
| `generate.py:370` sentence maker | `language_brief` |
| `seeder/generate_curriculum.py:131` | `_load_skill` |
| `seeder/generate_grammar.py:97` | `_load_skill` |
| `semantic_check.py:63` grammar review | `_load_skill` |
| `semantic_check.py:107` vocab review | `_load_skill` |

**Where it is not** — the other 27 `messages.create` calls. The language is
named by `languages.name`, which the seed sets to plain `'Arabic'`
(`20260312000002_seed_languages.sql:7`); `translate.py` alone has seven
calls (locale translations of cards, sentences, texts and trivia) and none
carries a register.

| Site | What the prompt says | Risk | Fix |
|---|---|---|---|
| `speak.py:276` conversation partner | "friendly Arabic conversation partner … Reply ONLY in Arabic … spoken-style chat" | **High.** The single most dialect-inviting prompt in the app. "Spoken-style" Arabic *is* dialect to a model. | Register line (below); and a per-course note that the *learner* may write dialect and must be answered in MSA with the MSA form named in the notes list. |
| `speak.py:506` end-of-session breakdown | "a Arabic conversation practice app" | Medium — it grades what the partner said. | Register line. |
| `speak.py:596` opener / third call | "Arabic" | Medium. | Register line. |
| `seeder/harvest_sentences.py:83` harvest checker | "natural, grammatical Arabic" | **High** — this is the gate the corpus defects passed. "Natural Arabic" accepts بكرة. | Add rule 6: "It is Modern Standard Arabic — no Egyptian, Levantine, Gulf, Iraqi or Maghrebi forms." |
| `generate.py:611` sentence reviewer | "strict reviewer of Arabic example sentences" | **High** — the checker of the pinned maker is itself unpinned, so it cannot reject a dialect sentence for register. | `language_brief` (as the makers) or the register line. |
| `generate.py:743` drill reviewer | same | High, same. | Same. |
| `generate.py:913` morphology tables | "expert in Arabic morphology" | Low — inflection is MSA by nature; dialect paradigms are a real risk only for weak forms. | Register line. |
| `generate.py:1103` syllabus audit | "audit the Arabic grammar syllabus" | Low. | Register line. |
| `reader.py:471/531/621` Reader texts | "Arabic" + a register ladder (native/academic/literary/professional) that is about *level*, not *variety* | Medium — prose defaults to MSA, dialogue inside prose does not. | Register line, and "dialogue in MSA too". |
| `write_assess.py:158` handwriting reader | "careful native reader of handwritten Arabic" | Low for the transcription; medium for `letterform_notes` and `word_diffs` where a dialect spelling may be called correct. | Register line ("expected text is MSA; a dialect spelling is a difference, not an alternative"). |
| `writing_baseline.py:96` placement judge | "Arabic … register control" | Medium — it scores register *control*, without saying which register is the target. | Register line. |
| `define.py:139/175`, `translate.py` (7 calls: card, sentence, text, trivia translators and their checkers), `seeder/translate_english.py`, `seeder/review_hints.py` | Arabic as the **support locale** (glosses and translations *into* Arabic for Arabic-speaking learners of other languages) | Medium — a UI in Egyptian would look wrong to a Saudi and vice versa; MSA is the only neutral choice. | Register line keyed on the *locale*, not only the course. |
| `topic_estimate.py:118`, `level_estimate.py`, `recommend.py:275`, `digest.py`, `tutor.py:1215` summary, `tutor_skill_digest.py` | classification, media picks, summaries | Low — outputs are labels or English; media recommendations in dialect (films, music) are *correct*. | Leave `recommend` alone; register line elsewhere is harmless. |

**The one-module fix.** Add to `quality_rules.py`:

```python
REGISTER = {
    "ar": ("Use Modern Standard Arabic (الفصحى) throughout — the register of "
           "news and textbooks. No Egyptian, Levantine, Gulf, Iraqi or Maghrebi "
           "forms in anything you write, grade or accept. If the learner writes "
           "a dialect form, treat it as a register difference: answer in MSA and "
           "name the MSA form. Dialect is welcome only inside an explicitly "
           "labelled note."),
    "fa": ..., "hi": ("Modern Standard Hindi …"),  # the same shape where a course has a standard
}
def register_line(code: str | None) -> str: ...
```

and append `register_line(code)` in every system prompt above
(twenty-seven one-line edits), plus `register_line(locale)` where Arabic is the
*support* language. Then a test: every `messages.create` call site's
system prompt, rendered for `ar`, contains "Modern Standard Arabic" — the
same shape as the existing "language brief is capped at 2,500 characters"
test, so a future call site cannot ship unpinned. Estimated one day,
including running the sentence and drill checkers once more over the
Arabic corpus with the pinned prompt to catch what the unpinned gate let
through (the three known defects, and whatever else).

**About the dialect-control review in progress.** The marker list
(`ARABIC_DIALECT_MARKERS`, 18 whole-word markers) is a *tripwire*, not a
detector: it catches the commonest function words and nothing else. Two
better instruments already exist in the repo and should join the audit
when the review lands: the calima-msa analyser's **out-of-vocabulary
rate** per sentence (a dialect sentence has several unanalysable tokens; an
MSA one has almost none), and the pinned **checker** above run as a
register judge. §4 turns these into the eval.

---

## 2. Would a different AI be better than Claude for MSA?

**For the leakage problem — no.** The published comparisons agree that
Claude, GPT and Gemini all handle MSA well and differ mainly in *dialect*
work (a comparison of Arabic content quality gives Claude a slight edge in
Egyptian and Gulf; a 2026 translation benchmark scores Claude and GPT-4o
within half a point). Leakage into dialect is a prompting failure in this
codebase (§1), not a model ceiling. Switching vendor would carry the same
unpinned prompts to a model that drifts the same way.

**For Arabic-native knowledge — yes, the Gulf models lead their own
leaderboards.** The Arabic-native benchmarks (OALL v2, QIMMA, AraGen) have
moved to native rather than translated tasks, and there the order in 2026
is Falcon-H1-Arabic-34B on the OALL aggregate (~75%), Jais-2-70B-Chat top
on ArabicMMLU and ArabCulture on QIMMA, ALLaM and Fanar close behind, with
the ranking shifting release to release. None of those boards measures
what this app does with a model: pedagogy in English about Arabic, rubric
grading, schema-constrained output, tool calls, vision. The frontier models
are trained hardest for exactly those. Claude's own system card lists
Arabic among the six languages its evaluations are run in.

**Where a different model genuinely helps: as a second opinion on
register.** An Arabic-native open model, run locally, asked one narrow
question — *is this sentence MSA, and if not, which word is dialect?* — is
a cheap, fast, independent judge, and independence is the point: the same
family should not grade its own register. That is the first real job for a
local model here (§5, phase 3), well before it writes anything a learner
sees.

**Honesty about the evidence.** Every number above is a source's, not
ours; the benchmarks are contested (QIMMA exists because the earlier ones
had quality problems), and none tests "explains إضافة to an English
speaker at A2". The only comparison that matters is the one in §4, run on
this app's own tasks.

---

## 3. Local model options, built on generic bases

What "a local LLM version built on a generic model to support MSA" means in
practice is one of three things, in rising cost:

1. **A generic or Arabic-native open model, prompted** — the register line
   of §1 and a strong system prompt. No training. This is where the eval
   starts, because it may be enough for the judge job.
2. **The same model plus a LoRA adapter** trained on the app's own curated
   MSA content with an explicit register tag. The Saudi-Dialect-ALLaM paper
   (2025) did the mirror image — a dialect token on ALLaM-7B via LoRA took
   Saudi output from 48% to 84% and cut MSA leakage from 33% to 6% — with
   5.5k instruction pairs. An `<msa>` tag with the same recipe is the
   cheapest known way to make register a *switch* rather than a hope.
3. **Preference tuning** (DPO) on MSA-vs-dialect pairs, on top of 2, if
   the eval shows the adapter still leaks under conversational prompts.

### Candidate bases

| Model | Sizes | Licence | Arabic story | Fit here |
|---|---|---|---|---|
| **Falcon-H1-Arabic** (TII, UAE) | 3B / 7B / 34B | TII Falcon licence (Apache-2.0-based) | Pre-training rebuilt for Arabic on native MSA *and* dialect data; 34B ≈ 75% OALL, beating some 70B models; 256K context on 7B/34B | **First pick for a single-GPU MSA specialist (7B)**; 34B if a bigger card is ever justified. Hybrid (Mamba+attention) architecture — check vLLM support for the exact version before committing. |
| **Jais 2** (Inception / MBZUAI / Cerebras) | 8B / 70B chat | Apache 2.0 | Trained from scratch Arabic-first with an Arabic-centric tokeniser; covers MSA, dialects, code-switching; GGUF builds published | **Second pick (8B)**; the 70B is the strongest Arabic-native open model but is a multi-GPU deployment. |
| **Fanar 2** (QCRI, Qatar) | 9B (v1) / 27B (v2, Mar 2026) | Apache 2.0 | MSA + Gulf/Levantine/Egyptian; +7 pts language, +3.5 dialect over Fanar 1; aligned to Islamic values and Arab culture | 27B is a sweet spot on one 48 GB card; the cultural alignment is a feature for a tutor, a consideration for a neutral judge. |
| **ALLaM** (SDAIA / HUMAIN, Saudi) | 7B preview | Research / non-commercial; enterprise via HUMAIN | Strong on ArabicMMLU; the model of the dialect-token paper | **Excluded** for a paid app unless licensed. |
| **Qwen 3.5** (Alibaba) | many, incl. small MoE | Apache 2.0 | 201 languages with Arabic among the strong ones; best generic instruction-following of the open families; runs on Ollama/vLLM out of the box | **The base if one local model must serve every course**, not only Arabic; weaker than the Arabic-native models on Arabic knowledge, stronger at following long rubrics and emitting schemas. |
| Gemma 4 (Google) | 31B and smaller | Apache 2.0 | 140+ languages, English-optimised | Not for Arabic specifically. |
| Llama 3.x / 4 | 8B+ | Llama licence | Adequate Arabic; the AceGPT/GemmAr line shows how much instruction-tuning it needs | Superseded by the rows above for this purpose. |

**Recommendation.** Falcon-H1-Arabic-7B *or* Jais-2-8B as the Arabic
specialist (both fit a 24 GB card in bf16 and a 16 GB one quantised), and
Qwen 3.5 mid-size as the generic fallback if the endpoint is ever pointed
at another course. Decide between the two Arabic bases by the eval, not by
the leaderboard: the eval is a day's work and the leaderboards do not
measure our tasks.

### Training data we already own

The MSA adapter's instruction set is mostly already in the repo, curated
and licensed:

- `data/ar_sentences.tsv` — 14,671 reviewed MSA sentences with English
  (after the §1 re-check removes the dialect rows);
- `data/grammar/ar_grammar.json` — 40 points, 274 drills with hints and
  explanations, all MSA (0 marker hits);
- `data/ar_morphology.json` — 6,869 inflection entries;
- tutor and Speak transcripts — **only with the opt-in consent flag** the
  roadmap's (c) requires (`user_profiles`, off by default; never pooled
  without it), PII-scrubbed;
- the Write samples (`writing_samples`) are the learner's hand and stay
  out.

Public MSA sources to widen it if the eval wants more: Arabic Wikipedia
(CC BY-SA — attribution, share-alike on derived *text*, fine for
training), the UN parallel corpus (public), Tatoeba's MSA-tagged sentences
(CC BY). Dialect corpora (MADAR, Alexandria) are for the *negative* side of
the register pairs, not for imitation.

**Size and cost of the adapter.** QLoRA (4-bit base, LoRA rank 16–64) on a
7–9B model with ~20k instruction pairs is a few hours on one A100 or under
a day on a 24 GB consumer card; Modal/RunPod rates in Sept 2026 put an A100
at roughly $2.20–3.45 an hour on demand, so a training run is tens of
dollars, and re-runs as the corpus grows are the same.

---

## 4. The eval harness — before anything is switched

The roadmap's gate rule stands: **a local model serves a task only when it
matches or beats the Claude baseline on that task's eval; otherwise the
admin panel shows the gap and keeps Claude.** The instruments are mostly
here already.

**Held-out set.** 300 items per task from the app's own content: 100
sentence-maker prompts (word + level), 100 drill-maker prompts, 100 Speak
turns (real anonymised learner lines with consent, or synthetic ones written
in dialect on purpose — the harder test). Frozen, versioned in `data/eval/`.

**Metrics, per model, per task.**

| Metric | Instrument | What it catches |
|---|---|---|
| Dialect leakage rate | `ar_register` markers (tripwire) **+** calima-msa OOV rate per sentence (`nlp/arabic.py` analyser) **+** the pinned checker as LLM judge with an "MSA formality" rubric (the Saudi paper's diagnostic, inverted) | The thing the owner complained about, measured three ways so no single instrument's blind spot decides. |
| Acceptance by the checker | `sentence_checker` / `grammar_checker` pass rate (one tier up, never self-certify) | Grammaticality and teachability. |
| Schema compliance | share of responses that parse against `_AUDIT_SCHEMA` / `emit_assessment` | Whether the model can be wired in at all. |
| Level fit | `auditor_level_rule` verdicts | Pitch at the CEFR bar. |
| Latency and cost | p50/p95, tokens, $/1M | Whether it is worth it. |

**Baseline.** Claude with the *pinned* prompts (after §1) — comparing a
local model against the unpinned baseline would flatter it.

**Run it as a script** in `backend/services/quality/` beside the audits, so
it is re-run per model version and per adapter, and its results land as a
page in `docs/quality/` the way every other audit does.

---

## 5. Integration in this codebase

### 5.1 The seam

Today every service constructs `AsyncAnthropic(...)` itself (35 calls in
16 files) and
`resolve_model(task, code, override)` returns an Anthropic model id string;
the per-language `languages.tutor_model` override is validated against an
allow-list of Claude ids (`generation_admin.py`, the Contribute-page picker).
That is one string field short of what the roadmap's item (b) describes.

Build (b) as written, with the detail:

- **`backend/services/providers.py`** — one function the services call
  instead of the SDK:
  `complete(task, language_code, *, system, messages, schema=None,
  tools=None, images=None, max_tokens)`. It calls `resolve_model`, and if
  the resolved id has the prefix `local:` (or the language row carries an
  `endpoint_url`), it goes to an OpenAI-compatible base URL (vLLM, Ollama,
  LM Studio, llama.cpp server all speak it); otherwise to Anthropic as
  now. Same return shape either way (`text`, `parsed`, `usage`, `model`).
- **Structured output** — the makers and checkers rely on
  `output_config.format` JSON schemas. vLLM does the same through guided
  decoding (`response_format: {type: json_schema}`); Ollama through
  `format: <schema>`. The Write assessor's `emit_assessment` **tool** is a
  JSON schema in a hat; give `complete()` a `schema=` path and let the
  provider choose tool-use (Anthropic) or guided JSON (local).
- **Vision stays on Claude.** `write_assess` takes images; none of the
  Arabic bases above is a vision model. `complete()` routes any call with
  `images` to Anthropic regardless of the language override.
- **Health check and fallback** — `GET {endpoint}/v1/models` on the admin's
  "test" button and on a 30-second cache in `complete()`; on failure or
  timeout, fall back to the Claude default and log a `provider_fallback`
  usage row so the Tutor-costs panel shows how often it happened.
- **Per-task, not per-language, routing.** The override today is one column
  per language. Add a `local_tasks` set (JSONB on `languages`, or a
  settings map) so Arabic can send `speak` and `sentence_checker` to the
  local model while `grammar_maker` and `tutor_chat` stay on Claude. The
  gate in §4 is per task; the routing must be too.
- **Usage accounting** — `log_tutor_usage` already keys by kind; add the
  provider so the cost panel separates the two.

Estimated three to four days, the same as the roadmap said, plus a day for
the structured-output shim on vLLM.

### 5.2 Which tasks, in which order

1. **Register judge** (new, small): the local model answers "MSA or not,
   which word" for every Arabic sentence the makers produce and every Speak
   reply before it is shown. Fast, cheap, independent of the maker. If it
   flags, the maker is re-asked once with the flag; if it flags again, the
   item goes to the Workshop queue instead of the learner. This is the
   dialect control the owner is reviewing, made continuous.
2. **Speak** — the highest-volume, most register-sensitive, most
   conversational task, and the one where a 7–8B Arabic-native model at
   A1–B1 sentence length is plausibly *enough*. Shadow first: run both,
   show Claude's, log the local reply, judge offline for two weeks.
3. **Sentence and drill checkers** — the local model as the *second*
   reviewer beside Claude's, not instead of it; disagreement routes to the
   Workshop.
4. **Makers and the tutor** — only after the adapter, and only if the eval
   says so. The tutor explains grammar in the learner's support language;
   that is the frontier models' home ground, and the last thing to move.

### 5.3 Serving

- **Where:** a single GPU box, either a cloud instance (an A10/L4-class
  card at roughly $0.50–0.80 an hour on demand, well under half that as
  spot, is enough for a quantised 7–8B; a 27B wants a 48 GB card) or a
  per-second serverless GPU (Modal-style) for bursty use — per the Sept
  2026 rate comparisons, serverless wins below ~80% utilisation, a
  dedicated pod above it. At the app's current Arabic traffic the honest
  estimate is tens of dollars a month either way; the Tutor-costs panel
  gives the Claude number to compare against.
- **With what:** vLLM for the shared endpoint (continuous batching, guided
  JSON, OpenAI-compatible API); Ollama only for the owner's laptop while
  developing the prompts. The Falcon-H1 hybrid architecture needs a vLLM
  version that supports it — check before choosing it over Jais-2-8B,
  which is a standard transformer.
- **Never in the DigitalOcean web container** — a GPU endpoint is a
  separate service with its own health, and the fallback in 5.1 is what
  keeps the app up when it is not.

---

## 6. Sequence, with effort

| Step | What | Size | Gate |
|---|---|---|---|
| 0 | **Pin MSA everywhere** (§1): `register_line`, twenty call sites, the support-locale case, the call-site test; re-run the pinned checkers over the Arabic corpus and fix what they find. | 1 day | Done when the test passes and `docs/quality/ar.md` records the re-check. |
| 1 | **Eval harness** (§4): held-out sets, three leakage instruments, the script, a results page. Baseline Claude-pinned. | 2–3 days | Numbers for Claude on all three tasks. |
| 2 | **Provider seam** (§5.1): `providers.py`, endpoint per language, per-task routing, health + fallback, usage split. No local model yet — point it at Claude and prove nothing changed. | 3–5 days | All 35 calls go through `complete()`; CI green; fallback exercised in a test. |
| 3 | **Register judge in shadow** (§5.2 step 1) on Falcon-H1-Arabic-7B *and* Jais-2-8B, prompted only. Two weeks of logged verdicts against the eval. | 2 days build + 2 weeks data | Judge agrees with the human review ≥ 95% on the marker set; then it goes live as a gate. |
| 4 | **Speak in shadow** on the better of the two. | 1 day build + 2 weeks data | Leakage ≤ Claude-pinned, checker pass rate ≥ 95% of Claude's, schema compliance ≥ 99%. |
| 5 | **The `<msa>` LoRA adapter** on the app's corpus (§3), evaluated like step 4. | 1 week | Beats the prompted base on leakage by a margin the eval can see. |
| 6 | **Switch per task** where the gate passes; everything else stays on Claude; the admin panel shows the gap per task. | ongoing | — |

Steps 0–2 need no GPU and no decision about which model. Step 0 is the one
that fixes the complaint; the rest is what makes a local model *safe* to
adopt, and the reason to adopt one is cost and independence, not MSA
quality — Claude, pinned, is already good at MSA.

---

## 7. Decisions for the owner

1. **Do step 0 now?** It is a day, it fixes the leak at its source, and it
   changes the wording of Speak's partner for Arabic (MSA in a "spoken-style
   chat" — which is what an MSA course should want, and what a learner
   should be told the partner is doing).
2. **Consent flag for pooling transcripts** into training data — required
   before any adapter uses learner text (roadmap (c)); the curated corpus
   alone is enough to start.
3. **Which base to shadow first** — both, if two weeks of two endpoints is
   affordable (the eval decides); Jais-2-8B alone if not (standard
   architecture, Apache 2.0, GGUF available today).
4. **Does Arabic-as-support-locale get MSA too?** Yes is the neutral
   answer; it should be a deliberate one.
5. **Persian.** `fa` shares the script and the composer; it is not Arabic
   and the register line for it is about formal vs colloquial Persian, not
   MSA. Out of scope here, noted so the register table does not copy the
   Arabic line by accident.

---

## Sources

Leaderboards and models: [Falcon-H1-Arabic (TII)](https://falcon-lm.github.io/blog/falcon-h1-arabic/) ·
[Falcon-H1 family](https://huggingface.co/blog/tiiuae/falcon-h1) ·
[Jais 2 paper](https://arxiv.org/abs/2608.13580) · [Jais-2-70B-Chat](https://huggingface.co/inception42/Jais-2-70B-Chat) ·
[Jais-2-8B-Chat GGUF](https://huggingface.co/inceptionai/Jais-2-8B-Chat-GGUF) ·
[Fanar 2.0 paper](https://arxiv.org/pdf/2603.16397) · [Fanar-2-27B-Instruct](https://huggingface.co/QCRI/Fanar-2-27B-Instruct) ·
[ALLaM-7B-Instruct-preview](https://huggingface.co/humain-ai/ALLaM-7B-Instruct-preview) ·
[QIMMA leaderboard](https://huggingface.co/blog/tiiuae/qimma-arabic-leaderboard) · [Are Arabic benchmarks reliable?](https://arxiv.org/pdf/2604.03395) ·
[Survey of Arabic LLM evaluation](https://arxiv.org/pdf/2510.13430) · [HELM Arabic](https://crfm.stanford.edu/helm/arabic/latest/) ·
[Arabic LLM landscape 2026 (Annota8)](https://annota8.ai/blog/arabic-llm-benchmark-landscape-2026.html) ·
[Best Arabic local LLMs 2026](https://www.promptquorum.com/local-llms/best-arabic-local-llms-2026) ·
[Gemma 4 vs Qwen 3.5](https://www.mindstudio.ai/blog/gemma-4-vs-qwen-3-5-open-weight-comparison).

Register control and training: [Saudi-Dialect-ALLaM: LoRA fine-tuning with a dialect token](https://arxiv.org/abs/2508.13525) ·
[Dialect-to-MSA translation with a 9B LoRA](https://pith.science/paper/2507.20301) ·
[Can dialects be steered like languages?](https://arxiv.org/pdf/2607.03936) ·
[Saudi dialect rubric benchmark (MSA-formality diagnostic)](https://arxiv.org/abs/2608.29990v1).

Frontier comparisons: [Claude vs ChatGPT for Arabic content](https://truescho.com/en/blog/claude-vs-chatgpt-arabic-content-2026) ·
[Claude vs Gemini translation 2026](https://www.machinetranslation.com/blog/claude-ai-vs-gemini) ·
[LLM translation benchmark 2026](https://intlpull.com/blog/llm-translation-quality-benchmark-2026) ·
[Cross-dialectal Arabic translation on LLMs](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12488727/) ·
[Claude Sonnet 5 system card](https://www-cdn.anthropic.com/9e6a1044980d8c4ed85669faf9c2a8342e2e9f1e/Claude%20Sonnet%205%20System%20Card.pdf).

Serving and cost: [vLLM vs Ollama 2026](https://www.sitepoint.com/ollama-vs-vllm-performance-benchmark-2026/) ·
[Modal vs RunPod pricing](https://markaicode.com/pricing/modal-vs-runpod-pricing/) ·
[GPU cloud pricing June 2026](https://www.buildmvpfast.com/api-costs/gpu) ·
[vLLM production cost guide](https://markaicode.com/pricing/vllm-pricing/).
