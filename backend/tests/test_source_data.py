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

    def test_unknown_words_penalized(self):
        ranks = {"ev": 10}
        assert sentence_difficulty("Ev xyzzy", ranks, lambda w: w) == 99999

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

    def test_write_frequency_tsv_roundtrip(self, tmp_path):
        rows = [{"word": "ev", "pos": "n", "gloss": "house"}]
        out = tmp_path / "out.tsv"
        assert write_frequency_tsv(rows, out) == 1
        assert out.read_text(encoding="utf-8").splitlines()[1] == "1\tev\tn\thouse"
