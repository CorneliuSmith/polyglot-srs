#!/usr/bin/env bash
# Regenerate all seed data from the best (CC-licensed) sources.
#
# Run this from a machine with open internet access — kaikki.org and
# tatoeba.org are blocked from some sandboxed environments. The kaikki
# downloads are large (Turkish ~200MB) but cached under data/raw/ so
# re-runs are cheap.
#
# Usage:  ./scripts/refresh_seed_data.sh
set -euo pipefail
cd "$(dirname "$0")/.."

for lang in tr sw yo ha xh; do
    echo "=== $lang: frequency + translations (kaikki/Wiktionary, CC-BY-SA) ==="
    python -m backend.services.seeder.source_data --language "$lang" --source kaikki
    echo "=== $lang: graded example sentences (Tatoeba, CC-BY) ==="
    python -m backend.services.seeder.source_data --language "$lang" --sentences \
        || echo "WARN: $lang sentences failed (Tatoeba unreachable or tiny corpus) — continuing"
done

echo
echo "Done. Load vocabulary into the database with:"
echo "  python -m backend.services.seeder.run --language all"
echo "Load hand-authored grammar curricula (Russian, Turkish):"
echo "  python -m backend.services.seeder.seed_grammar --language all"
echo "AI-generate a curriculum for a language without one (NLP-validated drills):"
echo "  python -m backend.services.seeder.generate_curriculum --language sw --generate"
echo "Fill AI grammar explanations for points that lack them:"
echo "  python -m backend.services.seeder.generate_grammar --language ru --generate"
