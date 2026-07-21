"""Korean vocabulary seeder (WP27).

Rides the generic rails (HermitDave ko frequency list + kaikki Korean
extract + Tatoeba kor sentences) with curated glosses over the
high-frequency band: the kaikki extract glosses particles and function
words in dictionary-speak ("이: nominative case marker used after a
consonant…"), which is useless on a flashcard. Curated entries keep the
plain-language house style.

Readings: Hangul is phonetic — no romanization column, same reasoning as
Thai deferring its tone-marked romanization. Revised-Romanization can be
generated later if native reviewers want it.
"""
import csv
import json

from .base import DATA_DIR, BaseSeeder  # noqa: F401 — re-exported so tests can patch it

FREQ_FILENAME = "ko_frequency.tsv"

# Curated English glosses for the most frequent words where the kaikki
# extract misleads or drowns the meaning in linguistics jargon.
KO_CURATED: dict[str, str] = {
    "은": "(topic particle, after consonant)",
    "는": "(topic particle, after vowel)",
    "이": "(subject particle, after consonant); this",
    "가": "(subject particle, after vowel)",
    "을": "(object particle, after consonant)",
    "를": "(object particle, after vowel)",
    "의": "of; 's (possessive)",
    "에": "at; to; in (time/place)",
    "에서": "at; in; from (action location)",
    "도": "also; too",
    "만": "only; just",
    "와": "and; with (after vowel)",
    "과": "and; with (after consonant)",
    "하고": "and; with (colloquial)",
    "로": "to; by; with (after vowel/ㄹ)",
    "으로": "to; by; with (after consonant)",
    "에게": "to (a person)",
    "한테": "to (a person, colloquial)",
    "부터": "from; starting at",
    "까지": "until; up to",
    "보다": "than (comparison); to see",
    "처럼": "like; as",
    "내가": "I (subject form of 나)",
    "제가": "I (subject form, humble)",
    "네가": "you (subject form of 너)",
    "내": "my; I (before 가)",
    "제": "my (humble)",
    "니": "your (colloquial)",
    "저": "I (humble); that (over there)",
    "나": "I (plain); or",
    "너": "you (plain)",
    "우리": "we; our",
    "그": "he; that",
    "그녀": "she",
    "이것": "this (thing)",
    "그것": "that (thing)",
    "저것": "that (thing over there)",
    "여기": "here",
    "거기": "there",
    "저기": "over there",
    "누구": "who",
    "무엇": "what",
    "뭐": "what (colloquial)",
    "어디": "where",
    "언제": "when",
    "왜": "why",
    "어떻게": "how",
    "얼마나": "how much; how many",
    "하다": "to do",
    "있다": "to exist; to have; there is",
    "없다": "to not exist; to not have",
    "이다": "to be (copula)",
    "아니다": "to not be",
    "되다": "to become; to be done",
    "가다": "to go",
    "오다": "to come",
    "먹다": "to eat",
    "마시다": "to drink",
    "보다가": "while doing",
    "주다": "to give",
    "받다": "to receive",
    "알다": "to know",
    "모르다": "to not know",
    "말하다": "to speak; to say",
    "좋다": "to be good",
    "싫다": "to be disliked; to hate",
    "크다": "to be big",
    "작다": "to be small",
    "많다": "to be many; a lot",
    "적다": "to be few; to write down",
    "네": "yes; your (plain)",
    "아니요": "no",
    "안": "not (before a verb); inside",
    "못": "cannot",
    "잘": "well",
    "정말": "really",
    "아주": "very",
    "너무": "too; very",
    "좀": "a little; please (softener)",
    "다": "all; everything",
    "또": "again; also",
    "그리고": "and (sentence-initial)",
    "그런데": "but; by the way",
    "하지만": "but; however",
    "그래서": "so; therefore",
    "사람": "person",
    "것": "thing; the fact of",
    "거": "thing (colloquial)",
    "때": "time; when",
    "년": "year (counter)",
    "일": "day; work; one",
    "시간": "time; hour",
    "집": "house; home",
    "물": "water",
    "밥": "rice; meal",
    "말": "words; speech; horse",
    "개": "(general counter); dog",
    "명": "(counter for people)",
    "분": "(polite counter for people); minute",
    "살": "(counter for age) years old",
    "권": "(counter for books)",
    "마리": "(counter for animals)",
    "요": "(polite sentence ending)",
    "습니다": "(formal sentence ending)",
}


class KoreanSeeder(BaseSeeder):
    language_code = "ko"

    async def download(self) -> None:
        import backend.services.seeder.seed_korean as _mod

        path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not path.exists():
            self.logger.warning(
                "Korean frequency file not found at %s — run "
                "source_data --language ko --source kaikki", path
            )

    async def transform(self) -> list[dict]:
        import backend.services.seeder.seed_korean as _mod

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
                if word in KO_CURATED:
                    translation = KO_CURATED[word]
                elif translation.endswith(":"):
                    translation = translation[:-1].strip()
                if not word or not translation or word in seen:
                    continue
                seen.add(word)
                rank = int(row["rank"])
                records.append({
                    "word": word,
                    "reading": None,
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

        self.logger.info(f"Transformed {len(records)} Korean words")
        return records
