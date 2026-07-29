#!/usr/bin/env bash
# Seed one or more languages end to end, in the order the data depends on.
#
#   ./scripts/seed_language.sh he la fa id tl
#   ./scripts/seed_language.sh all
#
# Order matters. Vocabulary first (grammar drills are matched against words
# that must already exist), grammar second. Both steps are idempotent: they
# UPSERT, they keep ids stable so learners' progress survives, and they never
# overwrite anything a human has curated — text diffs on curated points go to
# the review queue instead.
#
# Requires DATABASE_URL. Run the migrations FIRST (supabase db push): the
# languages themselves are rows created by migration, and seeding a language
# whose row does not exist yet fails with "language not found".
set -euo pipefail
cd "$(dirname "$0")/.."

if [ $# -eq 0 ]; then
    echo "usage: $0 <language-code>... | all" >&2
    exit 64
fi

if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL is not set." >&2
    exit 78
fi

for lang in "$@"; do
    echo
    echo "=============================================================="
    echo "  $lang"
    echo "=============================================================="

    echo "--- vocabulary (frequency list -> vocabulary_items) ---"
    python -m backend.services.seeder.run --language "$lang"

    echo "--- grammar (points + drills + one content_list per level) ---"
    python -m backend.services.seeder.seed_grammar --language "$lang"
done

echo
echo "Done. Two things this does NOT do, on purpose:"
echo "  * Example sentences — needs a harvested corpus:"
echo "      python -m backend.services.seeder.seed_sentences --language <code>"
echo "  * AI gap-fill (definitions, extra vocab, translations) — costs money:"
echo "      python -m backend.services.seeder.generate_content -l <code> -k definitions --max 200"
