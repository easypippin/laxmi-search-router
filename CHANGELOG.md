# Changelog

All notable changes to the Hermes web-search-plus plugin are documented here.

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
