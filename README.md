# laxmi-search-router

Multi-provider web search HTTP service for the LAxMI fund. Forked from
[robbyczgw-cla/hermes-web-search-plus](https://github.com/robbyczgw-cla/hermes-web-search-plus)
— Hermes plugin shim removed, replaced with a fund-style HTTP service so any
LAxMI bot (jekyl/hyde/scout/herald/etc.) can call it directly.

## What changed vs. upstream

| | Upstream | This fork |
|---|---|---|
| Entry point | Hermes plugin (`__init__.py:register`) | HTTP server (`server.py` on `:3451`) |
| Env loading | reads plugin-local `.env` | inherits from `dotenvx`-decrypted fund env |
| Halt awareness | none | reads `/tmp/fund-state.json`, refuses while halted |
| Caller telemetry | none | exposes search/extract counts via `GET /` |
| Routing engine | `search.py` | unchanged — all credit to upstream for the auto-router |

## Running

```bash
# Standalone
~/.venvs/search-router/bin/python /Users/shaway/laxmi-search-router/server.py

# Via fund.mjs (Phase 1 opt-in — see fund.mjs BOTS array)
node fund.mjs
```

Provider API keys (`SERPER_API_KEY`, `BRAVE_API_KEY`, `TAVILY_API_KEY`,
`EXA_API_KEY`, `QUERIT_API_KEY`, `LINKUP_API_KEY`, `FIRECRAWL_API_KEY`,
`PERPLEXITY_API_KEY`, `YOU_API_KEY`, `SEARXNG_INSTANCE_URL`) are read from
process env. In fund context they come from the encrypted `.env` via dotenvx.
At least one is required; missing keys just disable that provider.

## API

### `GET /` — status

```json
{
  "bot": "search-router",
  "cycle": 14,
  "running": false,
  "last": {"kind": "search", "query": "...", "provider": "tavily", "result_count": 5, "cached": false},
  "providers_configured": ["serper", "brave", "tavily", "exa"],
  "counts": {"search": 12, "extract": 2}
}
```

### `POST /search`

```bash
curl -s localhost:3451/search -H 'Content-Type: application/json' -d '{
  "query": "Aerodrome USDC pool TVL",
  "provider": "auto",
  "count": 5,
  "time_range": "week"
}' | jq
```

Body fields: `query` (required), `provider` (`auto`/`serper`/`brave`/`tavily`/`exa`/`querit`/`linkup`/`firecrawl`/`perplexity`/`you`/`searxng`), `count` (1–20), `depth` (`normal`/`deep`/`deep-reasoning` — Exa only), `time_range` (`day`/`week`/`month`/`year`), `include_domains[]`, `exclude_domains[]`.

Returns the underlying `search.py` JSON: `{provider, results: [...], routing: {...}, cached, ...}`.

### `POST /extract`

```bash
curl -s localhost:3451/extract -H 'Content-Type: application/json' -d '{
  "urls": ["https://example.com/article"],
  "provider": "firecrawl",
  "format": "markdown"
}' | jq
```

### `POST /trigger`

No-op (request/response service has no cycle). Returns `{ok: true}` so the fund
status aggregator and ops-chat treat it like any other bot.

## Calling from a fund bot

```js
const res = await fetch("http://localhost:3451/search", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ query, count: 5, time_range: "week" }),
});
const { results, routing } = await res.json();
```

Python equivalent (see `limitless-bot.py` style):

```python
import requests
r = requests.post("http://localhost:3451/search",
                  json={"query": q, "count": 5}, timeout=80)
data = r.json()
```

## Fund integration notes

- **Port**: 3451 (next free slot in CLAUDE.md ports table — bump that table to 3452 when this lands).
- **Halt-aware**: while `/tmp/fund-state.json.halted == true`, `/search` and `/extract` return 503 with the halt reason. Status endpoint stays up.
- **No money moved**: read-only API calls only. No `DRY_RUN` gate needed.
- **Cost**: free tiers cover normal usage. Heavy callers (deep research, mass extract) can blow through Tavily/Exa monthly limits — provider cooldowns kick in at 1h on failure.
- **Phase**: opt-in. Phase 0 doesn't need it; reactivated bots in Phase 1+ (jekyl/hyde/scout) benefit most.

## Credit

Routing engine (`search.py`, ~3.4k lines) is unchanged from upstream. All
provider integrations, scoring heuristics, cooldowns, and caching logic are
the original author's work. This fork only adds the fund's HTTP/halt/telemetry
shell around it.

## License

MIT — same as upstream.
