# PolyglotSRS backend — the deployable API service.
#
# Why a Dockerfile: PaaS buildpacks (DigitalOcean, Render) key on
# requirements.txt and don't detect a pyproject-only Python repo, and the
# NLP stack (spaCy model, WordNet data, camel-tools) needs build steps a
# buildpack won't run. This image bakes everything in, so the platform
# just runs it.
#
# DigitalOcean App Platform: detected automatically once this file is on
# the deploy branch. Leave build/run commands EMPTY (they're baked in),
# set HTTP port 8080, health check /api/health, and add the env vars from
# docs/DEPLOY.md.

FROM python:3.12-slim

# camel-tools occasionally compiles from source; cmake/build-essential
# make that path work on any base image update.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first for layer caching: the heavy wheels only rebuild
# when pyproject.toml changes, not on every code edit.
COPY pyproject.toml README.md ./
COPY backend ./backend
# Runtime data the API reads from disk (NOT the seed corpora):
#  - Gym manifests. Without this the deployed app had no /app/data at all
#    and every language's Gym showed the "no forms to train" empty state.
#  - Frequency lists, for the collision guard: _collision_surfaces() reads
#    data/<code>_frequency.tsv, and a missing file makes the guard degrade
#    silently to off rather than error. See .dockerignore.
COPY data/gym ./data/gym
COPY data/*_frequency.tsv ./data/
#  - Thai readings. The whole `th` romanisation layer is this lookup table;
#    a missing file degrades to no reading, which looks exactly like the
#    layer never having been built.
#    One glob for every course: th, ar, he and fa today, and whatever comes
#    next without needing this line edited again.
COPY data/*_readings.tsv ./data/
#  - Migration files, so /api/health/schema can diff what this build
#    expects against what the database has. Not applied from here (owner
#    applies them); read-only diagnostics. Without them the check has no
#    expectations and reports ok:true unconditionally — see .dockerignore.
COPY supabase/migrations ./supabase/migrations
RUN pip install --no-cache-dir .

# Build stamp, so /api/health can say WHAT is running. The .git directory
# is not in the build context, so the commit comes in as a build arg when
# the platform provides one (DigitalOcean/Render do not by default — then it
# is null and the build time is the identifying fact). The time is written
# by the build itself, not by the app at boot, so a restart of an old image
# does not masquerade as a fresh deploy.
ARG GIT_SHA=""
ENV BUILD_SHA=${GIT_SHA}
RUN date -u +%Y-%m-%dT%H:%M:%SZ > /app/BUILD_TIME

# Model/data downloads the app expects at runtime:
#  - spaCy English model (lemmatization, POS)
#  - WordNet + multilingual WordNet (English definitions)
# camel-tools (Arabic full morphology) is deliberately NOT installed: it
# pulls torch + transformers (~4 GB) and exhausted the PaaS build machine.
# ArabicNLP degrades to diacritic-folding grading without it.
RUN python -m spacy download en_core_web_sm \
    && python -m nltk.downloader -d /usr/local/share/nltk_data wordnet omw-1.4

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# Shell form so ${PORT} from the platform expands (DO/Render set it).
CMD uvicorn backend.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8080}
