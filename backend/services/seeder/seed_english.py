"""English vocabulary seeder using WordNet definitions and a bundled frequency list."""
import csv
import json

from .base import DATA_DIR, BaseSeeder  # noqa: F401 — DATA_DIR re-exported so tests can patch it

# Filename constant so tests can patch DATA_DIR
FREQ_FILENAME = "en_frequency.tsv"


class EnglishSeeder(BaseSeeder):
    language_code = "en"

    async def download(self) -> None:
        """Download NLTK WordNet corpus if not present."""
        import nltk

        try:
            nltk.data.find("corpora/wordnet")
        except LookupError:
            self.logger.info("Downloading WordNet corpus...")
            nltk.download("wordnet", quiet=True)

    async def transform(self) -> list[dict]:
        """Merge frequency list with WordNet definitions."""
        from nltk.corpus import wordnet as wn

        # Use module globals so tests can patch DATA_DIR and FREQ_FILENAME
        import backend.services.seeder.seed_english as _mod

        data_dir = _mod.DATA_DIR
        freq_path = data_dir / _mod.FREQ_FILENAME

        if not freq_path.exists():
            raise FileNotFoundError(f"English frequency file not found at {freq_path}")

        # Read frequency list
        freq_words = []
        with open(freq_path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                freq_words.append((int(row["rank"]), row["word"].strip()))

        # Optional: spaCy for POS and lemmatization
        nlp = None
        try:
            import spacy

            nlp = spacy.load("en_core_web_sm")
        except (ImportError, OSError):
            self.logger.warning("spaCy not available — POS from WordNet only")

        pos_map = {"n": "noun", "v": "verb", "a": "adj", "r": "adv", "s": "adj"}

        # WordNet's first synset for function words is often absurd — "i"
        # resolves to iodine, "a" to a blood type. Grammar words get honest
        # grammar glosses instead.
        function_glosses = {
            "i": "first-person singular pronoun ('I am here')",
            "you": "second-person pronoun",
            "he": "third-person masculine pronoun",
            "she": "third-person feminine pronoun",
            "it": "third-person pronoun for things",
            "we": "first-person plural pronoun",
            "they": "third-person plural pronoun",
            "me": "object form of 'I'",
            "him": "object form of 'he'",
            "her": "object form of 'she'; also 'belonging to she'",
            "us": "object form of 'we'",
            "them": "object form of 'they'",
            "my": "belonging to me",
            "your": "belonging to you",
            "his": "belonging to him",
            "its": "belonging to it",
            "our": "belonging to us",
            "their": "belonging to them",
            "the": "definite article — a specific one",
            "a": "indefinite article — one of many",
            "an": "indefinite article before a vowel sound",
            "this": "the one here",
            "that": "the one there; also a linking word",
            "these": "the ones here (plural)",
            "those": "the ones there (plural)",
            "and": "joins two things",
            "but": "introduces a contrast",
            "or": "offers an alternative",
            "if": "introduces a condition",
            "of": "belonging to / part of",
            "to": "toward; also marks the infinitive",
            "in": "inside; within a period",
            "on": "on top of; on a day",
            "at": "at a point or time",
            "for": "intended for; in exchange for",
            "with": "together with; using",
            "from": "starting point or origin",
            "by": "next to; done by someone",
            "about": "concerning; approximately",
            "as": "in the role of; while",
            "not": "makes a sentence negative",
            "no": "the opposite of yes; not any",
            "so": "therefore; to such a degree",
            "do": "to perform; also the question/negative helper",
            "will": "marks the future; also a promise",
            "would": "unreal or polite version of will",
            "can": "to be able to",
            "could": "past of can; polite request",
            "should": "it is right or advisable to",
            "must": "it is necessary to",
            "may": "it is possible or permitted",
            "might": "it is possible (weaker than may)",
        }

        # spaCy on a bare one-word doc mislabels function words ("a" comes
        # back PRON) — pin their real POS so the translation merge finds
        # the right Wiktionary entry (articles simply have no Russian row,
        # which is correct: no equivalent means no translation).
        function_pos = {
            "a": "article", "an": "article", "the": "article",
            "i": "pron", "you": "pron", "he": "pron", "she": "pron",
            "it": "pron", "we": "pron", "they": "pron", "me": "pron",
            "him": "pron", "her": "pron", "us": "pron", "them": "pron",
            "this": "det", "that": "det", "these": "det", "those": "det",
            "my": "det", "your": "det", "his": "det", "its": "det",
            "our": "det", "their": "det",
            "and": "conj", "but": "conj", "or": "conj", "if": "conj",
            "of": "prep", "to": "prep", "in": "prep", "on": "prep",
            "at": "prep", "for": "prep", "with": "prep", "from": "prep",
            "by": "prep", "about": "prep", "as": "prep",
            "not": "adv", "no": "adv", "so": "adv",
            "do": "verb", "will": "verb", "would": "verb", "can": "verb",
            "could": "verb", "should": "verb", "must": "verb",
            "may": "verb", "might": "verb",
        }

        records = []
        for rank, word in freq_words:
            lower = word.lower()
            if lower in function_glosses:
                definition = function_glosses[lower]
                wn_pos = function_pos.get(lower)
                synsets = []
            else:
                # Look up WordNet synsets for definition
                synsets = wn.synsets(word)
                if not synsets:
                    # Skip words with no synsets (unknown terms)
                    continue
                # Use first synset for primary definition
                primary = synsets[0]
                definition = primary.definition()
                wn_pos = pos_map.get(primary.pos(), None)

            # spaCy POS and lemma if available (never override a pinned
            # function-word POS — spaCy mislabels bare tokens)
            pos = wn_pos
            morphology = {"lemma": word}
            if nlp and lower not in function_pos:
                try:
                    doc = nlp(word)
                    if doc:
                        token = doc[0]
                        if token.pos_:
                            pos = token.pos_.lower()
                        morphology["lemma"] = token.lemma_
                except Exception:
                    pass

            records.append({
                "word": word,
                "reading": None,
                "pos": pos,
                "level": self.rank_to_level(rank),
                "frequency_rank": rank,
                "morphology": json.dumps(morphology, ensure_ascii=False),
                "translations": {"en": definition},
            })

        # Per-locale word translations (built by source_data --language en
        # from the kaikki English extract): lets "learning English from X"
        # learners see the word in THEIR language, not a WordNet definition.
        trans_path = data_dir / "en_translations.tsv"
        if trans_path.exists():
            # word -> kaikki-pos -> locale -> translation. The record's own
            # POS picks the entry, so "go" (verb) never wears its noun
            # sense's translations. A word whose matching entry lacks a
            # locale simply has no translation there — the UI falls back to
            # the English gloss (never a wrong-sense one).
            extra: dict[str, dict[str, dict[str, str]]] = {}
            with open(trans_path, encoding="utf-8") as f:
                for row in csv.DictReader(f, delimiter="\t"):
                    word = row["word"].strip().lower()
                    if row.get("locale") and row.get("translation"):
                        pos = (row.get("pos") or "").strip()
                        extra.setdefault(word, {}).setdefault(pos, {})[
                            row["locale"]] = row["translation"]
            spacy_to_kaikki = {
                "adp": "prep", "cconj": "conj", "sconj": "conj",
                "aux": "verb", "propn": "noun", "part": "particle",
            }
            # Core subject pronouns are certain, universal knowledge — a
            # hand table beats any extraction. Articles are pinned EMPTY:
            # most languages have no equivalent, and per the content rule,
            # no equivalent means NO translation (the English gloss shows).
            curated = {
                "i":   {"es": "yo", "fr": "je", "de": "ich", "it": "io",
                        "pt": "eu", "ca": "jo", "ro": "eu", "ru": "я",
                        "el": "εγώ", "tr": "ben", "ar": "أنا", "sw": "mimi"},
                "you": {"es": "tú; usted", "fr": "tu; vous", "de": "du; Sie",
                        "it": "tu; Lei", "pt": "você; tu", "ca": "tu; vostè",
                        "ro": "tu; dumneavoastră", "ru": "ты; вы",
                        "el": "εσύ; εσείς", "tr": "sen; siz",
                        "ar": "أنتَ / أنتِ", "sw": "wewe"},
                "he":  {"es": "él", "fr": "il", "de": "er", "it": "lui",
                        "pt": "ele", "ca": "ell", "ro": "el", "ru": "он",
                        "el": "αυτός", "tr": "o", "ar": "هو", "sw": "yeye"},
                "she": {"es": "ella", "fr": "elle", "de": "sie", "it": "lei",
                        "pt": "ela", "ca": "ella", "ro": "ea", "ru": "она",
                        "el": "αυτή", "tr": "o", "ar": "هي", "sw": "yeye"},
                "we":  {"es": "nosotros", "fr": "nous", "de": "wir",
                        "it": "noi", "pt": "nós", "ca": "nosaltres",
                        "ro": "noi", "ru": "мы", "el": "εμείς", "tr": "biz",
                        "ar": "نحن", "sw": "sisi"},
                "they": {"es": "ellos", "fr": "ils", "de": "sie",
                         "it": "loro", "pt": "eles", "ca": "ells",
                         "ro": "ei", "ru": "они", "el": "αυτοί",
                         "tr": "onlar", "ar": "هم", "sw": "wao"},
                # Grammatical words where extraction fails hard: case
                # languages get bare suffixes ("of" → ru "-ов"), languages
                # without a neuter get the wrong gender ("it" → ru "он" =
                # *he*, de "er"), and auxiliaries pick up noun senses
                # ("will" → ru "завещать" = *bequeath*). Beta report
                # 2026-07-16. Where no one-word equivalent exists, a short
                # parenthesized hint beats a wrong word.
                "it": {"es": "ello; eso", "fr": "il; ce", "de": "es",
                       "it": "esso; ciò", "ca": "això",
                       "pt": "ele/ela (coisa); isso",
                       "ro": "el/ea (obiect); asta", "ru": "оно́; э́то",
                       "el": "αυτό", "tr": "o (nesne)",
                       "ar": "هو / هي (لغير العاقل)", "sw": "kitu hicho"},
                "of": {"es": "de", "fr": "de", "de": "von", "it": "di",
                       "ca": "de", "pt": "de", "ro": "de; al",
                       "ru": "(принадле́жность — роди́тельный паде́ж)",
                       "el": "του / της", "tr": "-in / -ın (tamlayan)",
                       "ar": "لِـ (مِلْكِيَّة)", "sw": "-a (ya / wa / cha)"},
                "to": {"es": "a", "fr": "à", "de": "zu; nach", "it": "a",
                       "ca": "a", "pt": "a; para", "ro": "la; spre",
                       "ru": "к; в; до", "el": "σε; προς",
                       "tr": "-e / -a (yönelme)", "ar": "إِلَى",
                       "sw": "kwa; hadi"},
                "at": {"es": "en", "fr": "à", "de": "an; bei", "it": "a",
                       "ca": "a", "pt": "em", "ro": "la",
                       "ru": "у; в; на (ме́сто, вре́мя)", "el": "σε",
                       "tr": "-de / -da (bulunma)", "ar": "عِنْد",
                       "sw": "kwenye"},
                "by": {"es": "por", "fr": "par", "de": "von; bei",
                       "it": "da", "ca": "per", "pt": "por",
                       "ro": "de; lângă",
                       "ru": "(кем/чем — твори́тельный паде́ж); у",
                       "el": "από; δίπλα σε", "tr": "tarafından",
                       "ar": "بِـ", "sw": "na; kando ya"},
                "will": {"es": "(futuro)", "fr": "(futur)",
                         "de": "werden (Futur)", "it": "(futuro)",
                         "ca": "(futur)", "pt": "(futuro)",
                         "ro": "(viitor: va…)",
                         "ru": "(бу́дущее вре́мя: бу́дет)",
                         "el": "θα (μέλλοντας)", "tr": "-ecek / -acak",
                         "ar": "سَوْفَ / سَـ", "sw": "-ta- (wakati ujao)"},
                "would": {"es": "(condicional)", "fr": "(conditionnel)",
                          "de": "würde", "it": "(condizionale)",
                          "ca": "(condicional)", "pt": "(condicional)",
                          "ro": "(condițional: ar…)",
                          "ru": "бы (усло́вное)", "el": "θα (υποθετικό)",
                          "tr": "-erdi / -irdi", "ar": "كَانَ سَـ",
                          "sw": "-nge-"},
                "not": {"es": "no", "fr": "ne … pas", "de": "nicht",
                        "it": "non", "ca": "no", "pt": "não", "ro": "nu",
                        "ru": "не", "el": "δεν", "tr": "değil",
                        "ar": "لَا / لَيْسَ", "sw": "si / ha-"},
                "so": {"es": "así que; tan", "fr": "donc; si",
                       "de": "also; so", "it": "quindi; così",
                       "ca": "així que; tan", "pt": "então; tão",
                       "ro": "deci; atât de", "ru": "поэ́тому; так",
                       "el": "άρα; τόσο", "tr": "bu yüzden; çok",
                       "ar": "لِذَا; جِدًّا", "sw": "kwa hiyo; sana"},
                "why": {"es": "por qué", "fr": "pourquoi", "de": "warum",
                        "it": "perché", "ca": "per què", "pt": "por quê",
                        "ro": "de ce", "ru": "почему́", "el": "γιατί",
                        "tr": "neden", "ar": "لِمَاذَا", "sw": "kwa nini"},
                "your": {"es": "tu; su", "fr": "ton; votre",
                         "de": "dein; Ihr", "it": "tuo; Suo",
                         "ca": "teu; seu", "pt": "seu; teu",
                         "ro": "tău", "ru": "твой; ваш",
                         "el": "σου; σας", "tr": "senin; sizin",
                         "ar": "ـكَ / ـكِ", "sw": "-ako"},
                "their": {"es": "su (de ellos)", "fr": "leur", "de": "ihr",
                          "it": "loro", "ca": "el seu",
                          "pt": "deles / delas", "ro": "lor", "ru": "их",
                          "el": "τους", "tr": "onların", "ar": "ـهُم",
                          "sw": "-ao"},
                "his": {"es": "su (de él)", "fr": "son", "de": "sein",
                        "it": "suo", "ca": "el seu", "pt": "dele",
                        "ro": "său; lui", "ru": "его́", "el": "του",
                        "tr": "onun", "ar": "ـهُ", "sw": "-ake"},
                "its": {"es": "su (de ello)", "fr": "son", "de": "sein",
                        "it": "suo", "ca": "el seu", "pt": "dele / dela",
                        "ro": "său", "ru": "его́ / её", "el": "του",
                        "tr": "onun", "ar": "ـهُ / ـهَا", "sw": "-ake"},
                "a": {}, "an": {}, "the": {},
            }
            fallback_order = ("pron", "det", "article", "conj", "prep",
                              "particle", "num", "noun", "verb", "adj",
                              "adv", "intj")
            enriched = 0
            for rec in records:
                lower = rec["word"].lower()
                if lower in curated:
                    rec["translations"].update(curated[lower])
                    enriched += 1
                    continue
                per_pos = extra.get(lower)
                if not per_pos:
                    continue
                pos = (rec.get("pos") or "").lower()
                pos = spacy_to_kaikki.get(pos, pos)
                locales = per_pos.get(pos)
                if locales is None and lower not in function_pos:
                    # content words may fall back across entries; pinned
                    # grammar words must never wear another entry's senses
                    for candidate in fallback_order:
                        if candidate in per_pos:
                            locales = per_pos[candidate]
                            break
                if locales:
                    rec["translations"].update(locales)
                    enriched += 1
            self.logger.info(
                f"Merged support-locale translations for {enriched} words"
            )

        self.logger.info(f"Transformed {len(records)} English words")
        return records
