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
RUN pip install --no-cache-dir .

# Model/data downloads the app expects at runtime:
#  - spaCy English model (lemmatization, POS)
#  - WordNet + multilingual WordNet (English definitions)
#  - camel-tools light data (Arabic morphology; the app degrades to
#    diacritic-folding if this is absent, hence the tolerant ||)
RUN python -m spacy download en_core_web_sm \
    && python -m nltk.downloader -d /usr/local/share/nltk_data wordnet omw-1.4 \
    && (camel_data -i light || echo "camel data skipped — Arabic uses fallback grading")

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# Shell form so ${PORT} from the platform expands (DO/Render set it).
CMD uvicorn backend.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8080}
