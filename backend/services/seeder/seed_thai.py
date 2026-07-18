"""Thai vocabulary seeder.

Same rank/word/pos/en TSV as the generic tier (HermitDave th list + kaikki
Thai extract), with curated glosses overriding the kaikki noise on the
high-frequency band — the extract glosses ใช่ ("yes") via a negation sense
and buries other function words in dictionary-speak. Thai has no inflection,
so there is no lemma folding to worry about; readings (romanization with
tones) are deferred to the native-reviewer era rather than shipped wrong.
"""
import csv
import json

from .base import DATA_DIR, BaseSeeder  # noqa: F401 — re-exported so tests can patch it

FREQ_FILENAME = "th_frequency.tsv"

# Curated English glosses for the most frequent words where the kaikki
# extract misleads. Flagged for native review with the rest of the tier.
TH_CURATED: dict[str, str] = {
    "ใช่": "yes; that's right",
    "ไม่": "no; not",
    "ครับ": "(male polite particle)",
    "ค่ะ": "(female polite particle, statements)",
    "คะ": "(female polite particle, questions)",
    "ผม": "I (male); hair (of the head)",
    "ฉัน": "I (female / informal)",
    "คุณ": "you (polite); Mr/Ms",
    "เขา": "he; she; they",
    "เรา": "we; us",
    "มัน": "it (things/animals)",
    "ที่": "at; that/which (relative); place",
    "จะ": "(future marker) will",
    "ได้": "can; get; (past attainment)",
    "แล้ว": "already; and then",
    "อยู่": "to be (somewhere); (progressive marker)",
    "เป็น": "to be (a role or category)",
    "คือ": "to be (defining); namely",
    "มี": "to have; there is",
    "ไป": "to go",
    "มา": "to come",
    "กิน": "to eat",
    "ทำ": "to do; to make",
    "พูด": "to speak",
    "รู้": "to know (facts)",
    "ไหม": "(yes/no question particle)",
    "ก็": "then; also; well…",
    "ว่า": "that (opens a clause); to say",
    "ของ": "of; belonging to; thing",
    "และ": "and",
    "หรือ": "or",
    "กับ": "with",
    "ให้": "to give; for; to let",
    "ต้อง": "must; have to",
    "อยาก": "to want to",
    "เคย": "to have ever; used to",
    "กำลัง": "(progressive marker); strength",
    "ยัง": "still; yet",
    "มาก": "very; a lot",
    "นี่": "this (here)",
    "นั่น": "that (there)",
    "อะไร": "what",
    "ที่ไหน": "where",
    "ใคร": "who",
    "ทำไม": "why",
    "เมื่อไหร่": "when",
    "เท่าไหร่": "how much",
    "ดี": "good",
    "สวย": "beautiful",
    "อร่อย": "delicious",
    "ร้อน": "hot",
    "เย็น": "cool; cold; evening",
    "ใหญ่": "big",
    "เล็ก": "small",
    "แพง": "expensive",
    "ถูก": "cheap; correct; (passive marker for misfortunes)",
    "น้ำ": "water; liquid",
    "ข้าว": "rice; food; meal",
    "บ้าน": "house; home",
    "คน": "person; (classifier for people)",
    "ตัว": "body; (classifier for animals and clothes)",
    "อัน": "(classifier for small things)",
    "เล่ม": "(classifier for books)",
    "วัน": "day",
    "ปี": "year",
    "เวลา": "time",
    "หน่อย": "a little; (request softener)",
    "นะ": "(softening particle) okay?",
    "สิ": "(urging particle) go on!",
    "ขอ": "may I have; to ask for",
    "ช่วย": "to help; please (do for me)",
}


class ThaiSeeder(BaseSeeder):
    language_code = "th"

    async def download(self) -> None:
        import backend.services.seeder.seed_thai as _mod

        path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not path.exists():
            self.logger.warning(
                "Thai frequency file not found at %s — run "
                "source_data --language th --source kaikki", path
            )

    async def transform(self) -> list[dict]:
        import backend.services.seeder.seed_thai as _mod

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
                if word in TH_CURATED:
                    translation = TH_CURATED[word]
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

        self.logger.info(f"Transformed {len(records)} Thai words")
        return records
