"""
KoreanNLP backend — rule-based particle + verb-ending handling (WP27).

Korean is agglutinative like Turkish, but the machinery differs in two
ways this backend has to care about:

  - Nouns carry POSTPOSITION PARTICLES fused into the same orthographic
    word: 학교에 = 학교 "school" + 에 "at". Answer checking and the
    seeder's lemma folding both need 학교에 to fold onto 학교.
  - Verbs and adjectives conjugate off a stem; the dictionary form ends
    in 다 (가다 "to go"), while running text shows 가요/갑니다/갔어요.
    De-conjugation is genuinely irregular (vowel contraction, ㅂ/ㄷ/르
    stems), so the heuristic here is deliberately conservative: strip the
    unambiguous polite/past endings, reattach 다, and otherwise leave the
    word alone. Wrong-but-safe beats clever-but-leaky — the seeder only
    folds onto headwords that actually exist, and check_answer grades a
    lemma match as CORRECT_SLOPPY, never CORRECT.

No external morphology library: konlpy needs a JVM and mecab-ko needs a
system dictionary — both unreasonable for the deploy. The heuristics
cover the frequency band the app actually teaches.
"""
from __future__ import annotations

import re

from backend.services.nlp.base import BaseNLP

_HANGUL_RE = re.compile(r"[가-힣]")

# Multi-syllable particles are unambiguous — no real noun ends in these
# as part of its own material often enough to matter. Longest first.
_MULTI_PARTICLES = (
    "에서부터", "으로부터",
    "에게서", "한테서", "에서는", "에서도", "까지는", "부터는",
    "이라고", "이라는", "이라도", "이라면",
    "에서", "에게", "한테", "께서", "부터", "까지", "처럼", "보다",
    "마다", "조차", "밖에", "으로", "이나", "이랑", "하고", "라고",
)

# Single-syllable particles: stripped only when at least two syllables
# remain, which keeps 집에 → 집 but leaves two-syllable nouns that merely
# END in a particle-shaped syllable (종이 "paper", 고기 "meat") intact
# more often than not.
_SINGLE_PARTICLES = ("는", "은", "를", "을", "가", "이", "도", "만", "의", "에", "와", "과", "로", "랑", "요")

# Polite/past verb endings → reattach 다. Longest first; the stem keeps
# whatever contraction it has (가요 → 가다 works; 마셔요 → 마셔다 would
# not, so contracted vowels are simply not in this table beyond 해/했).
_VERB_ENDINGS = (
    ("했습니다", "하다"),
    ("합니다", "하다"),
    ("했어요", "하다"),
    ("해요", "하다"),
    ("하다", "하다"),
    ("았습니다", "다"),
    ("었습니다", "다"),
    ("습니다", "다"),
    ("았어요", "다"),
    ("었어요", "다"),
    ("아요", "다"),
    ("어요", "다"),
    ("네요", "다"),
    ("지요", "다"),
    ("죠", "다"),
)

_MIN_STEM_SYLLABLES = 1

# Hangul syllable arithmetic: code = 0xAC00 + (initial*21 + medial)*28 + final.
_HANGUL_BASE = 0xAC00
_HANGUL_LAST = 0xD7A3
_FINAL_BIEUP = 17  # ㅂ as a final consonant


def _hangul_len(word: str) -> int:
    return len(_HANGUL_RE.findall(word))


def _drop_final_bieup(ch: str) -> str | None:
    """가+ㅂ (갑) → 가; None when *ch* has no ㅂ final.

    The formal present ending ㅂ니다 fuses its ㅂ into the stem's last
    syllable (가다 → 갑니다), so plain string suffix matching never sees it.
    """
    code = ord(ch)
    if not (_HANGUL_BASE <= code <= _HANGUL_LAST):
        return None
    if (code - _HANGUL_BASE) % 28 == _FINAL_BIEUP:
        return chr(code - _FINAL_BIEUP)
    return None


class KoreanNLP(BaseNLP):
    """Korean NLP backend (particle-aware, conservative de-conjugation)."""

    def normalize(self, text: str) -> str:
        # Hangul has no case; lower() covers mixed-in Latin (loanword
        # answers typed in ASCII).
        return text.strip().lower()

    def lemmatize(self, word: str) -> str:
        w = self.normalize(word)
        if not w or not _HANGUL_RE.search(w):
            return w

        # Verb/adjective endings first — they are longer and more
        # specific than any particle.
        for ending, repl in _VERB_ENDINGS:
            if w.endswith(ending):
                stem = w[: -len(ending)]
                if ending in ("했습니다", "합니다", "했어요", "해요", "하다"):
                    candidate = stem + repl
                else:
                    candidate = stem + repl if stem else w
                if _hangul_len(candidate) >= _MIN_STEM_SYLLABLES + 1:
                    return candidate

        # Formal present ㅂ니다: the ㅂ hides inside the stem's last
        # syllable (갑니다 → 가다). Checked after the literal table so
        # 습니다-forms take their own row first.
        if w.endswith("니다") and len(w) >= 3:
            restored = _drop_final_bieup(w[-3])
            if restored is not None:
                return w[:-3] + restored + "다"

        for p in _MULTI_PARTICLES:
            if w.endswith(p) and _hangul_len(w[: -len(p)]) >= _MIN_STEM_SYLLABLES:
                return w[: -len(p)]

        for p in _SINGLE_PARTICLES:
            if w.endswith(p) and _hangul_len(w[: -len(p)]) >= 2:
                return w[: -len(p)]
        # 집에 → 집: allow a single-syllable remainder for the locative
        # particles only, where the reading is nearly always particle.
        for p in ("에", "은", "는", "을", "를", "가"):
            if w.endswith(p) and _hangul_len(w[: -len(p)]) == 1:
                return w[: -len(p)]

        return w

    def get_morphological_family(self, word: str) -> set[str]:
        w = self.normalize(word)
        lemma = self.lemmatize(w)
        family: set[str] = {w, lemma}
        if lemma.endswith("다") and _hangul_len(lemma) >= 2:
            stem = lemma[:-1]
            family.update({stem + "아요", stem + "어요", stem + "습니다"})
        else:
            for p in ("는", "은", "를", "을", "가", "이", "도", "에"):
                family.add(lemma + p)
        return family

    def get_aspect_partner(
        self,
        verb: str,
        card_context: dict | None = None,
    ) -> str | None:
        """Korean has no Slavic-style aspect pairs — always None."""
        return None
