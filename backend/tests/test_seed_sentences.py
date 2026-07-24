"""Sentence TSV parsing — including the optional per-row `source` column that
lets an extractor-authored 'ai' example land reviewed=false."""

from backend.services.seeder.seed_sentences import _read_rows


def _write(tmp_path, text):
    p = tmp_path / "es_sentences.tsv"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_read_rows_without_source_column(tmp_path):
    path = _write(tmp_path, "word\tsentence\ttranslation\ngato\tEl gato duerme.\tThe cat sleeps.\n")
    rows = list(_read_rows(path))
    assert rows[0]["word"] == "gato"
    assert rows[0]["source"] is None  # absent → seeder uses the file default


def test_read_rows_passes_source_through(tmp_path):
    path = _write(
        tmp_path,
        "word\tsentence\ttranslation\tsource\n"
        "gato\tMi gato es negro.\tMy cat is black.\tai\n"
        "casa\tLa casa es grande.\tThe house is big.\t\n",
    )
    by_word = {r["word"]: r for r in _read_rows(path)}
    assert by_word["gato"]["source"] == "ai"      # → reviewed=false on load
    assert by_word["casa"]["source"] is None       # blank → file default


def test_reviewed_gate_derivation():
    # The rule _seed_file applies: an 'ai' row is hidden (reviewed=false); every
    # other provenance is shown (reviewed=true).
    def reviewed(row_source, file_default):
        return (row_source or file_default) != "ai"

    assert reviewed("ai", "curated") is False
    assert reviewed(None, "curated") is True
    assert reviewed(None, "tatoeba") is True
    assert reviewed("human", "curated") is True
