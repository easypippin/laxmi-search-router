# Changelog

## [1.5.0] - 2026-04-24

### Added
- **Linkup provider** — source-grounded search with citations and fact-check signals. New regex dict `LINKUP_SOURCE_SIGNALS` (6 groups), bearer auth, parses both sourced-answer and standard search results.
- **Firecrawl provider** — web search with scrape-ready structured content. Scoring: `discovery_score + research_score * 0.35 + recency_score * 0.25`.
- Helper `load-env-file` supports plugin-local and legacy parent `.env` paths.

### Changed
- Provider priority order: tavily → linkup → querit → exa → firecrawl → perplexity → brave → serper → you → searxng.

### Credits
- Thanks @wysiecla for the contribution!

All notable changes to the Hermes web-search-plus plugin are documented here.

---

## [1.4.0] — 2026-04-23

### Added
- **Brave Search provider** — new independent search index with generous free tier (2000 queries/month). Huge thanks to **@Wysie** for the full implementation (#4). Reduces reliance on Serper/Tavily and adds a strong fallback when Google-backed providers rate-limit.
- `BRAVE_API_KEY` env support + `.env.template` entry + README provider matrix update (also @Wysie)
- `tests/test_tie_breaker.py` — unit coverage for the SHA-256 deterministic tie-breaker (`_choose_tie_winner`): single-winner passthrough, same-query stability, distribution fairness across 200 queries, fallback without priority list

### Fixed
- Hermes `main` branch compatibility: plugin now survives the updated toolset resolution in Hermes core (thanks again **@Wysie**, #4)

### Contributors
- **@Wysie** — Brave provider + Hermes main compat (PR #4). Second merged PR from Wysie after the virtualenv docs fix in 1.3.1. Top external contributor 🏆

---

## [1.3.1] — 2026-04-23

### Fixed
- Plugin `.env` file now loads on module import, ensuring API keys are available at tool registration time (thanks @josh-clarke, #1)
- `plugin.yaml` metadata: corrected `requires_env` schema and Hermes repo link

### Added
- MIT license file
- README: Quick Start section, routing transparency, adaptive fallback explanation
- Docs: Hermes virtualenv setup clarification to prevent dependency-install-in-wrong-env footgun (thanks @Wysie, #3)

---

## [1.3.0] — 2026-03-17

### Added
- `time_range` parameter: filter results by recency (`day`, `week`, `month`, `year`)
- `include_domains` parameter: whitelist specific domains (e.g. `["arxiv.org"]`)
- `exclude_domains` parameter: blacklist specific domains (e.g. `["reddit.com"]`)
- `you` added to provider enum (was missing from schema)
- Feature parity table in README

### Changed
- Timeout increased from 65s to **75s** (aligned with OpenClaw plugin)
- README: install guide, full parameter table, examples, architecture, feature parity table

### Notes
- Now fully feature-parity with [OpenClaw web-search-plus-plugin](https://github.com/robbyczgw-cla/web-search-plus-plugin) main branch

---

## [1.2.0] — 2026-03-17

### Added
- `depth` parameter for Exa deep research modes:
  - `deep`: multi-source synthesis (4-12s latency)
  - `deep-reasoning`: cross-document reasoning and analysis (12-50s latency)
- Timeout increased from 30s to 65s to support long-running deep-reasoning queries
- Full README with routing table, parameter docs, examples, architecture section
- CHANGELOG

### Fixed
- Handler now correctly unpacks input dict passed by Hermes registry
  (was causing "expected str, bytes or os.PathLike object, not dict" on all tool calls)
- `depth` parameter name aligned with OpenClaw plugin (was `exa_depth` in initial port)

### Notes
- Synced with [OpenClaw@908b145](https://github.com/robbyczgw-cla/web-search-plus-plugin/commit/908b14529230b1b300e44c6dd2cc8171833c1abb)

---

## [1.1.0] — 2026-03-17

### Fixed
- Plugin handler dict-unpacking bug: Hermes registry passes full input dict as first
  positional argument, not keyword args. Added `isinstance(args_or_query, dict)` check.

---

## [1.0.0] — 2026-03-17

### Added
- Initial Hermes plugin port of web-search-plus from OpenClaw TypeScript plugin
- Auto-routing across Serper, Tavily, Exa, Querit, Perplexity, SearXNG
- `provider` parameter to force a specific provider
- `count` parameter for result count (1-20)
- Hermes plugin registration via `register(ctx)` in `__init__.py`
