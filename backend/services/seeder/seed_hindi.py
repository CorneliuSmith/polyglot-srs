"""Hindi vocabulary seeder.

Same rank/word/pos/en TSV as the Latin-script tier (built by source_data
from the HermitDave 2018 Devanagari list + the kaikki Hindi extract), but
Devanagari is non-Latin, so every row also gets a romanized `reading` — the
transliteration hint layer a beginner sounds the word out from. Readings come
from the practical schwa-deleting romanizer in services/nlp/hindi and are
aids, not phonology; they ride reviewed:false with the rest of the tier.
"""
import csv
import json

from backend.services.nlp.hindi import devanagari_to_roman

from .base import DATA_DIR, BaseSeeder  # noqa: F401 — re-exported so tests can patch it

FREQ_FILENAME = "hi_frequency.tsv"

# The Hindi kaikki extract glosses inflected forms as "inflection of X
# (translit):" — unhelpful for a learner, and these forms dominate the
# high-frequency band (45 of the top 200). Curated English glosses for the
# common function words and inflected forms override the kaikki text so the
# A1/A2 vocabulary reads cleanly; the long tail keeps its kaikki gloss.
# Flagged for native review with the rest of the Hindi tier.
HI_CURATED: dict[str, str] = {
    # copula होना
    "है": "is; are (3rd person present)", "हैं": "are (plural / respectful)",
    "हो": "are (you, informal); be", "हूँ": "am", "था": "was (masc.)",
    "थी": "was (fem.)", "थे": "were (masc. pl.)", "थीं": "were (fem. pl.)",
    "हुआ": "happened; became (masc.)", "हुई": "happened; became (fem.)",
    "हुए": "happened; became (pl.)", "होगा": "will be; probably is",
    "होता": "is / would be (habitual, masc.)", "होती": "is / would be (habitual, fem.)",
    # का/के/की possessive + oblique
    "का": "of; 's (masc. sing.)", "के": "of; 's (masc. pl. / oblique)",
    "की": "of; 's (fem.)", "को": "to; (object marker)", "ने": "(past-tense subject marker)",
    "में": "in; inside", "से": "from; with; by", "पर": "on; at; but",
    # pronouns and possessives
    "मैं": "I", "मुझे": "to me; me", "मेरे": "my (oblique/pl.)", "मेरा": "my (masc.)",
    "मेरी": "my (fem.)", "हम": "we", "हमारे": "our (oblique/pl.)", "हमारा": "our",
    "तुम": "you (informal)", "तुम्हारे": "your (informal, oblique/pl.)",
    "आप": "you (respectful)", "आपके": "your (respectful)", "वह": "he; she; that",
    "वे": "they; those", "यह": "this; he; she", "ये": "these", "उसके": "his; her (oblique)",
    "उसे": "to him; to her", "उन": "those; them (oblique)", "इस": "this (oblique)",
    "अपने": "one's own (oblique/pl.)", "अपना": "one's own", "जो": "who; which (relative)",
    # very common verbs (inflected forms → base meaning)
    "करना": "to do; to make", "करता": "does (masc.)", "करती": "does (fem.)",
    "करते": "do (pl.)", "करो": "do! (informal)", "करें": "do (subjunctive/respectful)",
    "किया": "did", "करने": "to do (oblique infinitive)", "करेंगे": "will do (pl.)",
    "जाना": "to go", "जा": "go (stem)", "जाओ": "go! (informal)", "जाता": "goes (masc.)",
    "जाने": "to go (oblique)", "गया": "went (masc.)", "गई": "went (fem.)",
    "रहना": "to stay; to keep (on)", "रहा": "(continuous marker, masc.)",
    "रही": "(continuous marker, fem.)", "रहे": "(continuous marker, pl.)",
    "लेना": "to take", "ले": "take (stem)", "लिया": "took", "लिए": "for; took (pl.)",
    "देना": "to give", "दिया": "gave", "देखना": "to see; to look",
    "देखो": "look! (informal)", "देखा": "saw", "देख": "see (stem)",
    "सकना": "to be able to; can", "सकते": "can (pl.)", "सकता": "can (masc.)",
    "चाहना": "to want", "चाहता": "wants (masc.)", "चाहते": "want (pl.)",
    "चाहिए": "is needed; should", "जानना": "to know", "जानते": "know (pl.)",
    "लगना": "to seem; to feel; to begin", "लगता": "seems (masc.)",
    "छोड़": "leave; quit (stem)", "आना": "to come", "आओ": "come! (informal)",
    "बारे": "about (के बारे में)",
}


class HindiSeeder(BaseSeeder):
    language_code = "hi"

    async def download(self) -> None:
        import backend.services.seeder.seed_hindi as _mod

        path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not path.exists():
            self.logger.warning(
                "Hindi frequency file not found at %s — run "
                "source_data --language hi --source kaikki", path
            )

    async def transform(self) -> list[dict]:
        import backend.services.seeder.seed_hindi as _mod

        freq_path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not freq_path.exists():
            raise FileNotFoundError(f"Frequency file not found at {freq_path}")

        records = []
        seen: set[str] = set()
        with open(freq_path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                word = row["word"].strip()
                translation = (row.get("en") or "").strip()
                # Curated gloss beats the kaikki "inflection of …:" noise for
                # the common words; otherwise trim a bare trailing colon.
                if word in HI_CURATED:
                    translation = HI_CURATED[word]
                elif translation.endswith(":"):
                    translation = translation[:-1].strip()
                if not word or not translation or word in seen:
                    continue
                seen.add(word)
                rank = int(row["rank"])
                reading = devanagari_to_roman(word)
                records.append({
                    "word": word,
                    "reading": reading if reading and reading != word else None,
                    "pos": (row.get("pos") or "").strip() or None,
                    "level": self.rank_to_level(rank),
                    "frequency_rank": rank,
                    "morphology": json.dumps({"lemma": word}, ensure_ascii=False),
                    "translations": {"en": translation},
                })

        total = len(records)
        for rec in records:
            if rec.get("frequency_rank") is not None:
                rec["level"] = self.rank_to_level(rec["frequency_rank"], total)

        self.logger.info(f"Transformed {len(records)} Hindi words")
        return records
