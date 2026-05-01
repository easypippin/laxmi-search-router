"""
laxmi-search-router — multi-provider web search HTTP service.

Forked from robbyczgw-cla/hermes-web-search-plus. Strips the Hermes plugin shim
and exposes the same multi-provider router (search.py) as a standalone HTTP
service that any LAxMI bot can call.

Endpoints:
  GET  /            → status JSON (fund convention)
  POST /search      → {query, provider?, count?, depth?, time_range?, include_domains?, exclude_domains?}
  POST /extract     → {urls: [...], provider?, format?, include_images?, include_raw_html?, render_js?}
  POST /trigger     → no-op for fund.mjs uniformity (returns ok:true)

Provider keys are read from environment (decrypted via dotenvx in fund.mjs).
Honors fund halt at /tmp/fund-state.json — refuses search calls while halted.

Port: 3451  |  Default DRY_RUN-agnostic (read-only, no money moved).
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="[search-router] %(message)s", stream=sys.stdout)
log = logging.getLogger("search-router")

BOT_NAME       = os.getenv("BOT_NAME", "search-router")
STATUS_PORT    = int(os.getenv("SEARCH_ROUTER_PORT", "3451"))
FUND_STATE     = os.getenv("FUND_STATE", "/tmp/fund-state.json")
SEARCH_SCRIPT  = Path(__file__).parent / "search.py"
SEARCH_TIMEOUT = int(os.getenv("SEARCH_ROUTER_TIMEOUT", "75"))
EXTRACT_TIMEOUT = int(os.getenv("EXTRACT_TIMEOUT", "90"))

PROVIDER_ENV_KEYS = [
    "SERPER_API_KEY", "BRAVE_API_KEY", "TAVILY_API_KEY", "EXA_API_KEY",
    "QUERIT_API_KEY", "LINKUP_API_KEY", "FIRECRAWL_API_KEY",
    "PERPLEXITY_API_KEY", "YOU_API_KEY", "SEARXNG_INSTANCE_URL",
]

state: dict[str, Any] = {
    "cycle": 0,
    "running": False,
    "last": None,
    "error": None,
    "started_at": time.time(),
    "search_count": 0,
    "extract_count": 0,
}


def configured_providers() -> list[str]:
    return [k.replace("_API_KEY", "").replace("_INSTANCE_URL", "").lower()
            for k in PROVIDER_ENV_KEYS if os.getenv(k)]


def fund_halted() -> tuple[bool, str | None]:
    try:
        data = json.loads(Path(FUND_STATE).read_text())
        if data.get("halted"):
            return True, data.get("haltReason")
    except Exception:
        pass
    return False, None


def run_search(payload: dict) -> dict:
    query = (payload.get("query") or "").strip()
    if not query:
        return {"error": "missing 'query'", "results": []}

    cmd = [sys.executable, str(SEARCH_SCRIPT),
           "--query", query,
           "--provider", payload.get("provider", "auto"),
           "--max-results", str(int(payload.get("count", 5))),
           "--compact"]
    depth = payload.get("depth", "normal")
    if depth and depth != "normal":
        cmd += ["--exa-depth", depth]
    tr = payload.get("time_range")
    if tr and tr != "none":
        cmd += ["--time-range", tr]
    if payload.get("include_domains"):
        cmd += ["--include-domains", *payload["include_domains"]]
    if payload.get("exclude_domains"):
        cmd += ["--exclude-domains", *payload["exclude_domains"]]

    state["running"] = True
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=SEARCH_TIMEOUT, env=os.environ.copy())
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            try:
                return json.loads(stderr)
            except json.JSONDecodeError:
                return {"error": stderr or "search failed", "results": []}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"error": f"search timed out after {SEARCH_TIMEOUT}s", "results": []}
    except Exception as e:
        return {"error": str(e), "results": []}
    finally:
        state["running"] = False


def run_extract(payload: dict) -> dict:
    urls = payload.get("urls") or []
    if isinstance(urls, str):
        urls = [urls]
    if not urls:
        return {"error": "missing 'urls'", "results": []}

    cmd = [sys.executable, str(SEARCH_SCRIPT),
           "--extract-urls", *urls,
           "--provider", payload.get("provider", "auto"),
           "--format", payload.get("format", "markdown"),
           "--compact"]
    if payload.get("include_images"):
        cmd.append("--extract-images")
    if payload.get("include_raw_html"):
        cmd.append("--include-raw-html")
    if payload.get("render_js"):
        cmd.append("--render-js")

    state["running"] = True
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=EXTRACT_TIMEOUT, env=os.environ.copy())
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            try:
                return json.loads(stderr)
            except json.JSONDecodeError:
                return {"error": stderr or "extract failed", "results": []}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"error": f"extract timed out after {EXTRACT_TIMEOUT}s", "results": []}
    except Exception as e:
        return {"error": str(e), "results": []}
    finally:
        state["running"] = False


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, body: dict) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(body, indent=2).encode())

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8") or ""
        try:
            return json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        if self.path != "/" and not self.path.startswith("/?"):
            self._send_json(404, {"error": "not found"})
            return
        self._send_json(200, {
            "bot": BOT_NAME,
            "cycle": state["cycle"],
            "running": state["running"],
            "last": state["last"],
            "error": state["error"],
            "uptime_s": int(time.time() - state["started_at"]),
            "providers_configured": configured_providers(),
            "counts": {"search": state["search_count"], "extract": state["extract_count"]},
        })

    def do_POST(self):
        if self.path == "/trigger":
            self._send_json(200, {"ok": True, "note": "no cycle — service is request/response only"})
            return

        halted, reason = fund_halted()
        if halted and self.path in ("/search", "/extract"):
            self._send_json(503, {"error": "fund halted", "reason": reason, "results": []})
            return

        payload = self._read_json()

        if self.path == "/search":
            data = run_search(payload)
            state["cycle"] += 1
            state["search_count"] += 1
            state["last"] = {
                "kind": "search",
                "query": (payload.get("query") or "")[:120],
                "provider": data.get("provider"),
                "result_count": len(data.get("results") or []),
                "cached": data.get("cached", False),
                "timestamp": int(time.time()),
            }
            state["error"] = data.get("error")
            self._send_json(200, data)
            return

        if self.path == "/extract":
            data = run_extract(payload)
            state["cycle"] += 1
            state["extract_count"] += 1
            state["last"] = {
                "kind": "extract",
                "urls": (payload.get("urls") or [])[:3],
                "provider": data.get("provider"),
                "result_count": len(data.get("results") or []),
                "timestamp": int(time.time()),
            }
            state["error"] = data.get("error")
            self._send_json(200, data)
            return

        self._send_json(404, {"error": "not found"})

    def log_message(self, format, *args):
        pass


def main() -> None:
    if not SEARCH_SCRIPT.exists():
        log.error(f"search.py not found at {SEARCH_SCRIPT}")
        sys.exit(1)

    providers = configured_providers()
    if not providers:
        log.warning("No provider API keys set — service will return errors. "
                    f"Set at least one of: {', '.join(PROVIDER_ENV_KEYS[:4])}")
    else:
        log.info(f"Providers configured: {', '.join(providers)}")

    server = HTTPServer(("0.0.0.0", STATUS_PORT), Handler)
    log.info(f"laxmi-search-router listening on http://localhost:{STATUS_PORT}")
    log.info(f"  GET  /         → status")
    log.info(f"  POST /search   → {{query, provider?, count?, depth?, time_range?, include_domains?, exclude_domains?}}")
    log.info(f"  POST /extract  → {{urls, provider?, format?}}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("shutting down")


if __name__ == "__main__":
    main()
