"""English vocabulary seeder using WordNet definitions and a bundled frequency list."""
import csv
import json
import logging

from .base import BaseSeeder, DATA_DIR

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

        records = []
        for rank, word in freq_words:
            # Look up WordNet synsets for definition
            synsets = wn.synsets(word)
            if not synsets:
                # Skip words with no synsets (function words, unknown terms)
                continue

            # Use first synset for primary definition
            primary = synsets[0]
            definition = primary.definition()
            wn_pos = pos_map.get(primary.pos(), None)

            # spaCy POS and lemma if available
            pos = wn_pos
            morphology = {"lemma": word}
            if nlp:
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

        self.logger.info(f"Transformed {len(records)} English words")
        return records
