#!/usr/bin/env python3
"""
op_api.py — Operator Pass API client + key validator + catalog fetcher.

Deterministic CLI wrapper around the JMC API. Validates the API key,
fetches the live tool catalog, fetches per-tool schemas, calls tools
with JSON inputs. Handles 401/402/429/5xx per the brand-config rules.

USAGE:
    OPERATOR_PASS_API_KEY=jmc_live_... python3 op_api.py whoami
    OPERATOR_PASS_API_KEY=jmc_live_... python3 op_api.py list
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
from typing import Any, Callable, Dict, Optional


DEFAULT_BASE_URL = "https://api.jaymountconsulting.com/v1"
ALLOWED_HOST = "api.jaymountconsulting.com"
DEFAULT_TIMEOUT_S = 30
MAX_INPUT_BYTES = 2_000_000
USER_AGENT = "claude-operator-pass/0.2 (https://github.com/JMC-Go-to-market/claude-operator-pass)"
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


def sse_chunks(resp: Any) -> Callable[[], bytes]:
    """Return a reader that yields bytes as soon as they arrive (b"" at the end)."""
    read1 = getattr(resp, "read1", None)
    if callable(read1):
        return lambda: read1(65536)
    return lambda: resp.read(1)


def read_sse_response(read_chunk: Callable[[], bytes], want_id: Any) -> Optional[Dict[str, Any]]:
    """Read a text/event-stream incrementally and return the JSON-RPC response with id want_id.

    Lines end at CR, LF or CRLF; one leading UTF-8 BOM is dropped. Returns as
    soon as the matching response (result or error) arrives, so a stream the
    server keeps open does not block. Notifications, requests and comments are
    skipped. Returns None when the stream ends without a matching response or
    an event's data is not JSON.
    """
    buf = b""
    total = 0
    first = True
    skip_lf = False
    data_lines: list = []

    def dispatch() -> Optional[Dict[str, Any]]:
        try:
            message = json.loads("\n".join(data_lines))
        except json.JSONDecodeError:
            raise ValueError("invalid event data")
        if (
            isinstance(message, dict)
            and "method" not in message
            and message.get("id") == want_id
            and ("result" in message or "error" in message)
        ):
            return message
        return None

    try:
        while True:
            chunk = read_chunk()
            eof = not chunk
            total += len(chunk)
            if total > MAX_INPUT_BYTES:
                return None
            buf += chunk
            if first and len(buf) >= 3 or first and eof:
                if buf.startswith(b"\xef\xbb\xbf"):
                    buf = buf[3:]
                first = False
            elif first:
                continue
            while True:
                # A CR at the end of a chunk may be the first half of CRLF: keep
                # waiting until the next byte arrives before deciding.
                if skip_lf and buf:
                    if buf[:1] == b"\n":
                        buf = buf[1:]
                    skip_lf = False
                cut = min((i for i in (buf.find(b"\r"), buf.find(b"\n")) if i >= 0), default=-1)
                if cut < 0:
                    break
                line = buf[:cut].decode("utf-8", errors="ignore")
                skip_lf = buf[cut:cut + 1] == b"\r"
                buf = buf[cut + 1:]
                if line:
                    if line.startswith("data:"):
                        value = line[5:]
                        data_lines.append(value[1:] if value.startswith(" ") else value)
                    continue
                if data_lines:
                    message = dispatch()
                    data_lines = []
                    if message is not None:
                        return message
            if eof:
                # An unterminated final event is discarded, as the SSE standard requires.
                return None
    except ValueError:
        return None


def request(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    retry_on_429: bool = True,
    api_root: bool = False,
) -> Dict[str, Any]:
    """Make an authenticated API request. Returns parsed JSON."""
    key = get_key()
    base = base_url()  # validate the configured host before constructing either route
    url = f"https://{ALLOWED_HOST}{path}" if api_root else f"{base}{path}"
    headers = {
        "Authorization": f"Bearer {key}",
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/event-stream" if api_root else "application/json",
        **({"MCP-Protocol-Version": "2025-06-18"} if api_root else {}),
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
                ctype = resp.headers.get("Content-Type") if resp.headers is not None else None
                ctype = ctype.split(";", 1)[0].strip().lower() if isinstance(ctype, str) else ""
                if api_root and ctype == "text/event-stream":
                    want_id = body.get("id") if isinstance(body, dict) else None
                    parsed = read_sse_response(sse_chunks(resp), want_id)
                    if parsed is None:
                        sys.stderr.write("ERROR protocol: event stream has no matching JSON-RPC response\n")
                        return {"ok": False, "status": resp.status, "data": {"error": "invalid_sse"}}
                else:
                    raw = resp.read().decode("utf-8", errors="ignore")
                    try:
                        parsed = json.loads(raw) if raw else {}
                    except json.JSONDecodeError:
                        sys.stderr.write("ERROR protocol: API response is not JSON\n")
                        return {"ok": False, "status": resp.status, "data": {"error": "invalid_json"}}
                return {
                    "ok": True,
                    "status": resp.status,
                    "data": parsed,
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

def discover_tools() -> Optional[list]:
    """Authenticated stateless member MCP discovery (not a tool execution)."""
    tools = []
    cursor = None
    seen = set()
    for _ in range(100):
        result = request("POST", "/mcp", body={
            "jsonrpc": "2.0", "id": 1, "method": "tools/list",
            "params": {} if cursor is None else {"cursor": cursor},
        }, api_root=True)
        if not result["ok"]:
            return None
        data = result.get("data")
        if not isinstance(data, dict) or data.get("jsonrpc") != "2.0" or data.get("id") != 1:
            sys.stderr.write("ERROR MCP: invalid JSON-RPC response\n")
            return None
        if "error" in data:
            # A remote error is data, not a successful empty catalog.
            sys.stderr.write("ERROR MCP: " + json.dumps(data["error"]).replace(get_key(), "[redacted]") + "\n")
            return None
        page = data.get("result")
        if not isinstance(page, dict) or not isinstance(page.get("tools"), list):
            sys.stderr.write("ERROR MCP: missing tools array\n")
            return None
        for tool in page["tools"]:
            if not isinstance(tool, dict) or not isinstance(tool.get("name"), str) or not tool["name"] or not isinstance(tool.get("inputSchema"), dict):
                sys.stderr.write("ERROR MCP: invalid tool definition\n")
                return None
        tools.extend(page["tools"])
        cursor = page.get("nextCursor")
        if cursor is None:
            return tools
        if not isinstance(cursor, str) or not cursor or cursor in seen:
            sys.stderr.write("ERROR MCP: invalid or repeated pagination cursor\n")
            return None
        seen.add(cursor)
    sys.stderr.write("ERROR MCP: discovery page limit exceeded\n")
    return None


def cmd_whoami() -> int:
    tools = discover_tools()
    if tools is None:
        return 1
    print(f"Authenticated MCP discovery: OK ({len(tools)} tools)")
    print("Identity, plan, validity and quota: unknown (not returned by discovery)")
    return 0


def cmd_list() -> int:
    tools = discover_tools()
    if tools is None:
        return 1
    for tool in tools:
        print(f"  {tool['name'].ljust(35)} {tool.get('description', '')[:80]}")
    print(f"\nTotal: {len(tools)} tools")
    return 0


def cmd_schema(slug: str) -> int:
    tools = discover_tools()
    if tools is None:
        return 1
    for tool in tools:
        if tool["name"] == slug:
            print(json.dumps(tool["inputSchema"], indent=2))
            return 0
    sys.stderr.write("ERROR: tool not in member catalog; run /operator-pass list\n")
    return 1


def print_result(data: Any) -> None:
    """Render returned fields, without synthesizing or rewriting an envelope."""
    def render(value: Any, indent: str = "") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                print(f"{indent}{key}:", end="")
                if isinstance(item, (dict, list)):
                    print()
                    render(item, indent + "  ")
                else:
                    print(" " + scalar(item))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, (dict, list)):
                    print(indent + "-")
                    render(item, indent + "  ")
                else:
                    print(indent + "- " + scalar(item))
            if not value:
                print(indent + "(none returned)")
        else:
            print(indent + scalar(value))

    def scalar(value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    if isinstance(data, dict) and isinstance(data.get("summary"), str):
        print(data["summary"])
        render({key: value for key, value in data.items() if key != "summary"})
    else:
        render(data)


def cmd_call(slug: str, inputs: Dict[str, Any], raw: bool = False) -> int:
    result = request("POST", f"/tools/{urllib.parse.quote(slug, safe='')}", body=inputs)
    if not result["ok"]:
        return 1
    if raw:
        print(json.dumps(result["data"], indent=2))
    else:
        print_result(result["data"])
    if result.get("rate_remaining"):
        sys.stderr.write(f"(rate_remaining: {result['rate_remaining']})\n")
    return 1 if isinstance(result["data"], dict) and result["data"].get("status") == "error" else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("whoami", help="Check authenticated MCP discovery (account/quota unknown)")
    sub.add_parser("list", help="Fetch live tool catalog")
    p_schema = sub.add_parser("schema", help="Fetch schema for a tool")
    p_schema.add_argument("slug")
    p_call = sub.add_parser("call", help="Call a tool with JSON inputs")
    p_call.add_argument("slug")
    p_call.add_argument("--raw", action="store_true", help="Print unmodified response as JSON")
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
        return cmd_call(args.slug, inputs, raw=args.raw)
    return 2


if __name__ == "__main__":
    sys.exit(main())
