"""Korean → Latin reading (Revised Romanization of Korean, RR).

The `ko` seeder deferred this — "Revised-Romanization can be generated later
if native reviewers want it" — and the course shipped 7,214 words and 3,897
sentences with nothing a learner could sound out. Hangul is the one script in
this corpus a learner cannot even guess at: the letters are unrelated to Latin
and the syllable block hides its own segmentation.

RR is TRANSCRIPTION, so the hard part is not the letter table — it is that
Korean spells morphemes and pronounces something else. 신라 is spelled sin-la
and said *Silla*; 학년 is spelled hak-nyeon and said *hangnyeon*; 좋다 is
spelled joh-da and said *jota*. A syllable-by-syllable mapping gets the letter
table perfectly right and the word wrong, which is the failure a learner
cannot detect. So the boundary between every pair of syllables goes through
the assimilation table below.

Scope, stated plainly: this implements the regular sound changes RR specifies
— liaison, nasal assimilation, lateralisation, aspiration and tensing across
a syllable boundary. It does NOT implement the parts of Korean pronunciation
that need morphology or a lexicon: RR's optional hyphenation, the sai-siot,
and the vowel-length and compound-boundary distinctions that separate 감사
*gamsa* from cases where a boundary blocks assimilation. Those need a native
reviewer, as the seeder said. What is here is the layer that is right far
more often than no layer at all, and every rule it applies is one RR states.
"""
from __future__ import annotations

BASE = 0xAC00
LAST = 0xD7A3

# The 19 syllable-initial consonants, in Unicode order.
ONSET = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "",
         "j", "jj", "ch", "k", "t", "p", "h"]

# The 21 vowels.
VOWEL = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae",
         "oe", "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i"]

# The 28 finals (index 0 = no final). These are the RELEASED values used when
# nothing follows; before a vowel the coda re-links instead (see CODA_ONSET).
CODA = ["", "k", "k", "k", "n", "n", "n", "t", "l", "k", "m", "l", "l", "l",
        "p", "l", "m", "p", "p", "t", "t", "ng", "t", "t", "k", "t", "p", "t"]

# What a coda becomes when it moves into the next syllable's empty onset.
# Korean neutralises codas when released but restores the underlying consonant
# on liaison: 옷이 is *osi*, not *oti*, though 옷 alone is *ot*. A cluster
# splits — 읽어 is *ilgeo*: the ㄹ stays put and only the ㄱ moves across.
CODA_ONSET = {
    1: "g", 2: "kk", 3: ("k", "s"), 4: "n", 5: ("n", "j"), 6: "n",
    7: "d", 8: "r", 9: ("l", "g"), 10: ("l", "m"), 11: ("l", "b"),
    12: ("l", "s"), 13: ("l", "t"), 14: ("l", "p"), 15: "r",
    16: "m", 17: "b", 18: ("p", "s"), 19: "s", 20: "ss", 21: "ng",
    22: "j", 23: "ch", 24: "k", 25: "t", 26: "p",
    # ㅎ is the exception: it does not re-link, it DISAPPEARS before a vowel.
    # 좋아요 is *joayo*, not *johayo*.
    27: "",
}

# Palatalisation (구개음화): a ㄷ or ㅌ coda meeting 이 is not *ti* but *chi* —
# 같이 *gachi*, 해돋이 *haedoji*, 굳히다 *guchida*. Keyed by (coda, onset).
PALATALISE = {(7, 11): "j", (25, 11): "ch", (7, 18): "ch", (25, 18): "ch"}
# The vowels that trigger it: ㅣ and the y-glides that begin with the same
# high front position.
PALATAL_VOWELS = {20, 2, 6, 12, 17, 3, 7}

# Coda index -> the sound it actually ends on, for the assimilation table.
CODA_SOUND = {i: c for i, c in enumerate(CODA)}

# (coda sound, next onset letter) -> (replacement coda, replacement onset).
# Only the regular changes RR states; everything absent falls through
# unchanged, which is the common case.
ASSIMILATION: dict[tuple[str, str], tuple[str, str]] = {}
for _coda, _repl in (("k", "ng"), ("p", "m"), ("t", "n")):
    # Obstruent before a nasal becomes the matching nasal: 학년 hangnyeon,
    # 입니다 imnida, 닫는 danneun.
    for _onset in ("n", "m"):
        ASSIMILATION[(_coda, _onset)] = (_repl, _onset)
    # ...and before ㄹ, which itself becomes n: 백리 baengni.
    ASSIMILATION[(_coda, "r")] = (_repl, "n")
# ㄴ + ㄹ and ㄹ + ㄴ both give ll: 신라 Silla, 설날 seollal.
ASSIMILATION[("n", "r")] = ("l", "l")
ASSIMILATION[("l", "n")] = ("l", "l")
# ...and so does ㄹ + ㄹ itself, which is the sequence RR names by hand —
# "ㄹㄹ is written ll", as in 울릉도 Ulleungdo and 대관령 Daegwallyeong. Having
# the two rules that ASSIMILATE INTO this geminate without having the geminate
# itself produced `lr`, a string RR can never emit: 텔레비전 *telrebijeon* for
# *tellebijeon*, 몰라 *molra* for *molla*, 정말로 *jeongmalro* for *jeongmallo*.
ASSIMILATION[("l", "r")] = ("l", "l")
# A nasal or ㄹ coda turns a following ㄹ into n: 종로 Jongno, 심리 simni.
for _coda in ("ng", "m"):
    ASSIMILATION[(_coda, "r")] = (_coda, "n")

# The three codas that CONTAIN ㅎ, mapped to what is left of them once the ㅎ
# has been spent. Handling only the bare ㅎ missed the clusters: 많다 came out
# *manda* for *manta* and 많은 *manheun* for *maneun*. ㅎ never survives — it
# either aspirates the next stop or disappears before a vowel.
H_CODAS = {6: "n", 15: "l", 27: ""}

# ㅎ aspirates a neighbouring plain stop in either direction: 좋다 jota,
# 축하 chuka, 맏형 matyeong.
ASPIRATE_AFTER_H = {"g": "k", "d": "t", "b": "p", "j": "ch"}
ASPIRATE_BEFORE_H = {"k": "k", "t": "t", "p": "p"}


def _decompose(ch: str) -> tuple[int, int, int] | None:
    code = ord(ch)
    if not (BASE <= code <= LAST):
        return None
    off = code - BASE
    return off // 588, (off % 588) // 28, off % 28


def _link(coda_i: int, onset_i: int, next_vowel_i: int = -1) -> tuple[str, str]:
    """The two sounds at one syllable boundary: what the first syllable ends
    with, and what the second one starts with."""
    coda = CODA_SOUND[coda_i]
    onset = ONSET[onset_i]

    if next_vowel_i in PALATAL_VOWELS and (coda_i, onset_i) in PALATALISE:
        return "", PALATALISE[(coda_i, onset_i)]

    if onset_i == 11:  # ㅇ — silent onset, so the coda re-links across it
        moved = CODA_ONSET.get(coda_i, "")
        if isinstance(moved, tuple):
            return moved[0], moved[1]
        return "", moved

    if coda_i in H_CODAS:  # ㅎ (alone or in a cluster) aspirates the next stop
        return H_CODAS[coda_i], ASPIRATE_AFTER_H.get(onset, onset)
    if onset_i == 18:  # ㅎ onset is aspirated BY the coda
        asp = ASPIRATE_BEFORE_H.get(coda)
        if asp:
            return "", asp

    return ASSIMILATION.get((coda, onset), (coda, onset))


def korean_to_roman(text: str) -> str:
    """An RR reading of *text*. Non-Hangul runs pass through untouched, which
    is what keeps a cloze blank a blank."""
    if not text:
        return ""
    # Build every syllable with its DEFAULT sounds first, then let each
    # boundary overwrite the two cells it governs. Emitting as we walk had the
    # boundary write the next syllable's onset and the next syllable write it
    # again — 감사합니다 came out *gamsahhamnidda*.
    cells: list[dict | str] = []
    for ch in text:
        jamo = _decompose(ch)
        if jamo is None:
            cells.append(ch)
            continue
        onset_i, vowel_i, coda_i = jamo
        cells.append({"onset": ONSET[onset_i], "vowel": VOWEL[vowel_i],
                      "coda": CODA[coda_i], "coda_i": coda_i,
                      "onset_i": onset_i, "vowel_i": vowel_i})

    for i in range(len(cells) - 1):
        here, nxt = cells[i], cells[i + 1]
        if not isinstance(here, dict) or not isinstance(nxt, dict):
            continue
        here["coda"], nxt["onset"] = _link(
            here["coda_i"], nxt["onset_i"], nxt["vowel_i"])

    return "".join(
        c if isinstance(c, str) else c["onset"] + c["vowel"] + c["coda"]
        for c in cells
    )
