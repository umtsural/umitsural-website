# Architecture decisions

This document records the small set of decisions that future phases must preserve unless evidence justifies a deliberate change.

## Modular monolith and CLI-first delivery

The engine remains one deployable Python application with explicit package boundaries. A CLI makes workflows reproducible before any dashboard or CRM is considered. Orchestration receives dependencies explicitly; there is no service locator.

## SQLite-first persistence behind a repository

SQLite is the authoritative V1 store. Domain and pipeline code consume the neutral `Repository` protocol, never connections, rows, cursors, SQL, or SQLite exceptions. The adapter enables foreign keys, WAL and a bounded busy timeout. It offers an explicit transaction context for future audit/page/signal/score batches. Synchronous writes are acceptable now; async orchestration must bound concurrency and move persistence off latency-sensitive loops if measurements justify it.

## Append-only evidence history

Audits are distinct records for every website run. Signals and scores reference an audit; a unique `(audit_id, score_type)` prevents ambiguity within one run while allowing comparisons between runs. Discovery observations retain source, query, position and timestamp rather than globally deduplicating provenance.

## Signals before scores

Analyzers and enrichers produce persisted, typed signals. Scorers consume signals and perform no network access. Signal JSON is strict, deterministic and supports booleans, numbers, strings, null, UTC datetimes, dates, lists and mappings. Unsupported objects fail rather than being stringified.

## Score and confidence are separate

A score expresses magnitude on 0–100; confidence expresses evidence strength on 0–1. Scores retain contributing signal IDs and explanatory text. Initial YAML weights are examples, not calibrated production policy; calibration belongs to Phase 8.

## Stable and deterministic behavior

Enums persist stable string values. Domain timestamps are timezone-aware UTC. Migrations have explicit, ordered integer versions and apply transactionally once. Behavioral configuration hashes normalize key ordering while excluding secrets and machine-specific paths.

## External boundaries and exclusions

Search, reviews and performance services remain behind provider protocols. Crawlers, analyzers and enrichers are asynchronous contracts; SQLite remains synchronous by design. The core includes no ML or LLM dependency, no direct Google scraping, no browser automation, and no outreach behavior.

Phase 2 uses one production Brave Search adapter. Query generation is driven by localized category configuration. Every raw observation is persisted before a separate company-domain projection deduplicates canonical domains, ensuring discovery frequency and query provenance are never lost. Classification uses provider metadata, known-domain policy, host/path patterns, titles, and snippets; it does not inspect page content.
