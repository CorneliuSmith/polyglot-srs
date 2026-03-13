# Phase 2: NLP Backends and Answer Validation - Research

**Researched:** 2026-03-13
**Domain:** NLP morphological analysis, multilingual answer validation (Russian, Arabic, English)
**Confidence:** HIGH

## Summary

This phase builds the core differentiator of PolyglotSRS: language-aware answer validation that returns nuanced feedback (CORRECT / CORRECT_SLOPPY / WRONG_FORM / WRONG) instead of naive string comparison. Three NLP backends must be implemented behind a `BaseNLP` abstract interface using a Strategy + Registry pattern.

The key libraries are well-verified: **pymorphy3 2.0.6** (Russian, actively maintained, Python 3.9-3.13), **camel-tools 1.5.7** (Arabic MSA, Python 3.8-3.12, requires Rust compiler and CMake), and **spaCy 3.7+** with **lemminflect 0.2.3** (English). The `AnswerResult` enum already exists in `backend/services/srs.py` and must be relocated to the NLP base module (or imported from a shared location) since both SRS and NLP layers depend on it.

**Primary recommendation:** Build the NLP layer as `backend/services/nlp/` with `base.py` (BaseNLP ABC + shared validation pipeline), `russian.py`, `arabic.py`, `english.py`, and `__init__.py` (registry). All backends are sync, CPU-bound, loaded once at startup, called via `asyncio.to_thread()` from async context. Use `camel_data -i light` (not `all`) to minimize model size for Arabic.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NLP-01 | BaseNLP abstract interface with normalize, lemmatize, get_morphological_family, get_aspect_partner, check_answer | Strategy pattern with ABC; 4-tier check_answer in base class with language-specific overrides |
| NLP-02 | 4-tier answer validation returning AnswerResult enum | Base `check_answer` implements exact -> normalized -> lemma -> morphological family pipeline; AnswerResult already exists in srs.py |
| NLP-03 | Russian NLP backend (pymorphy3) with morphological analysis, lemmatization, case/gender/aspect detection | pymorphy3 2.0.6 provides `MorphAnalyzer.parse()` -> lexeme, normal_form, tag (case, gender, aspect) |
| NLP-04 | Russian Latin-to-Cyrillic transliteration as CORRECT_SLOPPY | cyrtranslit or transliterate library; check before calling super().check_answer() |
| NLP-05 | Russian aspect partner detection returns WRONG_FORM with explanation | pymorphy3 does NOT provide aspect pairs; must build lookup from card_context morphology JSONB or a hardcoded table |
| NLP-06 | Arabic NLP backend (camel-tools) with tashkeel stripping, alef normalization, root extraction | camel-tools 1.5.7: `dediac_ar()`, `normalize_alef_ar()`, Analyzer returns `root`, `lex`, `pos` keys |
| NLP-07 | Arabic answer validation never fails on diacritic presence/absence | `dediac_ar()` applied in normalize() ensures diacritics are stripped before comparison |
| NLP-08 | Arabic verb form detection returns WRONG_FORM with root + form table | Analyzer returns `root` and pattern fields; compare verb forms from analysis, show form table from card_context |
| NLP-09 | English NLP backend (spaCy) with lemmatization, article stripping, irregular verb handling | spaCy en_core_web_sm for lemmatization + lemminflect 0.2.3 for correct inflection generation |
| NLP-10 | Answer alternatives array checked before returning WRONG | Layer 6 in base check_answer pipeline; reads `answer_alternatives` from card_context dict |
</phase_requirements>

## Standard Stack

### Core NLP Libraries

| Library | Version | Purpose | Why Standard | Confidence |
|---------|---------|---------|--------------|------------|
| pymorphy3 | 2.0.6 | Russian morphological analysis | Active fork of pymorphy2, supports Python 3.9-3.13, MIT license, ~30MB memory, local-only (no API quota) | HIGH |
| camel-tools | 1.5.7 | Arabic NLP (MSA morphology, root extraction, normalization) | Most comprehensive open-source Arabic NLP toolkit, maintained by CAMeL Lab at NYU Abu Dhabi | HIGH |
| spaCy | >=3.7 | English NLP (lemmatization, POS tagging) | Industry standard, `en_core_web_sm` is 12MB, only need lemma + POS | HIGH |
| lemminflect | 0.2.3 | English inflection generation | Correct inflections from spaCy tokens (95.6% accuracy), handles irregular verbs/nouns properly | HIGH |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cyrtranslit | >=1.2 | Latin-to-Cyrillic transliteration | Russian transliteration fallback in check_answer (NLP-04) |
| unicodedata (stdlib) | - | NFC normalization | First step in every check_answer call, before any language-specific logic |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| cyrtranslit | transliterate library | transliterate is bidirectional but cyrtranslit is simpler and purpose-built for Cyrillic |
| lemminflect | pyinflect | pyinflect is older, lemminflect is its successor with better accuracy |
| camel-tools Analyzer | camel-tools MLE Disambiguator | MLE disambiguator uses sentence context for better analysis selection (95.4% lemma accuracy) but requires full sentence, not just a word. Use Analyzer for single-word analysis, consider MLE for sentence-level tasks later |
| spaCy en_core_web_sm | en_core_web_md/lg | Larger models add NER and word vectors we do not need; sm is sufficient for lemmatization |

**Installation:**
```bash
# NLP core
pip install pymorphy3 camel-tools spacy lemminflect cyrtranslit

# Download models
python -m spacy download en_core_web_sm
camel_data -i light  # morphology + MLE disambiguation only (~300-500MB, not 1.5GB)
```

**CRITICAL: camel-tools requires Python <=3.12.** The project must use Python 3.11 or 3.12 (not 3.13+). camel-tools also requires Rust compiler, CMake, and Boost as build dependencies.

## Architecture Patterns

### Recommended Project Structure

```
backend/
  services/
    srs.py                   # Existing SM-2 algorithm (keep AnswerResult here or move)
    nlp/
      __init__.py            # NLP_BACKENDS registry, get_nlp(), init_nlp_backends()
      base.py                # BaseNLP ABC + 4-tier check_answer pipeline
      russian.py             # RussianNLP (pymorphy3 + cyrtranslit)
      arabic.py              # ArabicNLP (camel-tools)
      english.py             # EnglishNLP (spaCy + lemminflect)
  tests/
    test_nlp_russian.py      # Russian backend unit tests
    test_nlp_arabic.py       # Arabic backend unit tests
    test_nlp_english.py      # English backend unit tests
    test_nlp_base.py         # Base pipeline integration tests
```

### Pattern 1: BaseNLP Abstract Interface with Template Method

**What:** Abstract base class defines the 4-tier validation pipeline in `check_answer()`. Language backends implement the abstract methods (`normalize`, `lemmatize`, `get_morphological_family`, `get_aspect_partner`) and optionally override `check_answer()` for language-specific pre-checks.

**When to use:** Always. This is the core pattern for the entire NLP layer.

**Example:**
```python
# backend/services/nlp/base.py
from abc import ABC, abstractmethod
from enum import Enum
import unicodedata

class AnswerResult(Enum):
    CORRECT = "correct"
    CORRECT_SLOPPY = "correct_sloppy"
    WRONG_FORM = "wrong_form"
    WRONG = "wrong"

class BaseNLP(ABC):
    @abstractmethod
    def normalize(self, text: str) -> str:
        """Language-specific normalization."""
        ...

    @abstractmethod
    def lemmatize(self, word: str) -> str:
        """Return dictionary/canonical form."""
        ...

    @abstractmethod
    def get_morphological_family(self, word: str) -> set[str]:
        """All inflected forms sharing the same lemma."""
        ...

    @abstractmethod
    def get_aspect_partner(self, verb: str) -> str | None:
        """Return aspect partner (Russian-meaningful; others return None)."""
        ...

    def check_answer(
        self,
        user_input: str,
        correct_answer: str,
        card_context: dict | None = None,
    ) -> tuple[AnswerResult, str | None]:
        ctx = card_context or {}
        user = unicodedata.normalize("NFC", user_input.strip())
        correct = unicodedata.normalize("NFC", correct_answer.strip())

        # Layer 1: Exact match
        if user == correct:
            return AnswerResult.CORRECT, None

        # Layer 2: Normalized match
        if self.normalize(user) == self.normalize(correct):
            return AnswerResult.CORRECT, None

        # Layer 3: Lemma match
        if self.lemmatize(user) == self.lemmatize(correct):
            return AnswerResult.CORRECT_SLOPPY, f"Correct word, check the exact form needed."

        # Layer 4: Morphological family
        family = self.get_morphological_family(correct)
        if self.normalize(user) in {self.normalize(f) for f in family}:
            return AnswerResult.CORRECT_SLOPPY, "Correct word, different inflection."

        # Layer 5: Aspect partner (Russian verbs)
        partner = self.get_aspect_partner(correct)
        if partner and self.normalize(user) == self.normalize(partner):
            return AnswerResult.WRONG_FORM, "Wrong aspect — this sentence needs the other form."

        # Layer 6: Explicit alternatives from card_context
        alternatives = ctx.get("answer_alternatives", [])
        for alt in alternatives:
            if self.normalize(user) == self.normalize(alt):
                return AnswerResult.CORRECT, None

        return AnswerResult.WRONG, None
```

### Pattern 2: Singleton Registry with Startup Loading

**What:** NLP backends are instantiated once at application startup (heavy model loading) and stored in a dict registry. `get_nlp(language_code)` retrieves the backend.

**Example:**
```python
# backend/services/nlp/__init__.py
from .base import BaseNLP

NLP_BACKENDS: dict[str, BaseNLP] = {}

def init_nlp_backends():
    from .russian import RussianNLP
    from .arabic import ArabicNLP
    from .english import EnglishNLP
    NLP_BACKENDS["ru"] = RussianNLP()
    NLP_BACKENDS["ar"] = ArabicNLP()
    NLP_BACKENDS["en"] = EnglishNLP()

def get_nlp(language_code: str) -> BaseNLP:
    if language_code not in NLP_BACKENDS:
        raise ValueError(f"No NLP backend for language: {language_code}")
    return NLP_BACKENDS[language_code]
```

Wire into `main.py` lifespan:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_pool(settings.database_url)
    init_nlp_backends()  # Add this line
    yield
    await close_pool()
```

### Pattern 3: Sync NLP + asyncio.to_thread Bridge

**What:** All NLP methods are synchronous. When called from async FastAPI endpoints, use `asyncio.to_thread()`.

**Example:**
```python
import asyncio

async def validate_answer_async(
    language_code: str,
    user_input: str,
    correct_answer: str,
    card_context: dict | None = None,
) -> tuple[AnswerResult, str | None]:
    nlp = get_nlp(language_code)
    return await asyncio.to_thread(
        nlp.check_answer, user_input, correct_answer, card_context
    )
```

### Pattern 4: Russian Transliteration Pre-check Override

**What:** RussianNLP overrides `check_answer()` to try Latin-to-Cyrillic transliteration before falling through to the base pipeline.

**Example:**
```python
# backend/services/nlp/russian.py
import cyrtranslit

class RussianNLP(BaseNLP):
    def check_answer(self, user_input, correct_answer, card_context=None):
        # Try transliteration if input looks Latin
        user_stripped = user_input.strip()
        if user_stripped.isascii() and not user_stripped.isdigit():
            cyrillic = cyrtranslit.to_cyrillic(user_stripped, "ru")
            if self.normalize(cyrillic) == self.normalize(correct_answer.strip()):
                return AnswerResult.CORRECT_SLOPPY, "Correct! Use Cyrillic next time."
        # Fall through to standard pipeline
        return super().check_answer(user_input, correct_answer, card_context)
```

### Anti-Patterns to Avoid

- **Async NLP backends:** pymorphy3, camel-tools, and spaCy are all synchronous CPU-bound. Making them async adds confusion with no benefit and risks deadlocks.
- **Per-request model loading:** Loading MorphAnalyzer or spacy model per request adds 50ms-5s latency. Load once at startup.
- **Taking analyses[0] blindly from camel-tools:** The first analysis is not necessarily the most likely. Use `pos_lex_logprob` to rank analyses, or prefer the analysis matching the card's stored POS/morphology.
- **Normalizing taa marbuta unconditionally:** Taa marbuta to ha normalization conflates genuinely different words. Treat as CORRECT_SLOPPY, not CORRECT.
- **Naive English inflection with string concatenation:** `lemma + 'ed'` produces "goed", "runed". Use lemminflect.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Russian morphological analysis | Custom rule-based analyzer | pymorphy3 `MorphAnalyzer` | 400k+ word dictionary with inflection rules, handles all 6 cases, 3 genders, aspect detection |
| Arabic diacritics stripping | Manual Unicode range filtering | camel-tools `dediac_ar()` | Handles all Arabic combining marks correctly, tested against MSA corpus |
| Arabic alef normalization | Manual char replacement | camel-tools `normalize_alef_ar()` | Handles all alef variants (hamza above, hamza below, madda) correctly |
| English irregular inflections | String concatenation rules | lemminflect `getAllInflections()` | Dictionary-backed + neural network OOV handling; 95.6% accuracy vs. 0% for naive rules on irregulars |
| Latin-to-Cyrillic transliteration | Manual character mapping dict | cyrtranslit `to_cyrillic()` | Handles ambiguous mappings (sh -> sh, ch -> ch, etc.) with standard Russian transliteration rules |
| Unicode normalization | Skipping it | `unicodedata.normalize('NFC', text)` | Invisible codepoint differences cause "correct answers marked wrong" — the most frustrating user experience bug |

**Key insight:** Every NLP operation looks simple until you hit the edge cases. Russian has 6 cases x 3 genders x 2 numbers x 2 animacy values = 72 noun forms. Arabic has 10+ verb forms each with full conjugation tables. English has 200+ irregular verbs. Libraries encode decades of linguistic knowledge.

## Common Pitfalls

### Pitfall 1: Unicode NFC Normalization Missing
**What goes wrong:** Cyrillic `a` (U+0430) looks identical to Latin `a` (U+0061). Arabic text from different sources may be NFC or NFD encoded. Copy-pasted text has invisible differences.
**Why it happens:** Users switch keyboards, copy from Google Translate, paste from WhatsApp.
**How to avoid:** Apply `unicodedata.normalize('NFC', text)` as the FIRST step in every `check_answer` call, before any language-specific logic. Also apply to all stored correct answers.
**Warning signs:** Users report "I typed the exact right answer and it said wrong."

### Pitfall 2: pymorphy3 Has No Aspect Partner Data
**What goes wrong:** `get_aspect_partner()` returns None for every verb because pymorphy3 simply does not contain aspect pair information. Russian aspect checking (NLP-05) silently breaks -- all aspect-wrong answers fall through to WRONG instead of WRONG_FORM.
**Why it happens:** pymorphy3 is a morphological analyzer, not a lexical database. Aspect pairs are a lexical relationship, not a morphological one.
**How to avoid:** Aspect partner data must come from `card_context` (the `morphology` JSONB field on vocabulary records). The vocabulary table should store `{"aspect": "impf", "aspect_partner": "napisat"}` in its morphology field. `get_aspect_partner()` should accept card_context and look up the partner there, or maintain a small hardcoded lookup table for the most common pairs.
**Warning signs:** Test with "pisat" when "napisat" is expected -- if result is WRONG instead of WRONG_FORM, aspect detection is broken.

### Pitfall 3: camel-tools Analyzer Returns Multiple Ambiguous Analyses
**What goes wrong:** `analyzer.analyze(word)` returns 5-15 possible analyses for ambiguous Arabic words. Taking `analyses[0]` picks an arbitrary interpretation.
**Why it happens:** Arabic is highly ambiguous without diacritics. The same consonantal skeleton can be multiple words.
**How to avoid:** (1) When card_context includes expected POS, filter analyses to match. (2) Use `pos_lex_logprob` score to rank analyses by likelihood. (3) For root extraction, if card_context includes the expected root, verify against it rather than trusting the top analysis.
**Warning signs:** Arabic answer validation returns wrong grammatical feedback for ambiguous words.

### Pitfall 4: camel-tools Requires Python <=3.12
**What goes wrong:** `pip install camel-tools` fails on Python 3.13+ with build errors from camel-kenlm dependency.
**Why it happens:** camel-tools explicitly declares `python_requires='>=3.8.0,<3.13'`. The camel-kenlm C extension has not been updated for 3.13.
**How to avoid:** Pin project to Python 3.11 or 3.12. Document this constraint in the project.
**Warning signs:** CI builds fail with "no matching distribution found" or C compilation errors.

### Pitfall 5: camel-tools Build Dependencies
**What goes wrong:** `pip install camel-tools` fails even on Python 3.12 because system dependencies are missing.
**Why it happens:** camel-tools depends on camel-kenlm which requires a C/C++ compiler, CMake, and Boost. The Rust compiler is also needed.
**How to avoid:** In Docker: `apt-get install -y build-essential cmake libboost-all-dev`. On macOS: `brew install cmake boost`. Document these prerequisites.
**Warning signs:** Compilation errors mentioning "kenlm", "cmake", or "boost".

### Pitfall 6: Taa Marbuta Over-Normalization
**What goes wrong:** Blanket normalization of taa marbuta (U+0629) to ha (U+0647) makes semantically different words indistinguishable.
**Why it happens:** The answer-validation-spec normalizes taa marbuta in `normalize()`. This is too aggressive.
**How to avoid:** Do NOT normalize taa marbuta in the primary `normalize()` method. Instead, add a secondary fallback: if the only difference is taa marbuta vs ha, return CORRECT_SLOPPY with a note. This preserves the distinction for exact matching while being forgiving.

### Pitfall 7: AnswerResult Enum Location Conflict
**What goes wrong:** AnswerResult is currently defined in `backend/services/srs.py`. The NLP layer also needs it. If both define it separately, they are different types and comparisons break.
**Why it happens:** Phase 1 put AnswerResult in srs.py because that's where quality mapping lives.
**How to avoid:** Either (a) move AnswerResult to `backend/services/nlp/base.py` and import it in srs.py, or (b) create a shared `backend/services/enums.py` module. Option (a) is more natural since AnswerResult is semantically an NLP concept that the SRS layer consumes.

## Code Examples

### Russian Backend -- pymorphy3 Core API

```python
# Source: pymorphy3 documentation + PyPI
import pymorphy3

morph = pymorphy3.MorphAnalyzer()

# Parse returns a list of possible analyses, sorted by score
parsed = morph.parse("собаку")
# parsed[0].normal_form -> "собака"
# parsed[0].tag -> OpencorporaTag('NOUN,anim,femn sing,accs')
# parsed[0].tag.case -> 'accs' (accusative)
# parsed[0].tag.gender -> 'femn' (feminine)
# parsed[0].tag.POS -> 'NOUN'

# Get all inflected forms (lexeme)
lexeme = parsed[0].lexeme
forms = {form.word for form in lexeme}
# {'собака', 'собаки', 'собаке', 'собаку', 'собакой', 'собак', ...}
```

### Arabic Backend -- camel-tools Core API

```python
# Source: camel-tools documentation (camel-tools.readthedocs.io)
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
from camel_tools.utils.dediac import dediac_ar
from camel_tools.utils.normalize import normalize_alef_ar

db = MorphologyDB.builtin_db()  # loads calima-msa-r13 by default
analyzer = Analyzer(db, backoff='NOAN_PROP')

analyses = analyzer.analyze("كَتَبَ")
# Each analysis is a dict with keys:
# 'root': 'ك.ت.ب'
# 'lex': 'كَتَب_1'   (lemma with sense ID)
# 'pos': 'verb'
# 'asp': 'p'          (perfective)
# 'gen': 'm'          (masculine)
# 'num': 's'          (singular)
# 'per': '3'          (third person)
# 'vox': 'a'          (active)
# 'pos_lex_logprob': -1.234  (ranking score)

# Normalization
dediac_ar("كَتَبَ")     # -> "كتب" (strip all diacritics)
normalize_alef_ar("أكتب")  # -> "اكتب" (normalize hamza-on-alef to bare alef)
```

### English Backend -- spaCy + lemminflect

```python
# Source: spaCy docs + lemminflect docs
import spacy
import lemminflect  # registers spaCy extensions on import

nlp = spacy.load("en_core_web_sm")

# Lemmatization
doc = nlp("went")
doc[0].lemma_  # -> "go"

# Inflection generation (via lemminflect)
from lemminflect import getAllInflections, getInflection

getAllInflections("go", upos="VERB")
# {'VB': ('go',), 'VBD': ('went',), 'VBG': ('going',),
#  'VBN': ('gone',), 'VBP': ('go',), 'VBZ': ('goes',)}

getInflection("mouse", tag="NNS")
# ('mice',)

# From spaCy token (after importing lemminflect)
doc = nlp("go")
doc[0]._.inflect("VBD")  # -> "went"
```

### Transliteration -- cyrtranslit

```python
# Source: cyrtranslit PyPI
import cyrtranslit

cyrtranslit.to_cyrillic("da", "ru")      # -> "да"
cyrtranslit.to_cyrillic("sobaka", "ru")   # -> "собака"
cyrtranslit.to_latin("собака", "ru")      # -> "sobaka"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pymorphy2 (unmaintained) | pymorphy3 2.0.6 (active fork) | 2023 | Python 3.11-3.13 support, active maintenance |
| Manual Arabic normalization | camel-tools `dediac_ar` + `normalize_*` | Stable | Handles all combining marks correctly |
| Naive English inflection (string concat) | lemminflect (dictionary + neural OOV) | 2019+ | 95.6% accuracy vs ~60% for naive rules |
| `transliterate` library | cyrtranslit (simpler, purpose-built) | Stable | Cleaner API for bidirectional Cyrillic transliteration |

**Deprecated/outdated:**
- pymorphy2: Does not support Python 3.11+. Use pymorphy3.
- `camel_data -i all`: Downloads 1.5GB+. Use `camel_data -i light` for morphology + MLE only.
- spaCy en_core_web_md/lg: Unnecessary for this use case. en_core_web_sm suffices.

## Open Questions

1. **camel-tools `light` data exact size**
   - What we know: `light` includes morphology + MLE disambiguation only, much smaller than `all` (~1.5GB)
   - What's unclear: Exact GB size of `light` install
   - Recommendation: Test with `camel_data -i light` during initial setup and measure. Expect 300-500MB.

2. **pymorphy3 thread safety**
   - What we know: pymorphy2 docs recommend single shared instance. pymorphy3 continues this pattern.
   - What's unclear: No explicit thread safety documentation for pymorphy3 MorphAnalyzer.
   - Recommendation: Treat as read-only (analysis is stateless lookup). The `run_in_executor`/`to_thread` approach uses the default ThreadPoolExecutor which serializes via GIL for CPU-bound work anyway. LOW risk.

3. **Aspect partner data source**
   - What we know: pymorphy3 does not provide aspect pairs. OpenRussian TSV has `aspect_partner_id` column.
   - What's unclear: Whether Phase 3 (seed data) must run before aspect detection works in Phase 2.
   - Recommendation: For Phase 2, `get_aspect_partner()` should read from `card_context["morphology"]["aspect_partner"]`. This means aspect detection works when cards have this data populated (Phase 3+), but the interface and pipeline are ready now. Add a small hardcoded test fixture for testing.

4. **Arabic verb form detection depth**
   - What we know: camel-tools analyzer returns root and pattern. Arabic has 10 verb forms (I-X).
   - What's unclear: Whether the analyzer's pattern field reliably maps to traditional verb form numbers.
   - Recommendation: For Phase 2, implement basic form detection using the `root` field comparison. If two words share the same root but different patterns, return WRONG_FORM. Detailed form table display (Form I, II, III...) can use card_context morphology data.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio |
| Config file | None -- uses existing `backend/tests/conftest.py` |
| Quick run command | `python -m pytest backend/tests/test_nlp_*.py -x -q` |
| Full suite command | `python -m pytest backend/tests/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NLP-01 | BaseNLP interface exists, all 3 backends registered and callable | unit | `python -m pytest backend/tests/test_nlp_base.py -x` | Wave 0 |
| NLP-02 | 4-tier validation returns correct AnswerResult per tier | unit | `python -m pytest backend/tests/test_nlp_base.py::TestCheckAnswerPipeline -x` | Wave 0 |
| NLP-03 | Russian backend morphological analysis, lemmatization | unit | `python -m pytest backend/tests/test_nlp_russian.py -x` | Wave 0 |
| NLP-04 | Russian Latin-to-Cyrillic transliteration returns CORRECT_SLOPPY | unit | `python -m pytest backend/tests/test_nlp_russian.py::TestTransliteration -x` | Wave 0 |
| NLP-05 | Russian aspect partner detection returns WRONG_FORM | unit | `python -m pytest backend/tests/test_nlp_russian.py::TestAspectPartner -x` | Wave 0 |
| NLP-06 | Arabic backend tashkeel stripping, alef normalization, root extraction | unit | `python -m pytest backend/tests/test_nlp_arabic.py -x` | Wave 0 |
| NLP-07 | Arabic never fails on diacritic presence/absence | unit | `python -m pytest backend/tests/test_nlp_arabic.py::TestDiacriticInvariance -x` | Wave 0 |
| NLP-08 | Arabic verb form detection returns WRONG_FORM with root | unit | `python -m pytest backend/tests/test_nlp_arabic.py::TestVerbFormDetection -x` | Wave 0 |
| NLP-09 | English lemmatization, article stripping, irregular verb handling | unit | `python -m pytest backend/tests/test_nlp_english.py -x` | Wave 0 |
| NLP-10 | Answer alternatives checked before WRONG | unit | `python -m pytest backend/tests/test_nlp_base.py::TestAlternatives -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest backend/tests/test_nlp_*.py -x -q`
- **Per wave merge:** `python -m pytest backend/tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_nlp_base.py` -- covers NLP-01, NLP-02, NLP-10
- [ ] `backend/tests/test_nlp_russian.py` -- covers NLP-03, NLP-04, NLP-05
- [ ] `backend/tests/test_nlp_arabic.py` -- covers NLP-06, NLP-07, NLP-08
- [ ] `backend/tests/test_nlp_english.py` -- covers NLP-09
- [ ] NLP library dependencies must be installed: `pip install pymorphy3 camel-tools spacy lemminflect cyrtranslit && python -m spacy download en_core_web_sm && camel_data -i light`

## Sources

### Primary (HIGH confidence)
- [pymorphy3 PyPI](https://pypi.org/project/pymorphy3/) - version 2.0.6, Python 3.9-3.13 support confirmed
- [camel-tools PyPI](https://pypi.org/project/camel-tools/) - version 1.5.7, Python 3.8-3.12
- [camel-tools Morphology Analyzer docs](https://camel-tools.readthedocs.io/en/stable/api/morphology/analyzer.html) - Analyzer API, analyze() returns list of dict
- [camel-tools MorphologyDB docs](https://camel-tools.readthedocs.io/en/stable/api/morphology/database.html) - builtin_db(), calima-msa-r13 default
- [camel-tools Morphology Features reference](https://camel-tools.readthedocs.io/en/stable/reference/camel_morphology_features.html) - root, lex, pos, asp, gen, num, cas keys
- [camel-tools normalize utils docs](https://camel-tools.readthedocs.io/en/stable/api/utils/normalize.html) - normalize_alef_ar, normalize_teh_marbuta_ar
- [lemminflect docs](https://lemminflect.readthedocs.io/en/latest/inflections/) - inflection API, spaCy integration, POS tags
- [lemminflect PyPI](https://pypi.org/project/lemminflect/) - version 0.2.3, 95.6% accuracy
- [spaCy Universe - lemminflect](https://spacy.io/universe/project/lemminflect) - spaCy extension integration
- [cyrtranslit PyPI](https://pypi.org/project/cyrtranslit/) - bidirectional Cyrillic transliteration

### Secondary (MEDIUM confidence)
- [camel-tools MLE disambiguator docs](https://camel-tools.readthedocs.io/en/latest/api/disambig/mle.html) - MLEDisambiguator.pretrained(), 95.4% lemma accuracy on MSA
- [camel-tools GitHub](https://github.com/CAMeL-Lab/camel_tools) - project health, release cadence

### Tertiary (LOW confidence)
- pymorphy3 thread safety -- no explicit documentation found; inferred from pymorphy2 patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries verified on PyPI with current versions and Python compatibility
- Architecture: HIGH - Strategy + Registry pattern is well-established and already documented in ARCHITECTURE.md
- Pitfalls: HIGH - Unicode normalization, camel-tools build deps, aspect partner gap are well-documented
- Arabic API details: MEDIUM - analysis dict keys verified via docs but exact behavior with edge cases needs live testing

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (stable libraries, 30-day window)
