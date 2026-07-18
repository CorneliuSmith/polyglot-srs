"""Language-shaped morphology for vocabulary cards (§3b).

Turns kaikki (Wiktionary) `forms` arrays into two structures the card page
renders generically:

  chips  — ordered {label, value} facts (gender, aspect + pair, verb form,
           plural, auxiliary, noun class…)
  charts — small tables {title, columns?, rows} (conjugations, declensions)

The LANGUAGE decides what a learner needs per part of speech: a Russian
verb card carries its aspect pair and conjugation; a German noun its
gender-genitive-plural triple; an Arabic noun its (often broken) plural;
a Spanish verb its core tense table. Builders live here so the judgment
is executable and testable — the seeder just merges the output into
vocabulary.morphology.

CLI: python -m backend.services.seeder.morphology_charts --language ru
Reads data/raw/{code}_kaikki.jsonl, keeps entries whose word is in
data/{code}_frequency.tsv, writes data/{code}_morphology.json.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

logger = logging.getLogger("morphology")

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
RAW_DIR = DATA_DIR / "raw"

# tags that mark table plumbing or variants we never chart
NOISE = {"table-tags", "inflection-template", "class", "romanization",
         "archaic", "obsolete", "rare", "dated", "dialectal"}

# Gender / number are properties of nouns and adjectives only. When a
# high-frequency function word (de, para, no, yo, sí…) is a homograph of a
# rare noun, kaikki's `forms` come from that noun sense, so the card ends up
# showing "Gender feminine, Plural des" on a preposition. These labels are
# never right on a non-nominal word — strip them (folded per-word against the
# card's chosen part of speech).
NOMINAL_CHIP_LABELS = {"Gender", "Plural", "Feminine", "Animacy"}
NOMINAL_POS = {"noun", "adj", "name", "propn"}


def strip_nominal_chips(morphology: dict | None, pos: str | None) -> dict | None:
    """Drop gender/number chips from a word whose part of speech can't carry
    them. No-op for nouns/adjectives and for morphology without such chips."""
    if not morphology or pos in NOMINAL_POS:
        return morphology
    chips = morphology.get("chips")
    if not chips:
        return morphology
    kept = [c for c in chips if c.get("label") not in NOMINAL_CHIP_LABELS]
    if len(kept) == len(chips):
        return morphology
    out = dict(morphology)
    if kept:
        out["chips"] = kept
    else:
        out.pop("chips", None)
    return out


def _clean_forms(entry: dict) -> list[tuple[str, frozenset[str]]]:
    out = []
    for f in entry.get("forms", []):
        form = (f.get("form") or "").strip()
        tags = frozenset(f.get("tags") or [])
        if not form or form == "-" or tags & NOISE:
            continue
        out.append((form, tags))
    return out


def _pick(forms, must: set[str], exclude: set[str] = frozenset()) -> str | None:
    """First form whose tags contain all of *must* and none of *exclude*."""
    for form, tags in forms:
        if must <= tags and not (tags & exclude):
            return form
    return None


def _person_rows(forms, labels: list[tuple[str, set[str]]],
                 base: set[str], exclude: set[str] = frozenset()) -> list[list[str]]:
    rows = []
    for label, person_tags in labels:
        form = _pick(forms, base | person_tags, exclude)
        if form:
            rows.append([label, form])
    return rows


def _chart(title: str, rows: list[list[str]], min_rows: int = 3,
           columns: list[str] | None = None) -> dict | None:
    if len(rows) < min_rows:
        return None
    c: dict = {"title": title, "rows": rows}
    if columns:
        c["columns"] = columns
    return c


def _canonical_tags(entry: dict) -> frozenset[str]:
    for f in entry.get("forms", []):
        if "canonical" in (f.get("tags") or []):
            return frozenset(f["tags"])
    return frozenset(entry.get("tags") or [])


def _expansion(entry: dict) -> str:
    hts = entry.get("head_templates") or []
    return hts[0].get("expansion", "") if hts else ""


# ── Russian ───────────────────────────────────────────────────────────────

RU_PERSONS = [
    ("я", {"first-person", "singular"}),
    ("ты", {"second-person", "singular"}),
    ("он/она́", {"third-person", "singular"}),
    ("мы", {"first-person", "plural"}),
    ("вы", {"second-person", "plural"}),
    ("они́", {"third-person", "plural"}),
]

RU_CASES = [("Nom.", "nominative"), ("Gen.", "genitive"), ("Dat.", "dative"),
            ("Acc.", "accusative"), ("Ins.", "instrumental"),
            ("Prep.", "prepositional")]


def build_ru(entry: dict) -> dict | None:
    pos = entry.get("pos")
    forms = _clean_forms(entry)
    canon = _canonical_tags(entry)
    chips: list[dict] = []
    charts: list[dict] = []

    if pos == "verb":
        aspect = ("imperfective" if "imperfective" in canon
                  else "perfective" if "perfective" in canon else None)
        if aspect:
            chips.append({"label": "Aspect", "value": aspect})
            partner_tag = "perfective" if aspect == "imperfective" else "imperfective"
            partners = [f for f, t in forms if t == frozenset({partner_tag})]
            if partners:
                chips.append({
                    "label": f"{partner_tag.capitalize()} pair",
                    "value": ", ".join(dict.fromkeys(partners)),
                })
        tense = "present" if aspect != "perfective" else "future"
        chart = _chart(tense.capitalize(),
                       _person_rows(forms, RU_PERSONS, {tense}, {"future"} if tense == "present" else set()))
        if chart:
            charts.append(chart)
        past = []
        for label, must in (("он", {"masculine"}), ("она́", {"feminine"}),
                            ("оно́", {"neuter"}), ("они́", {"plural"})):
            f = _pick(forms, {"past"} | must, {"participle", "adverbial"})
            if f:
                past.append([label, f])
        chart = _chart("Past", past)
        if chart:
            charts.append(chart)
        imp = []
        for label, must in (("ты", {"singular"}), ("вы", {"plural"})):
            f = _pick(forms, {"imperative"} | must)
            if f:
                imp.append([label, f])
        chart = _chart("Imperative", imp, min_rows=2)
        if chart:
            charts.append(chart)

    elif pos == "noun":
        gender = next((g for g in ("masculine", "feminine", "neuter") if g in canon), None)
        if gender:
            chips.append({"label": "Gender", "value": gender})
        if "animate" in canon:
            chips.append({"label": "Animacy", "value": "animate"})
        elif "inanimate" in canon:
            chips.append({"label": "Animacy", "value": "inanimate"})
        rows = []
        for label, case in RU_CASES:
            sg = _pick(forms, {case, "singular"})
            pl = _pick(forms, {case, "plural"})
            if sg or pl:
                rows.append([label, sg or "—", pl or "—"])
        chart = _chart("Declension", rows, min_rows=4,
                       columns=["", "Singular", "Plural"])
        if chart:
            charts.append(chart)

    elif pos == "adj":
        comp = _pick(forms, {"comparative"})
        if comp:
            chips.append({"label": "Comparative", "value": comp})
        short = []
        for label, must in (("m", {"masculine"}), ("f", {"feminine"}),
                            ("n", {"neuter"}), ("pl", {"plural"})):
            f = _pick(forms, {"short"} | must)
            if f:
                short.append([label, f])
        chart = _chart("Short forms", short)
        if chart:
            charts.append(chart)

    return _pack(chips, charts)


# ── Romance (es, pt, it, fr, ca, ro) ─────────────────────────────────────

ROMANCE_PRONOUNS = {
    "es": ["yo", "tú", "él/ella", "nosotros", "vosotros", "ellos"],
    "pt": ["eu", "tu", "ele/você", "nós", "vós", "eles"],
    "it": ["io", "tu", "lui/lei", "noi", "voi", "loro"],
    "fr": ["je", "tu", "il/elle", "nous", "vous", "ils"],
    "ca": ["jo", "tu", "ell/ella", "nosaltres", "vosaltres", "ells"],
    "ro": ["eu", "tu", "el/ea", "noi", "voi", "ei"],
}

PERSON_TAGS = [
    {"first-person", "singular"}, {"second-person", "singular"},
    {"third-person", "singular"}, {"first-person", "plural"},
    {"second-person", "plural"}, {"third-person", "plural"},
]

# core tenses per language: (title, must-tags). Exclusions keep vos/voseo
# and compound rows out of the simple tables.
ROMANCE_TENSES = {
    "es": [("Present", {"indicative", "present"}),
           ("Preterite", {"indicative", "preterite"}),
           ("Imperfect", {"indicative", "imperfect"}),
           ("Future", {"indicative", "future"}),
           ("Subjunctive (present)", {"subjunctive", "present"})],
    "pt": [("Present", {"indicative", "present"}),
           ("Preterite (perfeito)", {"indicative", "preterite"}),
           ("Imperfect", {"indicative", "imperfect"}),
           ("Future", {"indicative", "future"}),
           ("Subjunctive (present)", {"subjunctive", "present"})],
    "it": [("Present", {"indicative", "present"}),
           ("Imperfect", {"indicative", "imperfect"}),
           ("Future", {"indicative", "future"}),
           ("Passato remoto", {"indicative", "past", "historic"}),
           ("Subjunctive (present)", {"subjunctive", "present"})],
    "fr": [("Present", {"indicative", "present"}),
           ("Imperfect", {"indicative", "imperfect"}),
           ("Future", {"indicative", "future"}),
           ("Conditional", {"conditional"}),
           ("Subjunctive (present)", {"subjunctive", "present"})],
    "ca": [("Present", {"indicative", "present"}),
           ("Imperfect", {"indicative", "imperfect"}),
           ("Future", {"indicative", "future"}),
           ("Subjunctive (present)", {"subjunctive", "present"})],
    "ro": [("Present", {"indicative", "present"}),
           ("Imperfect", {"indicative", "imperfect"}),
           ("Simple perfect", {"indicative", "perfect", "simple"}),
           ("Subjunctive (present)", {"subjunctive", "present"})],
}

ROMANCE_EXCLUDE = {"vos-form", "voseo", "compound", "perfect", "pronominal",
                   "formal", "reflexive", "negative"}


def build_romance(code: str):
    pronouns = ROMANCE_PRONOUNS[code]
    labels = list(zip(pronouns, PERSON_TAGS))
    tenses = ROMANCE_TENSES[code]

    def _build(entry: dict) -> dict | None:
        pos = entry.get("pos")
        forms = _clean_forms(entry)
        canon = _canonical_tags(entry)
        chips: list[dict] = []
        charts: list[dict] = []

        if pos == "verb":
            ger = _pick(forms, {"gerund"}) or _pick(forms, {"participle", "present"})
            part = _pick(forms, {"participle", "past"})
            if ger:
                chips.append({"label": "Gerund", "value": ger})
            if part:
                chips.append({"label": "Past participle", "value": part})
            for title, must in tenses:
                exclude = ROMANCE_EXCLUDE - must
                chart = _chart(title, _person_rows(forms, labels, must, exclude),
                               min_rows=4)
                if chart:
                    charts.append(chart)
        elif pos == "noun":
            gender = next((g for g in ("masculine", "feminine", "neuter") if g in canon), None)
            if not gender:
                exp = _expansion(entry)
                gender = ("feminine" if " f " in f" {exp} " else
                          "masculine" if " m " in f" {exp} " else None)
            if gender:
                chips.append({"label": "Gender", "value": gender})
            pl = _pick(forms, {"plural"})
            if pl:
                chips.append({"label": "Plural", "value": pl})
        elif pos == "adj":
            fem = _pick(forms, {"feminine", "singular"})
            pl = _pick(forms, {"masculine", "plural"}) or _pick(forms, {"plural"})
            if fem:
                chips.append({"label": "Feminine", "value": fem})
            if pl:
                chips.append({"label": "Plural", "value": pl})

        return _pack(chips, charts)

    return _build


# ── German ────────────────────────────────────────────────────────────────

DE_PRONOUNS = [("ich", {"first-person", "singular"}),
               ("du", {"second-person", "singular"}),
               ("er/sie/es", {"third-person", "singular"}),
               ("wir", {"first-person", "plural"}),
               ("ihr", {"second-person", "plural"}),
               ("sie", {"third-person", "plural"})]


def build_de(entry: dict) -> dict | None:
    pos = entry.get("pos")
    forms = _clean_forms(entry)
    chips: list[dict] = []
    charts: list[dict] = []

    if pos == "verb":
        praet = _pick(forms, {"past"}, {"participle", "subjunctive", "first-person",
                                        "second-person", "third-person", "plural"})
        part = _pick(forms, {"participle", "past"})
        aux = _pick(forms, {"auxiliary"})
        if praet:
            chips.append({"label": "Präteritum", "value": praet})
        if part:
            chips.append({"label": "Partizip II", "value": part})
        if aux:
            chips.append({"label": "Auxiliary", "value": aux})
        chart = _chart("Present", _person_rows(
            forms, DE_PRONOUNS, {"indicative", "present"}, {"subjunctive"}), min_rows=4)
        if chart:
            charts.append(chart)
    elif pos == "noun":
        exp = f" {_expansion(entry)} "
        gender = ("das" if " n " in exp else "der" if " m " in exp
                  else "die" if " f " in exp else None)
        if gender:
            chips.append({"label": "Article", "value": gender})
        gen = _pick(forms, {"genitive"}, {"plural"})
        pl = _pick(forms, {"plural"}, {"diminutive", "genitive", "dative"})
        if gen:
            chips.append({"label": "Genitive", "value": gen})
        if pl:
            chips.append({"label": "Plural", "value": pl})
    elif pos == "adj":
        comp = _pick(forms, {"comparative"})
        sup = _pick(forms, {"superlative"})
        if comp:
            chips.append({"label": "Comparative", "value": comp})
        if sup:
            chips.append({"label": "Superlative", "value": sup})

    return _pack(chips, charts)


# ── Arabic ────────────────────────────────────────────────────────────────

AR_PERSONS = [
    ("أنا", {"first-person", "singular"}),
    ("أنتَ", {"second-person", "masculine", "singular"}),
    ("أنتِ", {"second-person", "feminine", "singular"}),
    ("هو", {"third-person", "masculine", "singular"}),
    ("هي", {"third-person", "feminine", "singular"}),
    ("نحن", {"first-person", "plural"}),
    ("أنتم", {"second-person", "masculine", "plural"}),
    ("هم", {"third-person", "masculine", "plural"}),
]

AR_FORM_NAMES = {f"form-{r}": r.upper() for r in
                 ("i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x")}


def build_ar(entry: dict) -> dict | None:
    pos = entry.get("pos")
    forms = _clean_forms(entry)
    canon = _canonical_tags(entry)
    chips: list[dict] = []
    charts: list[dict] = []

    if pos == "verb":
        for tag, roman in AR_FORM_NAMES.items():
            if tag in canon:
                chips.append({"label": "Verb form", "value": f"Form {roman}"})
                break
        nonpast = _pick(forms, {"non-past"}, {"active", "passive"})
        masdar = _pick(forms, {"noun-from-verb"})
        act_part = _pick(forms, {"active", "participle"})
        if nonpast:
            chips.append({"label": "Non-past", "value": nonpast})
        if masdar:
            chips.append({"label": "Maṣdar", "value": masdar})
        if act_part:
            chips.append({"label": "Active participle", "value": act_part})
        chart = _chart("Past (الماضي)", _person_rows(
            forms, AR_PERSONS, {"past", "perfective", "indicative", "active"},
            {"passive", "jussive", "subjunctive"}), min_rows=4)
        if chart:
            charts.append(chart)
        chart = _chart("Present (المضارع)", _person_rows(
            forms, AR_PERSONS, {"non-past", "imperfective", "indicative", "active"},
            {"passive", "jussive", "subjunctive"}), min_rows=4)
        if chart:
            charts.append(chart)
    elif pos == "noun":
        gender = next((g for g in ("masculine", "feminine") if g in canon), None)
        if gender:
            chips.append({"label": "Gender", "value": gender})
        pl = _pick(forms, {"plural"}, {"construct", "definite", "nominative",
                                       "accusative", "genitive", "informal"})
        dual = _pick(forms, {"dual"}, {"construct", "definite", "nominative",
                                       "accusative", "genitive", "informal"})
        if pl:
            chips.append({"label": "Plural", "value": pl})
        if dual:
            chips.append({"label": "Dual", "value": dual})

    return _pack(chips, charts)


# ── Greek ─────────────────────────────────────────────────────────────────

EL_PERSONS = [
    ("εγώ", {"first-person", "singular"}),
    ("εσύ", {"second-person", "singular"}),
    ("αυτός/-ή", {"third-person", "singular"}),
    ("εμείς", {"first-person", "plural"}),
    ("εσείς", {"second-person", "plural"}),
    ("αυτοί", {"third-person", "plural"}),
]

EL_CASES = [("Nom.", "nominative"), ("Gen.", "genitive"),
            ("Acc.", "accusative"), ("Voc.", "vocative")]


def build_el(entry: dict) -> dict | None:
    pos = entry.get("pos")
    forms = _clean_forms(entry)
    canon = _canonical_tags(entry)
    chips: list[dict] = []
    charts: list[dict] = []

    if pos == "verb":
        aorist = _pick(forms, {"past"}, {"participle", "passive", "imperfect"})
        passive = _pick(forms, {"passive"}, {"participle", "past", "imperfect",
                                             "first-person", "second-person"})
        if aorist:
            chips.append({"label": "Aorist", "value": aorist})
        if passive:
            chips.append({"label": "Passive", "value": passive})
        chart = _chart("Present", _person_rows(
            forms, EL_PERSONS,
            {"active", "imperfective", "indicative", "present"},
            {"passive", "dependent"}), min_rows=4)
        if chart:
            charts.append(chart)
    elif pos == "noun":
        gender = next((g for g in ("masculine", "feminine", "neuter") if g in canon), None)
        if not gender:
            exp = f" {_expansion(entry)} "
            gender = ("neuter" if " n " in exp else "feminine" if " f " in exp
                      else "masculine" if " m " in exp else None)
        if gender:
            chips.append({"label": "Gender", "value": gender})
        rows = []
        for label, case in EL_CASES:
            sg = _pick(forms, {case, "singular"})
            pl = _pick(forms, {case, "plural"})
            if sg or pl:
                rows.append([label, sg or "—", pl or "—"])
        chart = _chart("Declension", rows, min_rows=3,
                       columns=["", "Singular", "Plural"])
        if chart:
            charts.append(chart)

    return _pack(chips, charts)


# ── Turkish (noun cases; verb tables in kaikki are too noisy to chart) ────

TR_CASES = [("Nom.", "nominative"), ("Acc.", "accusative"), ("Dat.", "dative"),
            ("Loc.", "locative"), ("Abl.", "ablative"), ("Gen.", "genitive")]


def build_tr(entry: dict) -> dict | None:
    pos = entry.get("pos")
    forms = _clean_forms(entry)
    chips: list[dict] = []
    charts: list[dict] = []

    if pos == "noun":
        rows = []
        for label, case in TR_CASES:
            sg = _pick(forms, {case, "singular"})
            pl = _pick(forms, {case, "plural"})
            if sg or pl:
                rows.append([label, sg or "—", pl or "—"])
        chart = _chart("Cases", rows, min_rows=4, columns=["", "Singular", "Plural"])
        if chart:
            charts.append(chart)

    return _pack(chips, charts)


# ── Swahili (noun classes + key verb forms) ───────────────────────────────

def build_sw(entry: dict) -> dict | None:
    pos = entry.get("pos")
    forms = _clean_forms(entry)
    chips: list[dict] = []

    if pos == "noun":
        for form, tags in forms:
            cls = next((t for t in tags if t.startswith("class-")), None)
            if cls and "plural" in tags:
                chips.append({"label": "Plural", "value": form})
                chips.append({"label": "Class", "value": cls.removeprefix("class-").upper()})
                break
        else:
            pl = _pick(forms, {"plural"})
            if pl:
                chips.append({"label": "Plural", "value": pl})
    elif pos == "verb":
        inf = _pick(forms, {"infinitive"}, {"negative"})
        imp_sg = _pick(forms, {"imperative", "singular"})
        imp_pl = _pick(forms, {"imperative", "plural"})
        hab = _pick(forms, {"habitual"})
        if inf:
            chips.append({"label": "Infinitive", "value": inf})
        if imp_sg:
            chips.append({"label": "Imperative", "value": imp_sg})
        if imp_pl:
            chips.append({"label": "Imperative (pl)", "value": imp_pl})
        if hab:
            chips.append({"label": "Habitual", "value": hab})

    return _pack(chips, [])


# ── Generic (xh, yo: thin extracts — take what exists) ───────────────────

def build_generic(entry: dict) -> dict | None:
    forms = _clean_forms(entry)
    chips: list[dict] = []
    pl = _pick(forms, {"plural"})
    if pl:
        chips.append({"label": "Plural", "value": pl})
    return _pack(chips, [])


def _pack(chips: list[dict], charts: list[dict]) -> dict | None:
    out = {}
    if chips:
        out["chips"] = chips
    if charts:
        out["charts"] = charts
    return out or None


BUILDERS = {
    "ru": build_ru,
    "es": build_romance("es"),
    "pt": build_romance("pt"),
    "it": build_romance("it"),
    "fr": build_romance("fr"),
    "ca": build_romance("ca"),
    "ro": build_romance("ro"),
    "de": build_de,
    "ar": build_ar,
    "el": build_el,
    "tr": build_tr,
    "sw": build_sw,
    "xh": build_generic,
    "yo": build_generic,
}


def _frequency_words(code: str) -> set[str]:
    path = DATA_DIR / f"{code}_frequency.tsv"
    words: set[str] = set()
    if not path.exists():
        return words
    with open(path, encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        idx = header.index("word") if "word" in header else 0
        for line in f:
            cols = line.rstrip("\n").split("\t")
            if len(cols) > idx and cols[idx]:
                words.add(cols[idx])
    return words


def build_language(code: str) -> int:
    """Stream the kaikki extract and write data/{code}_morphology.json."""
    builder = BUILDERS[code]
    src = RAW_DIR / f"{code}_kaikki.jsonl"
    wanted = _frequency_words(code)
    # Frequency lists are lowercased (HermitDave) while Wiktionary keeps
    # orthographic case (German nouns!). Match case-insensitively and key
    # the output by the DB's spelling so the seeder merge lines up.
    by_lower = {w.lower(): w for w in wanted}
    out: dict[str, dict] = {}
    with open(src, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            word = entry.get("word")
            if not word:
                continue
            if wanted:
                db_word = by_lower.get(word.lower())
                if db_word is None:
                    continue
            else:
                db_word = word
            if db_word in out:
                # first entry that PRODUCES morphology wins — kaikki lists
                # the primary lemma before rarer homographs
                continue
            built = builder(entry)
            if built:
                built["pos"] = entry.get("pos")
                out[db_word] = built
    dest = DATA_DIR / f"{code}_morphology.json"
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0, sort_keys=True)
        f.write("\n")
    logger.info("%s: %d words with morphology -> %s", code, len(out), dest)
    return len(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build morphology chart files")
    parser.add_argument("--language", "-l", required=True,
                        choices=[*BUILDERS.keys(), "all"])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
    codes = list(BUILDERS) if args.language == "all" else [args.language]
    for code in codes:
        if not (RAW_DIR / f"{code}_kaikki.jsonl").exists():
            logger.warning("%s: no kaikki extract, skipped", code)
            continue
        build_language(code)


if __name__ == "__main__":
    main()
