# Local models on an M1 Mac — a working overview

**Status: a design and learning document, not shipped code.** Nothing in this
repo currently runs a local model. This file exists so the owner can (a) get
productive with local inference and fine-tuning on the M1, and (b) know which
parts of it would actually earn their place in `polyglot-srs` later, and which
would be a strictly worse version of what the app already does.

Written 2026-09-18. The model and tooling landscape moves fast; treat specific
version numbers as "check before relying on this," and the *reasoning* as the
durable part.

---

## 0. The honest summary first

You asked for a broad overview, so here is the conclusion before the 40
pages of it.

**Local models will not replace Claude in this app's hot paths.** The tutor,
the grammar maker/checker, the level estimator and the locale translator are
exactly the tasks where a 4–8B model on an M1 is worst: they are multilingual,
they include low-resource languages (`ar`, `sw`, `yo`, `ha`, `xh`, `mi` — see
`LOW_RESOURCE_LANGUAGES` in `backend/services/models.py`), and the failure mode
is *confidently wrong grammar shipped to a learner*. A local 8B model is a
fluent B1 speaker of Spanish and an unreliable A2 speaker of Yoruba. Your
quality program (`docs/quality/`, the maker–checker rule, "never
self-certify") exists precisely because model output at that reliability level
is not trustworthy. Swapping in a weaker model to save API spend inverts the
thing the program was built to protect.

**Where local models genuinely win for you, ranked by payoff:**

1. **Embeddings.** Dedupe, near-duplicate card detection, collision audits,
   semantic retrieval for the tutor's reference layer. A 0.6B multilingual
   embedding model on the M1 is *as good as* a hosted one for this, runs at
   thousands of sentences a minute, costs nothing, and lets you embed the
   entire content database repeatedly while iterating. This is the single
   highest-value item on the list and it is not an LLM at all.
2. **Batch pre-filters in front of paid checkers.** Cheap local pass that
   throws out the obvious junk (format violations, answer leaks, wrong-script
   rows, obviously-unnatural sentences), so the paid model only sees candidates
   worth paying for. Recall matters, precision doesn't — a pre-filter that
   drops 40% of candidates at 99% recall cuts your checker bill 40%.
3. **A realistic dev loop.** `TUTOR_DEV_MOCK` currently returns canned
   responses. A local model behind the same seam gives you *plausible* output
   in tests and local development with no key and no spend — closer to real
   behaviour than a fixture, without the flakiness of hitting a paid API in CI.
4. **ASR (and maybe TTS).** You pay Azure for fast transcription
   (`backend/services/stt.py`) and Edge/Azure for neural voices
   (`backend/services/tts.py`). Local Whisper/Parakeet is genuinely
   competitive for the major languages. Local TTS is *not* competitive for a
   pronunciation-teaching product — see §4.4, this is the one place I'd tell
   you to keep paying.
5. **Learning.** You want to be able to talk about fine-tuning, eval and
   MLflow with authority. That is a legitimate reason on its own; just don't
   confuse it with a product decision.

**Where I'd push back hardest:** the instinct to fine-tune a model on your card
data early. Fine-tuning is the *last* rung of the ladder in §6, and most
people who reach for it needed better retrieval, a better prompt, or a
constrained decode. Fine-tuning buys you *format, style and domain idiom* far
more reliably than it buys you *knowledge or correctness*. For a language
tutor, correctness is the whole product.

---

## 1. Hardware reality: what your M1 can actually hold

Apple Silicon's advantage is **unified memory** (UMA): the GPU addresses the
same RAM the CPU does, so a 16 GB M1 can put ~11 GB of weights on the GPU where
a 16 GB PC with an 8 GB discrete card cannot. Its disadvantage is **memory
bandwidth**, which is what token generation is actually bound by.

| Chip | Typical RAM | Memory bandwidth | Realistic ceiling |
|---|---|---|---|
| M1 (base) | 8 / 16 GB | ~68 GB/s | 3–4B comfortably; 7–8B at 4-bit is slow but works |
| M1 Pro | 16 / 32 GB | ~200 GB/s | 7–8B comfortable; 14B at 4-bit usable |
| M1 Max | 32 / 64 GB | ~400 GB/s | 14B comfortable; 32B at 4-bit usable |
| M1 Ultra | 64–128 GB | ~800 GB/s | 32–70B at 4-bit |

**The bandwidth rule of thumb:** decode speed ≈ memory bandwidth ÷ model size
in bytes, times ~0.5–0.8 for overhead. A 4-bit 7B model is ~4 GB, so a base M1
at 68 GB/s tops out around 68/4 × 0.7 ≈ **12 tok/s**; an M1 Max at 400 GB/s
gets ~50–70 tok/s on the same model. That formula is the most useful thing in
this section — it tells you, before you download anything, whether a given
model will feel interactive on your machine. Check yours with
`system_profiler SPHardwareDataType` and `sysctl hw.memsize`.

**Quantization** is how you fit things. Weights are stored at reduced
precision: 8-bit (~1 byte/param), 4-bit (~0.5 byte/param), and the various
"k-quants" and mixed schemes in between.

| Precision | 8B model size | Quality cost |
|---|---|---|
| fp16/bf16 | ~16 GB | baseline |
| 8-bit | ~8 GB | negligible |
| 4-bit (Q4_K_M / MLX 4bit) | ~4.5 GB | small but real; worst on reasoning and rare languages |
| 3-bit and below | ~3 GB | don't, except to prove a point |

**The quantization trap that matters for you specifically:** quantization
damage is not uniform across a model's capabilities. It lands hardest on
low-frequency tokens — which is exactly what non-Latin scripts and
low-resource languages are made of. A 4-bit quant that costs 1% on English
MMLU can cost far more on Yoruba diacritics or Arabic morphology. If you
evaluate a local model on English and conclude "4-bit is fine," you have
measured the wrong thing. Evaluate per-language, always.

**Two more memory facts:**

- **KV cache is not free.** Context costs memory on top of weights, roughly
  `2 × layers × kv_heads × head_dim × context_len × bytes_per_element`. For an
  8B model at 32k context this can be another 2–4 GB. Long-context work on a
  16 GB machine will push you into swap, at which point throughput collapses —
  this is the documented failure mode where MLX reports 51 tok/s of decode
  while the *wall-clock* result is ~3 tok/s ([Towards
  AI](https://pub.towardsai.net/apples-mlx-runs-local-llms-3x-faster-than-llama-cpp-until-your-context-hits-40k-715ec441afbb)).
  Measure end-to-end wall clock, never the tok/s the tool prints.
- **macOS caps GPU-wired memory** at roughly 65–75% of RAM. You can raise it
  (`sudo sysctl iogpu.wired_limit_mb=12288` on a 16 GB machine) but you are
  borrowing from the OS; if you swap, you have lost more than you gained.

**Your thermal/battery reality:** sustained inference and especially
fine-tuning will peg the GPU for minutes to hours. A fanless MacBook Air
throttles. Plug in, and expect a training run to make the machine
unpleasant to use for anything else.

---

## 2. The runtime layer: MLX, llama.cpp, Ollama, LM Studio, vLLM

Four things are being conflated whenever people argue about this, and
separating them makes the choice obvious:

- **A tensor framework** — how the math runs on the hardware (MLX, PyTorch/MPS,
  GGML).
- **An inference engine** — how a transformer is served efficiently
  (`mlx-lm`, `llama.cpp`, vLLM).
- **A model manager / UX** — how you pull, store and switch models (Ollama,
  LM Studio).
- **An API surface** — how your code talks to it (OpenAI-compatible HTTP is
  the de facto standard; everything below speaks it).

| Tool | What it is | Use it when |
|---|---|---|
| **MLX / `mlx-lm`** | Apple's array framework + LLM toolkit, built for UMA | You want the fastest path on Apple Silicon *and* you want to fine-tune locally. This is the one to learn. |
| **llama.cpp** | C++ inference engine, GGUF format, Metal backend | You want maximum control (batch size, cache quantization, GBNF grammars), cross-platform parity with a Linux server, or long contexts where MLX degrades. |
| **Ollama** | Model manager + server; uses MLX under the hood on Apple Silicon as of 0.19 | You want `ollama run qwen3:8b` to just work, with an HTTP API and a model library. Best default for app integration. |
| **LM Studio** | GUI + local server, MLX and GGUF backends | You want to browse/compare models and eyeball outputs without writing code. Good for exploration, not for automation. |
| **vLLM / SGLang** | Production serving: continuous batching, paged attention | Not for the M1. This is what you'd deploy on a rented GPU if you ever self-host (§10). Learn it *there*, not here. |

**Recommended setup on the M1:** Ollama as the everyday server (stable API,
easy model swaps), `mlx-lm` installed alongside for fine-tuning and for
anything where you want direct control of the Python objects, and `llama.cpp`
in your back pocket for GBNF-constrained generation and long-context work.
These coexist fine; they just each keep their own model cache, so watch disk
(§5.3).

The 2026 picture, briefly: MLX has become the fastest backend on Apple Silicon
and Ollama adopted it in 0.19, roughly doubling decode speed on some
configurations; the biggest gap is in prompt processing (time-to-first-token),
where MLX exploits hardware llama.cpp doesn't. Note that most of the headline
"30–40% faster" numbers are measured on M4/M5 silicon with Neural
Accelerators; **your M1 will see a smaller gap.** Benchmark on your own
machine before believing a blog post
([sitepoint](https://www.sitepoint.com/local-llms-apple-silicon-mac-2026/),
[comparative study, arXiv](https://arxiv.org/pdf/2511.05502)).

### 2.1 The API seam that makes all of this disposable

Whatever you pick, talk to it over an **OpenAI-compatible `/v1/chat/completions`
endpoint**. Ollama, LM Studio, llama.cpp's server, vLLM and every hosted
open-weights provider (Together, Fireworks, Groq, DeepInfra) expose it. That
means:

- your app code contains no runtime-specific logic;
- swapping Ollama → a rented vLLM box → a hosted provider is a base-URL change;
- you can A/B a local model against a hosted one with the same client.

This is the single most important architectural decision in the whole
document, and it costs you nothing to make now. See §9 for how it lands in
this repo.

---

## 3. LLMs vs SLMs — the axis that actually matters

The "small vs large" framing is a distraction. The real question is
**capability per unit of latency, cost and control**, and it decomposes into
three separate axes:

**Axis 1 — knowledge vs skill.** Parameters mostly buy *knowledge* (facts,
rare words, low-frequency languages, long-tail idiom). Post-training mostly
buys *skill* (following a format, using a tool, classifying against a rubric).
A 4B model can be taught a skill to near-frontier quality. It cannot be taught
the Yoruba tonal system it never saw enough of.

**Axis 2 — breadth vs narrowness.** The value of a big model is that it is
good at a task you didn't anticipate. If you can fully specify the task —
"given this sentence and this answer, output pass/fail and a reason code" —
breadth is something you are paying for and not using.

**Axis 3 — error cost.** If a wrong output is caught downstream (by a checker,
a human reviewer, a schema validator), a cheaper model is fine because you've
built the safety net. If a wrong output reaches a learner, it isn't.

Run any candidate task through those three and the answer falls out:

| Task shape | Model | Why |
|---|---|---|
| Classification, routing, tagging, reason-code assignment | SLM (1–4B), possibly fine-tuned | Narrow, verifiable, huge volume |
| Extraction into a fixed schema | SLM + constrained decoding | Schema does the heavy lifting |
| Dedupe / similarity / clustering | Embedding model (0.3–0.6B) | Not a generation problem at all |
| Translation *checking* into a high-resource language | SLM 7–8B, sampled + human-audited | Recall-oriented pre-filter |
| Drafting grammar explanations, tutor chat, low-resource anything | Frontier API | Knowledge-bound, learner-facing, high error cost |
| Anything where the output is the product | Frontier API | See above |

**The "distillation" pattern** is the bridge between the two columns, and it's
the one worth internalising: use the frontier model to produce high-quality
labelled outputs for a narrow task, then fine-tune a small model on those
outputs until it matches on *that task only*. You pay the frontier price once,
during dataset creation, and the marginal price forever after is your
electricity. This is how you'd legitimately move something like a first-pass
register check or a CEFR level estimator in-house — **not** by prompting an 8B
model and hoping.

Caveat worth stating plainly: distillation from a commercial API is
constrained by that API's terms of service regarding training competing
models. Read them before you build a product on it. Distilling for an
internal classifier that is not a competing general model is a different
posture than distilling a general assistant, but "I read the terms" should be
a real event, not a rhetorical one.

---

## 4. Model shortlist for *this* domain (multilingual, Sept 2026)

Model recommendations rot in months. The selection *criteria* don't:
multilingual coverage of the scripts you teach, a permissive licence, a size
that fits your bandwidth budget, and an active quantization community so MLX
and GGUF builds exist.

### 4.1 Generation

| Family | Sizes | Licence | Notes for you |
|---|---|---|---|
| **Qwen3** | 0.6B–235B; 4B and 8B are the M1 sweet spots | Apache-2.0 | Best default. 29+ languages natively, strongest non-English coverage in the open-weights tier, huge quantization ecosystem. Start here. |
| **Gemma 3** | 1B / 4B / 12B / 27B | Google's Gemma terms (not OSI) | 4B is strong per parameter and multimodal; the licence has use restrictions — read them if anything commercial is downstream. |
| **Phi-4-mini** | 3.8B | MIT | Punches above its weight on reasoning/instruction following, ~20 languages. Good candidate for classifier-style tasks. |
| **Llama 3.x / 4** | 8B up | Meta Community Licence | Fine, huge ecosystem, but no longer the obvious multilingual pick and the licence is the least permissive here. |

Sources:
[BentoML SLM guide](https://www.bentoml.com/blog/the-best-open-source-small-language-models),
[HF open-weights roundup](https://huggingface.co/blog/daya-shankar/open-source-llm-models-to-run-locally).

**Trust benchmarks less than you want to.** MMLU/HumanEval numbers are
English-dominant and heavily contaminated. For your purposes the only
benchmark that counts is the one you build from your own cards (§7). Expect
the ranking on *your* eval to differ from the leaderboard ranking; if it
doesn't, suspect your eval.

### 4.2 Embeddings — the highest-value local component

| Model | Size | Why |
|---|---|---|
| **Qwen3-Embedding-0.6B** | 0.6B | 100+ languages, 32k context, top of MTEB for its size. Strong cross-script separation — relevant when your corpus mixes Cyrillic, Arabic and Latin. |
| **BGE-M3** | 0.6B | Dense + sparse + multi-vector in one model, 100+ languages. The multi-vector mode is genuinely useful for cross-lingual retrieval. |
| **gte-multilingual-base** | 305M | Smallest credible option; fastest; good if you're embedding the whole DB on every iteration. |
| **EmbeddingGemma / Nomic Embed v2** | ~300M / MoE | Worth benchmarking against the above on your data. |

([BentoML embeddings guide](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models))

Practical notes: run these through `sentence-transformers` or
`mlx-embeddings`; batch aggressively (embedding is compute-bound, not
bandwidth-bound, so the M1 does much better here relative to generation);
store vectors in `pgvector` in the Postgres you already run, not in a new
vector database — you do not have a scale problem that justifies another
service.

### 4.3 ASR

Whisper (via `whisper.cpp` with Metal, or `mlx-whisper`) and NVIDIA's
Parakeet family (via `parakeet-mlx`) are the two credible local options.
Parakeet is faster and excellent on English; Whisper large-v3 has far broader
language coverage, which matters given your locale list. Both run on an M1;
`large-v3` needs ~3 GB at 4-bit and runs faster than real time.

**What this could replace:** `backend/services/stt.py` currently calls Azure
fast transcription, deliberately restricted to an allowlist of locales with
good models. A local Whisper pass wouldn't remove the allowlist problem (it
has the same coverage issue) but it would remove per-turn cost and the
round-trip. The catch is §10: your production box is a DigitalOcean App
Platform container, not a Mac, and Whisper on CPU there is not free either.
This is a "prove it locally, then decide" item.

### 4.4 TTS — where I'd tell you not to bother

Kokoro-82M is remarkable for its size and the local stack (Whisper +
Ollama + Kokoro) is a well-trodden path
([DEV](https://dev.to/xadenai/building-a-local-voice-ai-stack-whisper-ollama-kokoro-tts-on-apple-silicon-eo0),
[mlx-audio](https://github.com/Blaizzy/mlx-audio)). But you are not building a
voice assistant, you are building **pronunciation models for learners**. The
gap between Kokoro and Azure Neural on prosody, and especially on
non-English phoneme accuracy, is precisely the gap your product cannot
absorb. A learner imitating a slightly-wrong Arabic vowel length is worse
than no audio. Keep paying for voices; spend the local-model budget elsewhere.

---

## 5. The Hugging Face ecosystem, demystified

"Hugging Face" is four different things and people use the name for all of
them interchangeably.

**5.1 The Hub** — a git-with-LFS host for models, datasets and Spaces. Every
repo is a real git repo; `git clone` works, but use `hf download` (the CLI
from `huggingface_hub`) so you get resumable, parallel, deduplicated
transfers into the shared cache. Key concepts:

- **Model cards** (`README.md` with YAML frontmatter) — licence, languages,
  intended use, eval results. A model with a thin card is a model whose
  training data you cannot reason about.
- **Gated repos** — some models (Llama, Gemma) require accepting terms; you
  authenticate with `hf auth login` and a token. Automate this in CI with a
  read-scoped token in a secret, never a write token.
- **Revisions** — every repo has commits and tags. **Pin a revision in
  production code.** `AutoModel.from_pretrained("org/model")` with no
  `revision=` is the ML equivalent of an unpinned `latest` Docker tag, and
  people have shipped silently-different weights that way.
- **safetensors** — the weight format that replaced pickle. Pickle files
  execute arbitrary code on load. Prefer `.safetensors`; if a repo only ships
  `.bin`, that's a signal about its maintenance.

**5.2 The libraries**, roughly in the order you'd meet them:

| Library | What it does |
|---|---|
| `transformers` | Model + tokenizer loading, generation, the `Auto*` classes |
| `tokenizers` | Fast BPE/Unigram implementations. Worth understanding deeply given your linguistics background — see §5.4 |
| `datasets` | Memory-mapped (Arrow) dataset loading, mapping, splitting, streaming |
| `accelerate` | Device placement and distributed training; the thing that makes `device_map="auto"` work |
| `peft` | LoRA / QLoRA / DoRA adapters |
| `trl` | Post-training: `SFTTrainer`, `DPOTrainer`, `GRPOTrainer`, reward modelling. v1.0 (Apr 2026) unified these into one stack ([MarkTechPost](https://www.marktechpost.com/2026/04/01/hugging-face-releases-trl-v1-0-a-unified-post-training-stack-for-sft-reward-modeling-dpo-and-grpo-workflows/)) |
| `sentence-transformers` | Embedding models, similarity, and — importantly — *training* embedding models |
| `evaluate` / `lighteval` | Metric implementations and harnesses |
| `optimum` | Export/optimization (ONNX, CoreML) for deployment |

**5.3 The cache, which will eat your disk.** Everything lands in
`~/.cache/huggingface/hub`, Ollama keeps its own in `~/.ollama/models`, and
LM Studio a third in `~/.lmstudio`. Three copies of an 8B model is 15 GB. Set
`HF_HOME` to an external drive if you're on a 256/512 GB Mac, and run
`hf cache scan` / `hf cache delete` periodically. This is the most common
"why is my Mac full" cause for people doing this work.

**5.4 The tokenizer digression that is actually relevant to your product.**
Tokenizer fertility — tokens per word — varies enormously by language. English
runs ~1.3 tokens/word; Russian 2–3×; Arabic and Korean worse; a language with
rich morphology and a non-Latin script can cost 3–4× the tokens for the same
semantic content. Three consequences for you:

1. **Cost and latency are not language-neutral.** Your Arabic and Russian
   courses cost meaningfully more per tutor turn than the Spanish one, on the
   same model. Worth measuring — it's a real line item hiding in your unit
   economics.
2. **Effective context is language-dependent.** A 32k window holds noticeably
   less Arabic text than English text.
3. **Model choice should weigh tokenizer coverage**, not just benchmark
   scores. A model whose tokenizer fragments Yoruba diacritics into byte
   soup will underperform on it regardless of parameter count. You can
   measure this in ten lines: tokenize a parallel corpus in each of your
   languages and compare tokens-per-character across candidate models. That
   is a genuinely novel-ish internal metric and exactly the kind of thing
   your linguistics background lets you do better than most ML engineers.

**5.5 Publishing your own artifacts.** When you train something, push the
*adapter* (a few tens of MB), not a fused full model, plus a card recording:
base model + revision, dataset + its commit, hyperparameters, eval numbers
against a named eval set, and known failure modes. That card is the
reproducibility contract. If you can't fill it in, you can't reproduce the
run — which is the same problem MLflow solves from the other end (§8).

---

## 6. Training: the ladder, and where to stop climbing

Every rung costs more than the one below and should only be attempted after
the one below has demonstrably failed **against a measured baseline**. The
single most common failure in applied LLM work is skipping to rung 5.

| # | Rung | Cost | Buys you |
|---|---|---|---|
| 1 | Better prompt + few-shot examples | hours | Most of the gap, most of the time |
| 2 | Constrained decoding (schema/grammar) | hours | 100% format compliance — see §6.4 |
| 3 | Retrieval (give it the right context) | days | Knowledge it lacks, updatable without retraining |
| 4 | Routing / cascades (small model first, escalate) | days | Cost, not quality |
| 5 | SFT / LoRA on your data | 1–2 weeks | Format, style, domain idiom, latency (shorter prompts) |
| 6 | Preference optimization (DPO/GRPO) | weeks | Taste — choosing between two plausible outputs |
| 7 | Continued pretraining | months + real GPUs | New language/domain capability. Not a laptop activity |

**What fine-tuning does and does not do.** It reliably teaches *form*: always
emit this JSON shape, always use this register, always explain grammar in this
house style, always refuse in this way. It unreliably teaches *facts*, and it
actively damages capabilities you don't include in the training mix
(catastrophic forgetting — fine-tune only on Spanish drills and watch Russian
degrade). For your app, the honest framing is: a fine-tune could make a local
model *sound like your grammar explanations*. It will not make it *correct
about Yoruba tone*.

### 6.1 Data: where yours would come from, and the trap in it

You are in an unusually good position — you have a curated content database
with human review state, and a quality program that has already made
judgements. Candidate datasets, in rough order of tractability:

- **(sentence, answer, verdict, reason)** from your validation guards and
  audits → a classifier fine-tune. Labels already exist, deterministically.
- **Human-reviewed vs rejected AI drills** (`source='ai'`, `reviewed`) → a
  preference dataset for a quality scorer. This is the highest-value dataset
  you own and it is accumulating for free right now.
- **Register/level-labelled sentences** from the register passes → a CEFR
  level estimator, currently a paid `level_estimate` call.
- **Gloss/definition pairs** → style transfer into house voice.

**The trap:** your reviewed content is *selected*, not *sampled*. The rows
that survived review are not a random draw — they're the ones that passed
guards that already encode your rules. Train on them naively and you learn
"what my guards let through," which is circular: the model agrees with the
guards, your eval (built the same way) says it's great, and it has learned
nothing the guards didn't already know. Deliberately keep rejected examples
and hard negatives, and build at least part of your eval set by *fresh human
labelling* of a random sample, not by reusing guard verdicts.

**Volume:** LoRA for format/style starts showing results at ~500–1,000 good
examples and saturates around 5–10k. Quality beats quantity by a wide margin;
100 hand-checked examples beat 2,000 scraped ones. Split **before** any
dedupe or augmentation, and split by *grammar point / lemma family*, not by
row — otherwise near-duplicate drills for the same point land in both train
and test and your eval number is a leak, not a result. Your `audit_collisions`
work is directly reusable here.

### 6.2 Doing it on the M1 with MLX

`mlx-lm` ships LoRA, QLoRA and DoRA natively; a 4-bit 7–8B QLoRA run fits in
roughly 7–8 GB of working memory, i.e. a 16 GB machine
([KDnuggets](https://www.kdnuggets.com/fine-tuning-language-models-on-apple-silicon-with-mlx),
[llmcheck guide](https://llmcheck.net/guides/fine-tune-llm-mac-mlx/)).

```bash
pip install mlx-lm

# data/ holds train.jsonl and valid.jsonl, one JSON object per line:
#   {"messages": [{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}

mlx_lm.lora \
  --model mlx-community/Qwen3-4B-Instruct-4bit \
  --train \
  --data ./data \
  --fine-tune-type lora \     # lora | dora | full
  --num-layers 16 \           # how many transformer layers get adapters
  --batch-size 1 \            # keep at 1 on 16 GB
  --iters 600 \
  --learning-rate 1e-5 \
  --adapter-path ./adapters/level-estimate-v1

# evaluate the adapter, then generate with it
mlx_lm.lora --model <base> --adapter-path ./adapters/... --test --data ./data
mlx_lm.generate --model <base> --adapter-path ./adapters/... --prompt "..."

# optionally fuse into a standalone model for serving
mlx_lm.fuse --model <base> --adapter-path ./adapters/... --save-path ./fused
```

Hyperparameters that actually matter, in order: **number of layers adapted**
(more = more capacity and more forgetting; 8–16 is a normal range), **LoRA
rank** (8–32; higher for genuinely new behaviour, lower for style), **learning
rate** (1e-5 to 1e-4; too high is the #1 cause of a model that starts
babbling), and **iterations** (watch validation loss; stop when it turns up).
Everything else is noise until those four are right.

Expect roughly 20–60 minutes for a small LoRA on a few thousand examples on an
M1 Pro/Max; a base M1 will be several times that. If a run would take more
than ~2 hours, rent an hour of an A100 instead — at ~$1–2/hour that is
cheaper than your time, and the same TRL/PEFT script runs there unchanged.
**That is the real argument for learning the HF stack alongside MLX:** MLX is
the fast local path, TRL/PEFT is the portable path that scales off the laptop.

### 6.3 The TRL path (portable)

```python
from trl import SFTTrainer, SFTConfig
from peft import LoraConfig

trainer = SFTTrainer(
    model="Qwen/Qwen3-4B-Instruct",
    train_dataset=ds["train"],
    eval_dataset=ds["validation"],
    peft_config=LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                           target_modules="all-linear"),
    args=SFTConfig(
        packing=True,              # concatenate short samples to fixed length
        max_length=2048,
        num_train_epochs=2,
        learning_rate=2e-5,
        bf16=True,
        eval_strategy="steps", eval_steps=50,
        report_to="mlflow",        # §8 — one line, and the run is tracked
    ),
)
trainer.train()
```

`packing=True` matters more than it looks: without it, a batch of short drill
sentences is mostly padding and you burn most of your compute on nothing.

For preference training (rung 6), the same shape with `DPOTrainer` and a
dataset of `(prompt, chosen, rejected)` — which your review workflow produces
naturally every time a reviewer picks one candidate over another. GRPO is the
RL variant that's worth knowing about conceptually (it optimizes against a
*programmatic reward* rather than a preference dataset), and it fits your
domain unusually well: your guards in `backend/services/drills.py` are
already a machine-checkable reward function. That is an interesting research
direction, not a next step.

### 6.4 Constrained decoding — rung 2, and criminally underused

Before fine-tuning for format, force the format. Grammar-constrained decoding
compiles a JSON Schema (or an arbitrary grammar) into a state machine and
zeroes out any token that would break it, so malformed output is not merely
unlikely, it is *unrepresentable*. Implementations: llama.cpp's GBNF,
XGrammar (the default in vLLM ≥0.7, also SGLang/TensorRT-LLM/MLC), Outlines,
and native structured outputs in Ollama and all the hosted APIs — Anthropic
shipped GA structured outputs in Feb 2026
([overview](https://www.aidancooper.co.uk/constrained-decoding/),
[vLLM](https://developers.redhat.com/articles/2025/06/03/structured-outputs-vllm-guiding-ai-responses)).

Two caveats people skip: constraints guarantee *shape*, not *content* — a
schema-valid wrong answer is still wrong; and over-constraining can hurt
quality, because forcing the model into a rigid frame before it has "thought"
suppresses reasoning. The standard fix is a two-field schema where the model
writes its reasoning into a free-text field first and the verdict second.
Your existing `_DRILL_SCHEMA` and `_SCHEMA` constants are already the right
shape for this to slot in.

---

## 7. Testing and evaluation — the part that decides whether any of this is real

This is the section that separates people who *have* a local model from people
who have *shipped* one. It is also the part with the most transferable value
to your day job: eval infrastructure is the hard, unglamorous, durable skill.

### 7.1 The three kinds of eval, and what each is for

1. **Deterministic checks** — schema validity, no answer leaks, correct script,
   the answer actually appears in the sentence. Cheap, exact, and they should
   run on 100% of outputs forever. You already have these
   (`validate_drill`, the NLP answerability layer). They are not "eval," they
   are a type system, and they catch more real defects than anything below.
2. **Reference-based metrics** — exact match, F1, accuracy against a gold
   label. Applicable wherever a ground truth exists (classification, level
   estimation, form selection). Use these wherever you possibly can: they are
   free, stable, and not themselves a model.
3. **LLM-as-judge** — a model scores an output against a rubric. Necessary for
   "is this explanation clear," "is this sentence natural." Also the most
   dangerous, because it *always returns a number* whether or not that number
   means anything.

**The order matters.** Every time you can convert a judge metric into a
reference metric or a deterministic check, do it. Most teams' eval suites are
70% judge because that was the fastest to write, and they are measuring the
judge.

### 7.2 Building the golden set

- **200–500 examples per task minimum.** Below ~100 your confidence interval
  is wider than the differences you're trying to detect; a 5-point difference
  on 50 examples is noise.
- **Stratify deliberately**: by language, by CEFR level, by grammar point
  type, and — critically — include a *hard* stratum of cases you know models
  get wrong. An eval set of easy cases saturates and stops discriminating.
- **Freeze it and version it.** A golden set that changes between runs makes
  every comparison meaningless. Commit it; treat edits as a reviewed change
  with a changelog.
- **Keep a holdout you never look at.** If you iterate against a set, you
  overfit to it — by hand, via prompt tweaks, just as surely as by gradient
  descent.
- **Label some of it yourself.** You are the domain expert for four of these
  languages. 100 personally-labelled rows is worth more than 1,000 rows of
  model-assigned labels, and it's the only way you'll learn whether your
  rubric is even well-defined.

### 7.3 Making an LLM judge trustworthy

A judge is a model, so it needs its own eval. The procedure:

1. Write the rubric with **explicit anchors** ("3 = grammatical and natural;
   2 = grammatical but a native speaker wouldn't say it; 1 = ungrammatical"),
   not vibes ("rate naturalness 1–5").
2. Human-label a calibration set (~100 items).
3. Measure judge-vs-human agreement with **Cohen's κ** (or Krippendorff's α),
   not raw accuracy — raw agreement is inflated by class imbalance. κ below
   ~0.6 means your judge is not measuring your rubric; fix the rubric before
   fixing the model.
4. Re-run calibration whenever you change the judge model or the prompt. A
   judge upgrade is a measurement-instrument change and invalidates historical
   comparisons unless you re-baseline.

Known judge pathologies to design around: **position bias** (in pairwise
comparison, swap the order and average); **verbosity bias** (longer answers
score higher — control for length); **self-preference** (a model rates its own
family's output higher, so never judge Claude output with Claude when the
comparison is Claude-vs-local); and **rubric drift** (the judge silently
reweights criteria as the prompt grows — keep rubrics short and one-dimensional,
run several narrow judges rather than one omnibus judge).

Your repo already encodes the deepest version of this principle — "never
self-certify," checkers run one tier up (`backend/services/models.py`). Apply
it to eval too: the judge must not be the maker.

### 7.4 Statistical hygiene

- Report **confidence intervals**, not point estimates. Bootstrap them; it's
  five lines.
- For A-vs-B, use **paired** comparison on the same items — massively more
  sensitive than comparing two independent means.
- Set a **minimum detectable effect** before running. If your set can only
  detect a 7-point difference and you're chasing 2 points, add data or accept
  you can't answer the question.
- Set **temperature 0 / fixed seed** for eval runs, and still expect
  non-determinism from batching on some backends. Run three times; if your
  metric moves more between reruns than between models, your eval is too small.

### 7.5 Wiring eval into CI

The endpoint of this work is: **a PR that changes a prompt, a model, or a
guard runs the eval suite and fails if quality regresses.** That is the
same bar `CLAUDE.md` already sets for `pytest` and `npm run build` — the only
difference is that the threshold is statistical rather than binary.

MLflow 3.14 ships a pytest integration specifically for gating GenAI quality
in CI ([MLflow releases](https://mlflow.org/releases/)), which is the natural
fit here. Practical shape:

- A fast tier (dozens of items, deterministic checks only) runs on every PR.
- A slow tier (full golden set, judges) runs nightly or on-demand via a
  label, because judge calls cost money and minutes.
- Thresholds are **relative to a recorded baseline**, not absolute — the same
  pattern as your known-failing-test baseline in `CLAUDE.md`.

---

## 8. MLflow — what it is and whether you need it

MLflow is four products under one name. Knowing which one you're using
prevents most of the confusion:

1. **Tracking** — log params, metrics, and artifacts per run, compare runs in
   a UI. The original, and the part that matters for §6.
2. **Model Registry** — versioned model artifacts with stage transitions
   (staging → production) and lineage back to the run that made them.
3. **Tracing (GenAI)** — OpenTelemetry-compatible spans capturing inputs,
   intermediate steps and outputs of an LLM app. Compatible with OTel GenAI
   semantic conventions, so you're not locked in.
4. **`mlflow.genai.evaluate()`** — the eval harness: **scorers** (small
   composable functions returning a score or pass/fail), built-in and custom
   LLM judges (Anthropic, Gemini, OpenAI-compatible via litellm), review
   queues for human feedback, and the pytest gate mentioned above
   ([MLflow GenAI docs](https://mlflow.org/docs/latest/genai/),
   [Databricks](https://www.databricks.com/blog/mlflow-30-unified-ai-experimentation-observability-and-governance)).

**Local setup is genuinely five minutes:**

```bash
pip install mlflow
mlflow server --backend-store-uri sqlite:///mlflow.db \
              --default-artifact-root ./mlruns --port 5000
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
```

```python
import mlflow
mlflow.set_experiment("level-estimate")
with mlflow.start_run(run_name="qwen3-4b-lora-r16"):
    mlflow.log_params({"base": "Qwen3-4B", "rank": 16, "layers": 16, "lr": 1e-5})
    mlflow.log_metric("exact_match", 0.81)
    mlflow.log_artifact("adapters/level-estimate-v1")
```

**What to log, non-negotiably:** base model *with revision hash*, dataset
version/commit, every hyperparameter, the eval set identifier, the metric with
its CI, and the git SHA of the code. If you can't reconstruct a run from its
logged metadata, it didn't happen — you have a number with no provenance,
which is worse than no number.

**Do you need it?** For a handful of runs, a directory of JSON files and a
spreadsheet genuinely works, and I'd rather you start there than spend a day
on infrastructure before you have anything to track. MLflow earns its place at
around run 20, when you can no longer remember whether the good result came
from rank 32 or from the cleaned dataset. Given that you also want the
resume/interview value, learning it is cheap and it is the de facto standard
in enterprise ML — including, almost certainly, at Citi.

**Alternatives, honestly:** Weights & Biases is nicer for experiment tracking
UX and worse for the "self-host it for free forever" property. Langfuse and
Opik are lighter-weight, GenAI-only, open-source tracing/eval tools with less
ceremony than MLflow — if you only ever want tracing and eval and never
training runs, Langfuse is the smaller thing that fits. Braintrust is the
commercial polish option. MLflow's argument is breadth (it covers both the
training and the GenAI halves) and ubiquity, not elegance.

**Where this would live for you:** on the Mac, as a dev-time service. Do not
put MLflow tracking in the request path of the FastAPI app. If you eventually
want production LLM tracing, that's a separate decision with a latency budget
attached, and the answer might be Langfuse or plain structured logs into the
observability you already have (Sentry).

---

## 9. Integrating into `polyglot-srs` — the seam already exists

The good news: you already built the abstraction this needs.
`backend/services/models.py` resolves `task -> model` in one place, with a
documented priority order and a rule (checkers run one tier up) that the type
of the *field*, not the name of the task, enforces. Every AI call site goes
through `resolve_model()`. That is exactly the seam a second provider plugs
into, and you got it right by accident of good design.

### 9.1 What would have to change

Today `resolve_model()` returns a model *name* and each service constructs
`AsyncAnthropic()` directly. To support a local model you need it to return a
*provider + model*, and a thin client factory:

```python
# services/models.py — sketch, not shipped
@dataclass(frozen=True)
class ModelRef:
    provider: Literal["anthropic", "openai_compatible"]
    name: str
    base_url: str | None = None   # e.g. http://127.0.0.1:11434/v1

def resolve_model(task, language_code=None, override=None) -> ModelRef: ...
```

with an `llm_client(ref)` helper returning something both backends satisfy.
Since Ollama/llama.cpp/LM Studio/vLLM all speak the OpenAI wire format
(§2.1), "local" and "hosted open-weights" are the *same* provider with a
different base URL — which means the decision "run it on my Mac vs rent a GPU
vs use Together" becomes config, not code.

Non-negotiable properties of that change:

- **Fail closed.** A local provider that is unreachable must not silently
  downgrade a learner-facing call. Either fall back to the configured hosted
  model, or fail the request — never quietly return an unchecked local answer
  where a checked one was promised. This is the same posture as the migration
  rule in `CLAUDE.md`: degrade deliberately, don't crash, don't lie.
- **Provenance must record the real model.** `origin_detail` already stores
  the model for WP38 provenance. A locally-generated row must be
  distinguishable forever, because if a local model turns out to have a
  systematic flaw you need to find every row it touched. This is the single
  most important requirement in this section.
- **The checker tier rule must survive.** A local model must never be
  resolvable as a checker for a learner-facing maker. Encode that as a
  constraint in `TASK_MODELS`, not a convention.
- **Tests must not depend on a running local server.** Local-provider tests
  either mock the HTTP layer or skip with a marker, like `requires_wordnet`
  in `backend/tests/conftest.py`.

### 9.2 Task-by-task verdict

| Task | Local? | Reasoning |
|---|---|---|
| `tutor_chat`, `reader` | **No** | Learner-facing, open-ended, multilingual. The thing frontier models are for. |
| `grammar_maker`, `sentence_maker` | **No** (maybe as *candidate generator* in bulk, always with the paid checker) | Drafting quality is the ceiling on content quality |
| `grammar_checker`, `sentence_checker`, `translate_checker` | **Never** | Checkers are the safety net; weakening them defeats the whole design |
| `level_estimate` | **Yes, eventually** | Bounded label space, ground truth exists, ideal distillation target (§3) |
| `semantic_check` | **As a pre-filter only** | Run local first, escalate anything it flags *or* is unsure about to the paid checker. Recall-oriented. |
| `translate` (locale rows) | **Partially** | High-resource target languages only, and only with the paid checker retained |
| Dedupe / collision audits (`audit_collisions`) | **Yes, now** | Embeddings, not generation. Highest value, lowest risk |
| `write_assess` (vision) | **No** | Local VLMs on handwriting in non-Latin scripts are not close |
| `TUTOR_DEV_MOCK` replacement | **Yes, now** | Pure upside: realistic dev behaviour, zero spend, no key |
| STT (`stt.py`) | **Prototype it** | Real cost savings possible; production hosting is the blocker (§10) |
| TTS (`tts.py`) | **No** | Quality gap lands exactly where the product can't absorb it (§4.4) |

The pattern across that table: **local models belong on the inside of your
quality funnel, never on the outside.** Anything a human or a stronger model
subsequently checks is fair game. Anything that reaches a learner unchecked is
not.

### 9.3 A concrete first project

If you want one piece of work that is genuinely useful, low-risk, and teaches
most of this document:

**Semantic near-duplicate detection across the content database.** Embed every
sentence/card with Qwen3-Embedding-0.6B locally, store vectors in `pgvector`,
find cross-course and within-course near-duplicates above a threshold you
calibrate against a hand-labelled set of 200 pairs, and report them into the
existing audit tooling. It touches embeddings, evaluation, threshold
calibration, and a real content-quality problem, and it never writes to
production (you'd prepare the report; the owner runs any write — `CLAUDE.md`).

---

## 10. Production hosting and the cost math

**The M1 is a development machine, not a server.** Your production deploy is
DigitalOcean App Platform, which is CPU containers — you already hit its build
limits with camel-tools' torch dependency (see `pyproject.toml`). There is no
path to serving a 7B model there at acceptable latency. So "local models in
production" really means one of:

| Option | ~Cost | When it makes sense |
|---|---|---|
| Keep frontier APIs | pay per token | Default. Almost certainly correct for the learner-facing paths |
| Batch on the Mac, push results | $0 | **The best option you have.** Offline content pipelines, audits, embeddings. No serving problem at all |
| Hosted open-weights (Together/Fireworks/Groq/DeepInfra) | ~$0.05–0.30 / M tokens for 7–8B | You've validated a local model's quality and want it in the request path without ops |
| Rented GPU (Modal, RunPod, a DO GPU droplet) | ~$0.5–2/hr, or per-second serverless | Sustained high volume, or a fine-tuned model no host carries |
| Self-hosted vLLM on a dedicated GPU | $300–1,500/mo | You have volume that justifies it. You do not, yet |

**Break-even thinking.** A frontier-tier model costs on the order of dollars
per million tokens; a hosted 8B costs on the order of cents. If a task burns
10M tokens a month, that's a difference of tens of dollars a month. A rented
GPU at $500/month needs to displace *hundreds of dollars* of API spend before
it breaks even — and that's before your time maintaining it, which at any
realistic hourly valuation of your evenings dwarfs the infrastructure
difference. **Your API bill is almost certainly not your binding constraint;
your time is.** Optimising the bill by adding an inference platform to
maintain is a bad trade until the bill is several hundred dollars a month.

Where the math *does* work immediately: the batch lane. Generating embeddings
for the whole database, running a pre-filter across tens of thousands of
candidate rows, doing five iterations of a quality sweep while you tune a
threshold — those are jobs where API cost scales with your *iteration count*,
and free local compute changes how freely you can experiment. That is a real
and underrated benefit: **not saving money, but removing the marginal cost of
trying things.**

---

## 11. Agents vs. not

Your instinct should be **workflow first, agent only where discovery is the
bottleneck** — which happens to be exactly what this codebase already does.
The maker–checker pipeline is a deterministic workflow with LLM steps: fixed
control flow, judgement only inside bounded steps, every output validated
before it persists. That is the pattern production systems converge on, and
you converged on it without the detour
([Anthropic's workflow-vs-agent framing](https://mer.vin/2026/05/when-not-to-build-ai-agents-anthropics-workflow-vs-agent-playbook/),
[Towards Data Science](https://towardsdatascience.com/a-developers-guide-to-building-scalable-ai-workflows-vs-agents/)).

**The definitions worth holding onto:**

- **Workflow** — you control the flow; the LLM fills in steps. Testable,
  costable, debuggable.
- **Agent** — the LLM controls the flow, deciding which tools to call and when
  to stop. Flexible, and you pay for that flexibility on *every run* in
  latency, token cost (roughly quadratic as the transcript grows), and a
  failure surface you cannot unit-test.

**The test:** can you draw the complete flowchart before seeing the input? If
yes, it's a workflow, and building an agent is a strictly worse implementation
of a thing you already understand. Agents earn their cost when the path can't
be hardcoded **but progress is still verifiable** — coding agents with tests,
support agents with tool-backed actions.

**Where an agent could legitimately fit in your world:**

- **Content research**, off the hot path: "find and cite three authentic
  examples of this construction, check them against the corpus, propose a
  drill." Path is genuinely unknown; output is verified by existing guards;
  latency doesn't matter because it's offline. This is the good case.
- **Contributor/feedback triage** with tool access to the DB — plausible, but
  a classifier plus a workflow probably does 90% of it for 5% of the cost.
- **Not** the tutor. A tutoring turn is latency-sensitive and its shape is
  known. Keep it a workflow.

**Local models and agents are a bad combination right now.** Tool-calling
reliability degrades sharply below ~7B, errors compound across turns, and an
agent's long transcripts hit exactly the long-context regime where Apple
Silicon inference falls apart (§1). If you want to learn agents, learn them
against a frontier API; if you want to learn local models, learn them on
single-step tasks. Doing both at once means every failure has two candidate
causes.

**MCP** (Model Context Protocol) is worth knowing as the standard for
exposing tools/data to models — it's how you'd give an agent typed access to
your content DB without bespoke glue, and it's transferable knowledge. But
note that an MCP server exposing your database is an access-control surface:
scope it read-only, and keep the production-write rule from `CLAUDE.md`
absolute regardless of what's calling.

---

## 12. Licensing, privacy and the things that bite later

- **Licences are not all "open."** Apache-2.0 (Qwen3, many others) is genuinely
  permissive. Gemma has Google's use-restriction terms; Llama has the Meta
  Community Licence with an MAU threshold and naming requirements. If a model
  touches anything commercial, read the actual licence — "open weights" is a
  marketing category, not a legal one.
- **Derivatives inherit.** A LoRA adapter trained on a restrictively-licensed
  base inherits those restrictions. So can a model fine-tuned on outputs of a
  model whose terms forbid it (§3).
- **Privacy is the strongest real argument for local.** Learner audio is
  biometric data — your `stt.py` already refuses to store it, which is the
  right call. Processing it on hardware you control is strictly better than
  shipping it to a vendor, and it's an argument that survives a GDPR
  conversation. That is a better justification for local ASR than cost is.
- **Model supply chain.** Pin revisions, prefer `safetensors`, don't run
  arbitrary `trust_remote_code=True` repos, and treat a random fine-tune from
  an unknown account exactly as you'd treat an unvetted npm package.
- **Local ≠ private if you're careless.** LM Studio and Ollama both listen on
  a port. Don't bind them to `0.0.0.0` on a coffee-shop network.

---

## 13. A staged plan that ends somewhere useful

Each stage produces an artifact and can be abandoned without wasting the
previous one.

**Stage 1 — inference fluency (a weekend).** Install Ollama and `mlx-lm`. Pull
Qwen3-4B and 8B. Measure *your* tok/s and time-to-first-token with the
bandwidth formula from §1 as a prediction, and see how close you were. Run the
same 20 prompts through both and through Claude. Write down where the local
model falls over — this is your first, informal eval, and the point is
calibration: you need a felt sense of the gap before any of the later
decisions are meaningful.

**Stage 2 — embeddings and a real result (a week).** Qwen3-Embedding-0.6B over
your content DB, vectors in `pgvector`, near-duplicate report. Hand-label 200
pairs, calibrate the threshold, report precision/recall with confidence
intervals. **This is the stage that pays for itself**; everything after it is
optional.

**Stage 3 — eval infrastructure (a week).** Pick one narrow task
(`level_estimate` is the best candidate). Build a frozen 300-item golden set
stratified by language and level. Score Claude, Qwen3-8B, and Qwen3-4B on it.
Add a judge for one subjective dimension and calibrate it against your own
labels with Cohen's κ. You now have the thing most teams never build.

**Stage 4 — MLflow (two days).** Local server, log stages 2 and 3
retroactively if you still can. Get the run-comparison view working. Add the
pytest gate for the fast tier.

**Stage 5 — first fine-tune (a week).** Distil `level_estimate` from Claude
labels into a Qwen3-4B LoRA via `mlx_lm.lora`. Evaluate against the *same*
frozen set from stage 3. Two outcomes, both good: it matches and you have a
free classifier, or it doesn't and you know exactly how much the frontier
model was doing. Log everything to MLflow; push the adapter to the Hub with a
real model card.

**Stage 6 — integrate one thing (a week).** The `ModelRef` refactor from §9.1,
with the local provider wired to exactly one non-learner-facing task, full
provenance, tests that don't need a server, and an entry in `LEARN.md`
explaining the new seam.

**Explicitly deferred:** preference training, agents, self-hosted serving,
local TTS. Each has a clear trigger — respectively: you have ≥1,000 reviewer
preference pairs; you have a task whose path genuinely can't be drawn; your
API bill passes a few hundred dollars a month; open TTS closes the prosody gap
on your non-English locales.

---

## 14. Sources

Runtimes and hardware:
[Local LLMs on Apple Silicon 2026](https://www.sitepoint.com/local-llms-apple-silicon-mac-2026/) ·
[macOS runtime comparison](https://dev.to/bspann/running-llms-locally-on-macos-the-complete-2026-comparison-48fc) ·
[Comparative study of MLX, MLC-LLM, Ollama, llama.cpp (arXiv)](https://arxiv.org/pdf/2511.05502) ·
[MLX long-context degradation](https://pub.towardsai.net/apples-mlx-runs-local-llms-3x-faster-than-llama-cpp-until-your-context-hits-40k-715ec441afbb)

Models:
[Best open-source SLMs 2026 (BentoML)](https://www.bentoml.com/blog/the-best-open-source-small-language-models) ·
[Open-weights models to run locally (HF)](https://huggingface.co/blog/daya-shankar/open-source-llm-models-to-run-locally) ·
[Open-source embedding models (BentoML)](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models)

Training:
[Fine-tuning on Apple Silicon with MLX (KDnuggets)](https://www.kdnuggets.com/fine-tuning-language-models-on-apple-silicon-with-mlx) ·
[MLX LoRA guide](https://llmcheck.net/guides/fine-tune-llm-mac-mlx/) ·
[TRL docs](https://huggingface.co/docs/trl/en/index) ·
[TRL v1.0 post-training stack](https://www.marktechpost.com/2026/04/01/hugging-face-releases-trl-v1-0-a-unified-post-training-stack-for-sft-reward-modeling-dpo-and-grpo-workflows/)

Structured output:
[Constrained decoding explainer](https://www.aidancooper.co.uk/constrained-decoding/) ·
[Structured outputs in vLLM (Red Hat)](https://developers.redhat.com/articles/2025/06/03/structured-outputs-vllm-guiding-ai-responses)

Eval and tracking:
[MLflow GenAI docs](https://mlflow.org/docs/latest/genai/) ·
[MLflow releases](https://mlflow.org/releases/) ·
[MLflow 3.0 announcement (Databricks)](https://www.databricks.com/blog/mlflow-30-unified-ai-experimentation-observability-and-governance)

Speech:
[mlx-audio](https://github.com/Blaizzy/mlx-audio) ·
[Local voice stack on Apple Silicon](https://dev.to/xadenai/building-a-local-voice-ai-stack-whisper-ollama-kokoro-tts-on-apple-silicon-eo0)

Agents vs workflows:
[When not to build agents](https://mer.vin/2026/05/when-not-to-build-ai-agents-anthropics-workflow-vs-agent-playbook/) ·
[Workflows vs agents (Towards Data Science)](https://towardsdatascience.com/a-developers-guide-to-building-scalable-ai-workflows-vs-agents/)
