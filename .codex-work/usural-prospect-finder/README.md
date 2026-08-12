# USURAL Prospect Finder

USURAL Prospect Finder is a production-oriented internal system for finding and ranking businesses with evidence of meaningful website, SEO, or digital modernization opportunities. It favors prospect quality, explainability, and repeatable analysis over collection volume.

This repository contains the **Phase 2 business discovery engine**. It can execute configured search queries through the replaceable Brave Search provider, normalize and classify results, preserve every observation, and produce unique company-domain candidates. It does not crawl candidate websites or calculate production scores.

## Architecture

The application is a modular monolith with a `src/` package layout:

```text
discovery → domain resolution → crawling → fact extraction → analyzers
          → persisted signals → scoring → persistence → reporting
```

Core dataclasses are infrastructure-independent. Protocol-based ports define discovery, crawlers, analyzers, enrichers, scorers, providers, and persistence. `SQLiteRepository` is the initial persistence adapter; pipeline dependencies are passed explicitly rather than resolved through global state.

Analyzers emit typed `Signal` evidence rather than opaque scores. Scorers are pure consumers of stored signals and cannot fetch external resources. A score stores its confidence, explanatory reason, and contributing signal IDs, making the chain from observation to commercial recommendation auditable.

Score and confidence answer different questions: score measures the magnitude or desirability of an opportunity, while confidence measures how strongly the available evidence supports that estimate. A high score based on weak evidence must remain distinguishable from a high-confidence result.

## Persistence

SQLite is the primary Phase 1 store; CSV and JSON are secondary reporting formats. Explicitly ordered, transactional migrations create normalized tables for businesses, websites, pages, contacts, audits, signals, scores, and discovery candidates. Foreign keys preserve the evidence graph. Composite indexes cover website/category/time and website/name/time signal history; focused indexes cover audit, business, signal name/category/time, and canonical domain. Past audits are retained. Repository protocols keep application logic portable to PostgreSQL.

Signal values and metadata use JSON because values may be boolean, numeric, textual, date-like, or structured. Important identifiers, categories, weights, confidence, timestamps, and relationships remain queryable columns rather than being hidden in one blob.

## Project structure

- `src/usural_prospect_finder/models`: typed domain entities and enums
- `discovery`, `crawling`, `analyzers`, `enrichment`, `scoring`: domain/application boundaries
- `providers`: normalized external-service ports
- `storage`: repository protocol, schema, migrations, SQLite adapter
- `pipeline`: explicitly injected orchestration skeletons
- `reporting`: stable CSV/JSON projections
- `utils`: URL/domain safety, strict serialization, configuration hashing, retries, logging, text and dates
- `config`: versioned YAML policy examples
- `docs/architecture.md`: lightweight architecture decisions and invariants
- `tests/unit`, `tests/integration`, `tests/websites`: offline test layers and future saved-site fixtures

## Installation

Python 3.13 or newer is required.

```bash
cd usural-prospect-finder
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
prospect-finder init-db
```

Environment variables use the `UPF_` prefix. Relative paths resolve from the installed project root, not the caller's current directory. `.env.example` documents runtime paths, logging, user agent, timeouts, concurrency, and reserved provider keys. The application reads process environment variables; a shell or deployment platform may load `.env`. YAML files configure scoring, exclusions, technology fingerprints, and category profiles. Secrets must stay outside version control.

## CLI

```bash
prospect-finder init-db [--database PATH]                 # functional
prospect-finder discover --location Barcelona --category architects
prospect-finder audit --domain example.com
prospect-finder run --location Barcelona --category architects --target 100
prospect-finder rescore [--domain example.com]
prospect-finder export --format csv
prospect-finder inspect example.com
```

`init-db`, `discover`, `audit`, `rescore`, and `inspect` are implemented. Discovery requires
`UPF_SEARCH_API_KEY` and prints counts derived from the provider response; it never fabricates
results. `run` and `export` remain deliberate placeholders.

## Production Readiness Status

The architecture foundation, Phase 2 discovery pipeline, and Phase 3 selective static crawler are
implemented. Crawling produces objective page, contact, structured-data, content-freshness, image,
and technology-reference evidence. It does not calculate redesign, modernity, SEO, or opportunity
scores, so the application is not yet suitable for final prospect qualification.

## Phase 4 redesign scoring

`rescore` reads only persisted Phase 3 audits and Signals; it does not instantiate the crawler or
make network requests. It appends Website Modernity and Redesign Need score history with scorer and
configuration provenance. `inspect` displays the latest analysis and evidence-backed reasons.

The six normalized dimensions are legacy technology risk (100 = high risk), front-end modernity,
responsive/image modernity, performance-oriented markup, content freshness, and technical
reliability (100 = good for the latter five). Confidence is an evidence-coverage measure and is
separate from the score. Sparse or failed crawls are explicitly `INSUFFICIENT_EVIDENCE`.

All Phase 4 weights and gates in `config/redesign.yaml` are `INITIAL_UNCALIBRATED`. Scores are
deterministic heuristics intended for human review, not statistically calibrated predictions.

## Phase 3 crawler behavior

`prospect-finder audit --domain example.com` resolves a public homepage, checks robots.txt, and
selects a conservative multilingual set of contact, about, team, service, project, news/blog, legal,
and privacy pages. Every request and redirect target is checked both syntactically and through DNS
against non-public address ranges. Redirects, request time, response bytes, total pages, concurrency,
and per-domain delay are bounded through `UPF_` settings.

Fetched HTML is parsed in memory and discarded. The database retains page diagnostics, content
length and SHA-256 hash, extracted contacts, and structured Signals. This bounded strategy supports
audit comparison without retaining large response bodies. Content dates and copyright years are
stored strictly as content-freshness evidence and are never interpreted as redesign dates.

## Development and testing

Tests are offline and use temporary SQLite databases. Future crawler fixtures belong in `tests/websites/`, with one directory per synthetic or permission-safe saved site and a manifest describing source, capture date, expected page roles, and intended assertions.

```bash
ruff check .
mypy src
pytest
```

## Phase 2 discovery behavior and limitations

Category YAML supplies localized labels, synonyms, and query templates. Results flow through deterministic URL/domain normalization, multi-signal classification, filtering, observation persistence, then canonical-domain deduplication. Social, directory, government, marketplace, news, blog/article, and document results are retained as filtered observations with reasons. Repeated company results preserve each query, position, timestamp, and provider source.

Classification uses layered, deterministic evidence: configured high-confidence domains,
government/TLD and document/path structure, provider type metadata, hostname and title/snippet
phrases, plus category-specific company terms. Legal discovery additionally distinguishes ranking,
network, recruitment, marketplace, directory, and editorial results. Every decision records a
confidence value and evidence reasons in observation metadata. Known-domain reputation is a
high-confidence input, but generic signals cover previously unseen platforms. For a configured
category, a titled HTTP(S) result enters the company pool only when its title, snippet, or hostname
also supplies category-specific company evidence; otherwise it remains `UNKNOWN` for review.

The discovery provider currently returns at most 20 results per query due to the upstream API
contract. Discovery itself has no pagination; homepage redirects and DNS/network safety are handled
by the Phase 3 audit path.

## Roadmap

Phase 1 intentionally contains no search integration, Google Maps support, detailed or browser crawling, DNS-based SSRF validation, contact/review/social extraction, WordPress or technology detection, SEO/modernity/performance/accessibility audits, business enrichment, calibrated scoring, GUI, machine learning, LLM, outreach, or live prospect data.

Planned work:

1. **Phase 3 — Crawling & Contact Extraction:** respectful async crawling, selective pages, contacts, and structured business facts.
3. **Phase 4 — Website Technology & Modernity:** WordPress/theme/plugin, legacy technology, freshness, and modernization signals.
4. **Phase 5 — SEO Audit:** page/site technical, local, and multilingual SEO evidence.
5. **Phase 6 — Business Quality & Enrichment:** activity, capacity, reviews, social, and team/company signals.
6. **Phase 7 — Opportunity Scoring:** configurable calibrated weights, composable eligibility gates, classifications, and reasons.
7. **Phase 8 — Calibration:** labelled prospects, evaluation, threshold tuning, and false-positive analysis.
8. **Phase 9 — Optional Dashboard / CRM:** only after the engine is validated.
