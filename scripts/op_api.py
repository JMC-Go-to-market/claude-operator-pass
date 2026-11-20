#!/usr/bin/env python3
"""
op_api.py — Operator Pass API client + key validator + catalog fetcher.

Deterministic CLI wrapper around the JMC API. Validates the API key,
fetches the live tool catalog, fetches per-tool schemas, calls tools
with JSON inputs. Handles 401/402/429/5xx per the brand-config rules.

USAGE:
    OPERATOR_PASS_API_KEY=jmc_live_... python3 op_api.py whoami   # key check, via the member MCP
    OPERATOR_PASS_API_KEY=jmc_live_... python3 op_api.py list     # tool list, via the member MCP
    OPERATOR_PASS_API_KEY=jmc_live_... python3 op_api.py schema cold-email-linter
    OPERATOR_PASS_API_KEY=jmc_live_... python3 op_api.py call cold-email-linter --input '{"email":"..."}'
    OPERATOR_PASS_API_KEY=jmc_live_... python3 op_api.py call data-atlas-search --input '{"query":"intent data","limit":5}'
    OPERATOR_PASS_API_KEY=jmc_live_... python3 op_api.py call data-atlas-dossier --input '{"slug":"<slug from search>"}'

Zero non-stdlib deps. Uses urllib + json.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


DEFAULT_BASE_URL = "https://api.jaymountconsulting.com/v1"
ALLOWED_HOST = "api.jaymountconsulting.com"
DEFAULT_TIMEOUT_S = 30
MAX_INPUT_BYTES = 2_000_000
USER_AGENT = "claude-operator-pass/0.2 (https://github.com/JMC-Go-to-market/claude-operator-pass)"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PATH_RE = re.compile(r"(?:/[A-Za-z0-9._~-]+)+")


class _SameHostRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse a redirect that would carry the bearer token off the API host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parts = urllib.parse.urlsplit(newurl)
        if parts.scheme != "https" or (parts.hostname or "") != ALLOWED_HOST:
            raise urllib.error.URLError("refusing redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def get_key() -> str:
    key = os.environ.get("OPERATOR_PASS_API_KEY", "").strip()
    if not key:
        sys.stderr.write(
            "ERROR: OPERATOR_PASS_API_KEY env var not set.\n"
            "Subscribe + get a key: https://jaymountconsulting.com/operator-pass\n"
        )
        sys.exit(2)
    return key


def _safe_base_path(path: str) -> bool:
    if path in ("", "/"):
        return True
    if ".." in path.split("/"):
        return False
    return bool(_PATH_RE.fullmatch(path))


def base_url() -> str:
    raw = os.environ.get("OPERATOR_PASS_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    parts = urllib.parse.urlsplit(raw)
    if (
        parts.scheme != "https"
        or (parts.hostname or "") != ALLOWED_HOST
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
        or not _safe_base_path(parts.path or "")
    ):
        sys.stderr.write(
            "ERROR: OPERATOR_PASS_BASE_URL must be https://api.jaymountconsulting.com\n"
        )
        sys.exit(2)
    path = (parts.path or "").rstrip("/")
    return f"https://{ALLOWED_HOST}{path}"


def fail_input(message: str) -> None:
    sys.stderr.write(f"error: {message}\n")
    raise SystemExit(2)


def read_json_object(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        fail_input("invalid JSON")
    if not isinstance(data, dict):
        fail_input("JSON must be an object")
    return data


def read_input_file(path: str) -> Dict[str, Any]:
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_INPUT_BYTES + 1)
    except IsADirectoryError:
        fail_input(f"not a file: {path}")
    except FileNotFoundError:
        fail_input(f"file not found: {path}")
    except OSError:
        fail_input(f"cannot read file: {path}")
    if len(raw) > MAX_INPUT_BYTES:
        fail_input(f"file is too large: {path}")
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        fail_input(f"file is not UTF-8 text: {path}")
    return read_json_object(text)


def request(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    retry_on_429: bool = True,
    root: bool = False,
    raw_body: bool = False,
    accept: str = "application/json",
) -> Dict[str, Any]:
    """Make an authenticated API request. Returns parsed JSON.

    root=True resolves path against the API host root (the MCP lives at /mcp,
    outside /v1). raw_body=True returns the response text unparsed.
    """
    key = get_key()
    base = base_url()  # always validated, even for root paths
    url = f"https://{ALLOWED_HOST}{path}" if root else f"{base}{path}"
    headers = {
        "Authorization": f"Bearer {key}",
        "User-Agent": USER_AGENT,
        "Accept": accept,
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    opener = urllib.request.build_opener(_SameHostRedirect)
    for attempt in range(2 if retry_on_429 else 1):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with opener.open(req, timeout=timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
                return {
                    "ok": True,
                    "status": resp.status,
                    "data": raw if raw_body else (json.loads(raw) if raw else {}),
                    "rate_remaining": resp.headers.get("X-RateLimit-Remaining"),
                }
        except urllib.error.HTTPError as err:
            body_text = err.read().decode("utf-8", errors="ignore")
            try:
                err_data = json.loads(body_text) if body_text else {}
            except json.JSONDecodeError:
                err_data = {"raw": body_text}

            if err.code == 401:
                sys.stderr.write(
                    "ERROR 401: API key invalid or expired.\n"
                    "Renew: https://jaymountconsulting.com/operator-pass\n"
                )
                return {"ok": False, "status": 401, "data": err_data}
            if err.code == 402:
                sys.stderr.write(
                    "ERROR 402: Operator Pass subscription expired.\n"
                    "Renew: https://jaymountconsulting.com/operator-pass\n"
                )
                return {"ok": False, "status": 402, "data": err_data}
            if err.code == 429:
                if retry_on_429 and attempt == 0:
                    try:
                        retry_after = int(err.headers.get("Retry-After", "30"))
                    except ValueError:
                        retry_after = 30
                    retry_after = max(0, min(retry_after, 60))
                    sys.stderr.write(f"429 rate-limited — retrying in {retry_after}s...\n")
                    time.sleep(retry_after)
                    continue
                sys.stderr.write("ERROR 429: rate-limited. Try again later.\n")
                return {"ok": False, "status": 429, "data": err_data}
            preview = body_text[:200].replace(key, "[redacted]")
            sys.stderr.write(f"ERROR {err.code}: {preview}\n")
            return {"ok": False, "status": err.code, "data": err_data}
        except (urllib.error.URLError, TimeoutError):
            sys.stderr.write("ERROR network: could not reach the Operator Pass API\n")
            return {"ok": False, "status": 0, "data": {"error": "network"}}
    return {"ok": False, "status": 0, "data": {}}


# ---------------- Commands ----------------

def parse_mcp_body(text: str) -> Dict[str, Any]:
    """Parse an MCP reply: plain JSON, or an SSE stream carrying one JSON message."""
    text = text.strip()
    candidates = [text]
    candidates += [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
    for cand in candidates:
        try:
            msg = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(msg, dict):
            return msg
    raise ValueError("MCP reply is not valid JSON")


def mcp_tools() -> Optional[Dict[str, Any]]:
    """tools/list on the member MCP. Returns {"tools": [...], "rate_remaining": ...} or None.

    The REST API has no account, catalog or schema route; the MCP is where the
    key check, the catalog and each tool's input schema live.
    """
    result = request(
        "POST",
        "/mcp",
        body={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        root=True,
        raw_body=True,
        accept="application/json, text/event-stream",
    )
    if not result["ok"]:
        return None
    try:
        msg = parse_mcp_body(result["data"])
    except ValueError:
        sys.stderr.write("ERROR: the MCP reply was not valid JSON\n")
        return None
    tools = (msg.get("result") or {}).get("tools")
    if not isinstance(tools, list):
        sys.stderr.write("ERROR: the MCP reply was not valid: no tool list\n")
        return None
    return {"tools": [t for t in tools if isinstance(t, dict)], "rate_remaining": result.get("rate_remaining")}


def cmd_whoami() -> int:
    listing = mcp_tools()
    if listing is None:
        return 1
    print("Key:              accepted")
    print(f"Tools available:  {len(listing['tools'])} tools")
    # No endpoint reports the plan, quota or expiry: say unknown, never guess.
    print("Plan:             unknown (not reported by the API)")
    print("Quota remaining:  " + (str(listing["rate_remaining"]) if listing["rate_remaining"] else "unknown"))
    print("Pass valid until: unknown (not reported by the API)")
    return 0


def cmd_list() -> int:
    listing = mcp_tools()
    if listing is None:
        return 1
    tools = listing["tools"]
    for t in sorted(tools, key=lambda x: str(x.get("name", ""))):
        print(f"  {str(t.get('name', '?')).ljust(35)} {str(t.get('description', ''))[:80]}")
    print(f"\nTotal: {len(tools)} tools")
    return 0


def cmd_schema(slug: str) -> int:
    check_slug(slug)
    listing = mcp_tools()
    if listing is None:
        return 1
    for t in listing["tools"]:
        if t.get("name") == slug:
            print(json.dumps(t.get("inputSchema", {}), indent=2))
            return 0
    sys.stderr.write(f"error: unknown tool: {slug}\n")
    return 1


def check_slug(slug: str) -> None:
    if not SLUG_RE.fullmatch(slug):
        fail_input("tool slug must be lowercase letters, digits and hyphens")


def cmd_call(slug: str, inputs: Dict[str, Any]) -> int:
    check_slug(slug)
    result = request("POST", f"/tools/{urllib.parse.quote(slug)}", body=inputs)
    if not result["ok"]:
        return 1
    print(json.dumps(result["data"], indent=2))
    if result.get("rate_remaining"):
        sys.stderr.write(f"(rate_remaining: {result['rate_remaining']})\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("whoami", help="Check the API key is accepted (via the member MCP)")
    sub.add_parser("list", help="List the tools your key can call (via the member MCP)")
    p_schema = sub.add_parser("schema", help="Fetch schema for a tool")
    p_schema.add_argument("slug")
    p_call = sub.add_parser("call", help="Call a tool with JSON inputs")
    p_call.add_argument("slug")
    p_call.add_argument("--input", default="{}", help="JSON input")
    p_call.add_argument("--input-file", default=None, help="Path to JSON input file")

    args = parser.parse_args()

    if args.cmd == "whoami":
        return cmd_whoami()
    if args.cmd == "list":
        return cmd_list()
    if args.cmd == "schema":
        return cmd_schema(args.slug)
    if args.cmd == "call":
        if args.input_file:
            inputs = read_input_file(args.input_file)
        else:
            if len(args.input.encode("utf-8")) > MAX_INPUT_BYTES:
                fail_input("input is too large")
            inputs = read_json_object(args.input)
        return cmd_call(args.slug, inputs)
    return 2


if __name__ == "__main__":
    sys.exit(main())
