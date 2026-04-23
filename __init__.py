"""
web-search-plus — Hermes Plugin v1.3.0
Multi-provider web search with intelligent auto-routing.
Ported from robbyczgw-cla/web-search-plus-plugin (OpenClaw) to Hermes Plugin API.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, List, Optional

_SEARCH_SCRIPT = Path(__file__).parent / "search.py"
_TOOLSET_NAME = "web-search-plus"
_PROVIDER_ENV_KEYS = [
    "SERPER_API_KEY",
    "BRAVE_API_KEY",
    "TAVILY_API_KEY",
    "EXA_API_KEY",
    "QUERIT_API_KEY",
    "PERPLEXITY_API_KEY",
    "YOU_API_KEY",
    "SEARXNG_INSTANCE_URL",
]


def _load_plugin_env() -> None:
    """Load the plugin's .env file into os.environ if keys aren't already set."""
    plugin_env = Path(__file__).parent / ".env"
    if not plugin_env.exists():
        return
    for line in plugin_env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if val and not val.startswith("***") and key not in os.environ:
            os.environ[key] = val

# Load plugin .env on import
_load_plugin_env()


def _run_search(
    query: str,
    provider: str = "auto",
    count: int = 5,
    exa_depth: str = "normal",
    time_range: Optional[str] = None,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
) -> dict:
    """Call search.py subprocess and return parsed JSON result."""
    cmd = [
        sys.executable,
        str(_SEARCH_SCRIPT),
        "--query", query,
        "--provider", provider,
        "--max-results", str(count),
        "--compact",
    ]
    if exa_depth != "normal":
        cmd += ["--exa-depth", exa_depth]
    if time_range and time_range != "none":
        cmd += ["--time-range", time_range]
    if include_domains:
        cmd += ["--include-domains"] + include_domains
    if exclude_domains:
        cmd += ["--exclude-domains"] + exclude_domains

    env = os.environ.copy()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=75,
            env=env,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            try:
                return json.loads(stderr)
            except json.JSONDecodeError:
                return {"error": stderr or "Search failed", "provider": provider, "query": query, "results": []}

        return json.loads(result.stdout)

    except subprocess.TimeoutExpired:
        return {"error": "Search timed out after 75s", "provider": provider, "query": query, "results": []}
    except Exception as e:
        return {"error": str(e), "provider": provider, "query": query, "results": []}


def _format_results(data: dict) -> str:
    """Format search results for LLM consumption."""
    if "error" in data and not data.get("results"):
        return f"Search error: {data['error']}"

    results = data.get("results", [])
    provider = data.get("provider", "unknown")
    routing = data.get("routing", {})
    answer = data.get("answer", "")
    cached = data.get("cached", False)

    lines = []

    if routing.get("auto_routed"):
        confidence = routing.get("confidence_level", "")
        reason = routing.get("reason", "")
        lines.append(f"[Provider: {provider} | auto-routed | {confidence} confidence | {reason}]")
    else:
        lines.append(f"[Provider: {provider}{' | cached' if cached else ''}]")

    if answer:
        lines.append(f"\nAnswer: {answer}\n")

    for i, r in enumerate(results, 1):
        title = r.get("title", "No title")
        url = r.get("url", "")
        snippet = r.get("snippet", "")
        lines.append(f"{i}. {title}")
        if url:
            lines.append(f"   {url}")
        if snippet:
            lines.append(f"   {snippet}")
        lines.append("")

    return "\n".join(lines).strip()


def register(ctx: Any) -> None:
    """Register web_search_plus tool with Hermes plugin system."""

    schema = {
        "name": "web_search_plus",
        "description": (
            "Multi-provider web search with intelligent auto-routing. "
            "Automatically selects the best provider based on query intent: "
            "Serper for shopping/news/facts, Tavily for research/analysis, "
            "Exa for semantic discovery, Querit for multilingual/real-time, "
            "Perplexity for direct answers. "
            "Set depth='deep' for Exa multi-source synthesis, 'deep-reasoning' for complex cross-document analysis. "
            "Override with provider param if needed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "provider": {
                    "type": "string",
                    "enum": ["auto", "serper", "brave", "tavily", "exa", "querit", "perplexity", "you", "searxng"],
                    "description": "Search provider. Use 'auto' for intelligent routing (default). Brave and Serper share generic web-search intents and ties are distributed deterministically per query.",
                    "default": "auto",
                },
                "depth": {
                    "type": "string",
                    "enum": ["normal", "deep", "deep-reasoning"],
                    "description": "Exa search depth: 'deep' synthesizes across sources (4-12s), 'deep-reasoning' for complex cross-document analysis (12-50s). Only applies when routed to Exa.",
                    "default": "normal",
                },
                "count": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20,
                },
                "time_range": {
                    "type": "string",
                    "enum": ["day", "week", "month", "year"],
                    "description": "Filter results by recency. Optional.",
                },
                "include_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Whitelist specific domains (e.g. ['arxiv.org', 'github.com']). Optional.",
                },
                "exclude_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Blacklist specific domains (e.g. ['reddit.com']). Optional.",
                },
            },
            "required": ["query"],
        },
    }

    def handler(args_or_query, provider: str = "auto", count: int = 5, depth: str = "normal",
                time_range: Optional[str] = None, include_domains: Optional[List[str]] = None,
                exclude_domains: Optional[List[str]] = None, **kwargs) -> str:
        # Hermes registry passes the entire input dict as first positional arg
        if isinstance(args_or_query, dict):
            query = args_or_query.get("query", "")
            provider = args_or_query.get("provider", provider)
            count = args_or_query.get("count", count)
            depth = args_or_query.get("depth", depth)
            time_range = args_or_query.get("time_range", time_range)
            include_domains = args_or_query.get("include_domains", include_domains)
            exclude_domains = args_or_query.get("exclude_domains", exclude_domains)
        else:
            query = args_or_query
        data = _run_search(
            query=query,
            provider=provider,
            count=count,
            exa_depth=depth,
            time_range=time_range,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
        )
        return _format_results(data)

    def check_fn() -> bool:
        """Plugin is available if at least one provider credential is configured."""
        return any(os.environ.get(k) for k in _PROVIDER_ENV_KEYS)

    ctx.register_tool(
        name="web_search_plus",
        toolset=_TOOLSET_NAME,
        schema=schema,
        handler=handler,
        check_fn=check_fn,
        requires_env=[],
        description="Multi-provider web search with intelligent auto-routing",
        emoji="🔍",
    )
