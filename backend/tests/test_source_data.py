"""Tests for the data sourcing pipeline — fixtures only, no network calls."""
from collections import Counter

import pytest

from backend.services.seeder.source_data import (
    build_sentence_rows,
    build_swahili_rows,
    build_turkish_rows,
    corpus_word_counts,
    parse_freedict_tei,
    parse_hermitdave,
    parse_kaikki_jsonl,
    parse_tatoeba_links,
    parse_tatoeba_sentences,
    sentence_difficulty,
    write_frequency_tsv,
)

TEI_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" version="5.0">
  <text><body>
    <entry xml:id="abiria">
      <form xml:lang="sw"><orth>abiria</orth></form>
      <xr type="plural-form"><ref target="#maabiria">maabiria</ref></xr>
      <gramGrp><pos>n</pos></gramGrp>
      <sense><def>passenger</def></sense>
    </entry>
    <entry xml:id="acha">
      <form xml:lang="sw"><orth>acha</orth></form>
      <gramGrp><pos>v</pos></gramGrp>
      <sense n="1"><def>leave</def></sense>
      <sense n="2"><def>quit, stop doing sth</def></sense>
    </entry>
    <entry>
      <form><orth>Alman</orth></form>
      <sense><cit type="trans"><quote>German</quote></cit></sense>
    </entry>
    <entry>
      <form><orth>boş</orth></form>
      <sense></sense>
    </entry>
  </body></text>
</TEI>
"""


class TestParseFreedictTei:
    @pytest.fixture
    def entries(self, tmp_path):
        p = tmp_path / "dict.tei"
        p.write_text(TEI_SAMPLE, encoding="utf-8")
        return parse_freedict_tei(p)

    def test_def_senses_joined(self, entries):
        assert entries["acha"]["gloss"] == "leave; quit, stop doing sth"
        assert entries["acha"]["pos"] == "v"

    def test_cit_quote_translations(self, entries):
        assert entries["alman"]["gloss"] == "German"
        assert entries["alman"]["pos"] is None

    def test_plural_xr_captured(self, entries):
        assert entries["abiria"]["plural"] == "maabiria"

    def test_glossless_entries_skipped(self, entries):
        assert "boş" not in entries


class TestParseHermitdave:
    def test_parses_rank_word_count(self, tmp_path):
        p = tmp_path / "freq.txt"
        p.write_text("bir 1000000\nve 900000\nmalformed-line\nev 5000\n")
        rows = parse_hermitdave(p)
        assert rows[0] == (1, "bir", 1000000)
        assert rows[2] == (3, "ev", 5000)
        assert len(rows) == 3


class TestParseKaikki:
    def test_streams_and_filters(self, tmp_path):
        p = tmp_path / "kaikki.jsonl"
        p.write_text(
            '{"word": "ev", "pos": "noun", "senses": [{"glosses": ["house", "home"]}]}\n'
            '{"word": "kedi", "pos": "noun", "senses": [{"glosses": ["cat"]}]}\n'
            "not json\n"
            '{"word": "boş", "pos": "adj", "senses": []}\n'
        )
        entries = parse_kaikki_jsonl(p, wanted={"ev"})
        assert entries == {"ev": {"pos": "noun", "gloss": "house; home", "plural": None}}


class TestCorpusWordCounts:
    def test_counts_seg_tokens(self, tmp_path):
        p = tmp_path / "nt.xml"
        p.write_text(
            "<text><body>"
            '<seg id="b.MAT.1.1" type="verse">Yesu akasema neno. Neno jema!</seg>'
            "</body></text>",
            encoding="utf-8",
        )
        counts = corpus_word_counts(p)
        assert counts["neno"] == 2
        assert counts["akasema"] == 1


class TestBuildTurkishRows:
    def test_aggregates_inflected_forms_onto_headword(self):
        freq = [(1, "evde", 500), (2, "ev", 400), (3, "evler", 300), (4, "zzz", 200)]
        dictionary = {"ev": {"pos": "n", "gloss": "house", "plural": None}}
        rows = build_turkish_rows(freq, dictionary)
        assert rows == [{"word": "ev", "pos": "n", "gloss": "house"}]

    def test_orders_by_aggregated_count(self):
        freq = [(1, "su", 100), (2, "evde", 300), (3, "evler", 300)]
        dictionary = {
            "ev": {"pos": "n", "gloss": "house", "plural": None},
            "su": {"pos": "n", "gloss": "water", "plural": None},
        }
        rows = build_turkish_rows(freq, dictionary)
        assert [r["word"] for r in rows] == ["ev", "su"]


class TestBuildSwahiliRows:
    def test_conjugations_fold_onto_stem(self):
        counts = Counter({"akasema": 50, "alisema": 30, "sema": 5, "kitabu": 20})
        dictionary = {
            "sema": {"pos": "v", "gloss": "say", "plural": None},
            "kitabu": {"pos": "n", "gloss": "book", "plural": "vitabu"},
        }
        rows = build_swahili_rows(counts, dictionary)
        assert rows[0]["word"] == "sema"  # 85 aggregated vs 20
        assert rows[1]["word"] == "kitabu"


class TestSentencePipeline:
    def test_parse_tatoeba_files(self, tmp_path):
        s = tmp_path / "sent.tsv"
        s.write_text("10\ttur\tEv güzel.\n11\ttur\tKedi geldi.\n")
        ln = tmp_path / "links.tsv"
        ln.write_text("10\t90\n11\t91\n")
        assert parse_tatoeba_sentences(s) == {10: "Ev güzel.", 11: "Kedi geldi."}
        assert parse_tatoeba_links(ln) == [(10, 90), (11, 91)]

    def test_difficulty_is_rarest_word_rank(self):
        ranks = {"ev": 10, "güzel": 200}
        assert sentence_difficulty("Ev güzel", ranks, lambda w: w) == 200

    def test_one_unknown_word_tolerated_as_hard(self):
        # One out-of-list word no longer poisons the sentence (the old
        # all-or-nothing drop left Hindi with 427 sentences and Catalan at
        # 17% coverage) — it scores hard-but-usable instead.
        ranks = {"ev": 10}
        assert sentence_difficulty("Ev xyzzy", ranks, lambda w: w) == 19999

    def test_two_unknown_words_penalized(self):
        ranks = {"ev": 10}
        assert sentence_difficulty("Ev xyzzy plugh", ranks, lambda w: w) == 99999

    def test_all_unknown_penalized(self):
        assert sentence_difficulty("xyzzy", {"ev": 10}, lambda w: w) == 99999

    def test_single_letter_clitics_ignored(self):
        # l'home tokenizes to "l" + "home": the bare clitic is not vocabulary
        ranks = {"home": 50}
        assert sentence_difficulty("L'home", ranks, lambda w: w) == 50

    def test_build_sentence_rows_prefers_easy_sentences(self):
        target = {1: "Ev güzel.", 2: "Ev karmaşık."}
        eng = {90: "The house is beautiful.", 91: "The house is complex."}
        links = [(1, 90), (2, 91)]
        ranks = {"ev": 10, "güzel": 50, "karmaşık": 5000}
        rows = build_sentence_rows(target, eng, links, ranks, lambda w: w, per_word=1)
        ev_rows = [r for r in rows if r["word"] == "ev"]
        assert len(ev_rows) == 1
        assert ev_rows[0]["sentence"] == "Ev güzel."
        assert ev_rows[0]["difficulty_rank"] == 50

    def test_build_sentence_rows_never_bridges_diacritics(self):
        # Beta bug: with the accent-folding lemmatizer, "Es él." nominated
        # itself as an example for the ARTICLE card 'el' (and año-sentences
        # for 'ano'). A fold-only lemma match must not link; an exact token
        # and a real morphology fold still do.
        from backend.services.nlp.latin_base import SpanishNLP

        target = {1: "Es él.", 2: "¿Cómo está el tiempo?"}
        eng = {90: "It is he.", 91: "How's the weather?"}
        links = [(1, 90), (2, 91)]
        ranks = {"el": 1, "es": 2, "cómo": 3, "está": 4, "tiempo": 5}
        rows = build_sentence_rows(
            target, eng, links, ranks, SpanishNLP().lemmatize, per_word=5
        )
        el_sentences = {r["sentence"] for r in rows if r["word"] == "el"}
        assert el_sentences == {"¿Cómo está el tiempo?"}

    def test_build_sentence_rows_keeps_real_lemma_matches(self):
        # A genuine lemmatizer fold (кошку -> кошка) still links.
        target = {1: "Я вижу кошку."}
        eng = {90: "I see the cat."}
        ranks = {"кошка": 10, "я": 1, "вижу": 5}
        lemmatize = lambda w: "кошка" if w == "кошку" else w  # noqa: E731
        rows = build_sentence_rows(
            target, eng, [(1, 90)], ranks, lemmatize, per_word=5
        )
        assert any(r["word"] == "кошка" for r in rows)

    def test_write_frequency_tsv_roundtrip(self, tmp_path):
        rows = [{"word": "ev", "pos": "n", "gloss": "house"}]
        out = tmp_path / "out.tsv"
        assert write_frequency_tsv(rows, out) == 1
        assert out.read_text(encoding="utf-8").splitlines()[1] == "1\tev\tn\thouse"


class TestEnglishPipeline:
    """English-as-target: reversed Tatoeba links + kaikki translation arrays."""

    def test_reversed_links_make_english_the_sentence(self):
        from backend.services.seeder.source_data import build_sentence_rows

        eng = {10: "I drink water.", 11: "The cat sleeps."}
        spa = {20: "Bebo agua.", 21: "El gato duerme."}
        # Tatoeba spa-eng links are (spa_id, eng_id); the English build
        # reverses them so the English side is the card's sentence.
        links = [(20, 10), (21, 11)]
        reversed_links = [(e, s) for (s, e) in links]
        rows = build_sentence_rows(
            eng, spa, reversed_links,
            {"water": 3, "cat": 5, "the": 1, "i": 2, "drink": 4, "sleeps": 6},
            lemmatize=lambda w: w,
            per_word=3,
        )
        by_word = {r["word"]: r for r in rows}
        assert by_word["water"]["sentence"] == "I drink water."
        assert by_word["water"]["translation"] == "Bebo agua."

    def test_parse_english_kaikki_translations(self, tmp_path):
        import json as _json

        from backend.services.seeder.source_data import (
            parse_english_kaikki_translations,
        )

        entries = [
            # noun entry: primary sense = the LARGEST translation table
            {"word": "time", "pos": "noun", "senses": [
                {"translations": [{"code": "de", "word": "Mal"}]},  # marginal
                {"translations": [
                    {"code": "es", "word": "tiempo"},
                    {"code": "fr", "word": "temps"},
                    {"code": "de", "word": "Zeit"},
                    {"code": "xx", "word": "ignored"},
                ]},
            ]},
            # verb entry: kept separately, POS-keyed
            {"word": "time", "pos": "verb", "senses": [
                {"translations": [{"code": "es", "word": "cronometrar"}]},
            ]},
            # letter/symbol entries never contribute
            {"word": "time", "pos": "character", "translations": [
                {"code": "es", "word": "junk"},
            ]},
            {"word": "obscureword", "pos": "noun", "translations": [
                {"code": "es", "word": "nunca"},
            ]},
        ]
        path = tmp_path / "en_kaikki.jsonl"
        path.write_text(
            "\n".join(_json.dumps(e) for e in entries), encoding="utf-8"
        )
        out = parse_english_kaikki_translations(
            path, wanted={"time"}, locales={"es", "fr", "de"}
        )
        assert out == {"time": {
            "noun": {"es": "tiempo", "fr": "temps", "de": "Zeit"},
            "verb": {"es": "cronometrar"},
        }}

    def test_sentences_tsv_locale_column_roundtrip(self, tmp_path):
        import csv as _csv

        from backend.services.seeder.source_data import write_sentences_tsv

        rows = [{
            "word": "water", "sentence": "I drink water.",
            "translation": "Bebo agua.", "difficulty_rank": 4,
            "translation_locale": "es",
        }]
        out = tmp_path / "en_sentences.tsv"
        assert write_sentences_tsv(rows, out, locale_column=True) == 1
        with open(out, encoding="utf-8") as f:
            row = next(_csv.DictReader(f, delimiter="\t"))
        assert row["translation_locale"] == "es"
        assert row["translation"] == "Bebo agua."
