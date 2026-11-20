#!/usr/bin/env python3
"""Run: python3 -m unittest tests.test_client_plugin

The client plugin wires the member MCP with the Pass key from an env var,
ships a Data Atlas skill, checks the key first, and calls only routes that exist."""

import importlib.util
import io
import json
import re
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "operator-pass-data-atlas"


def load_api():
    spec = importlib.util.spec_from_file_location("op_api", ROOT / "scripts" / "op_api.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def text_files():
    out = []
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT)
        if not p.is_file() or rel.parts[0] in {".git", "assets", "tests"}:
            continue
        if p.suffix in {".md", ".json", ".py", ".sh"} and rel.name != "CHANGELOG.md":
            out.append(p)
    return out


class McpWiring(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())

    def test_member_mcp_server_uses_env_key(self):
        server = self.manifest["mcpServers"]["operator-pass"]
        self.assertEqual(server["type"], "http")
        self.assertEqual(server["url"], "https://api.jaymountconsulting.com/mcp")
        self.assertEqual(server["headers"], {"Authorization": "Bearer ${OPERATOR_PASS_API_KEY}"})

    def test_no_key_value_in_any_file(self):
        hits = [str(f.relative_to(ROOT)) for f in text_files() if re.search(r"jmc_live_[A-Za-z0-9]{8,}", f.read_text())]
        self.assertEqual(hits, [])

    def test_only_one_server_and_not_the_free_one(self):
        self.assertEqual(list(self.manifest["mcpServers"]), ["operator-pass"])
        self.assertNotIn("/mcp/free", json.dumps(self.manifest))


class NoInternalLeak(unittest.TestCase):
    """Public repo: only the API host, the public site and this repo may be named."""

    HOST = re.compile(r"(?i)\b(?:[a-z0-9-]+\.)+jaymountconsulting\.com\b")
    REPO = re.compile(r"(?i)github\.com/JMC-Go-to-market/([A-Za-z0-9._-]+)")
    ALLOWED_HOSTS = {"api.jaymountconsulting.com", "jaymountconsulting.com", "www.jaymountconsulting.com"}

    def test_only_allowed_hosts(self):
        hits = []
        for f in text_files():
            for m in self.HOST.finditer(f.read_text()):
                if m.group(0).lower() not in self.ALLOWED_HOSTS:
                    hits.append(f"{f.relative_to(ROOT)}: {m.group(0)}")
        self.assertEqual(hits, [])

    def test_only_this_repo_is_linked(self):
        hits = []
        for f in text_files():
            for m in self.REPO.finditer(f.read_text()):
                if m.group(1).lower().removesuffix(".git") != "claude-operator-pass":
                    hits.append(f"{f.relative_to(ROOT)}: {m.group(0)}")
        self.assertEqual(hits, [])


class NoDeadRoutes(unittest.TestCase):
    def test_docs_and_client_skip_routes_that_do_not_exist(self):
        pat = re.compile(r"/v1/me\b|/v1/tools(?![/\w-])|/tools/<slug>/schema|\"/me\"|\"/tools\"|/schema\"|api_get\(\"/me\"\)")
        hits = []
        for f in text_files():
            for m in pat.finditer(f.read_text()):
                hits.append(f"{f.relative_to(ROOT)}: {m.group(0)}")
        self.assertEqual(hits, [])

    def test_geo_slug_matches_live_catalog(self):
        for f in text_files():
            self.assertNotRegex(f.read_text(), r"geo-visibility(?!-audit)", str(f))


class WritePermission(unittest.TestCase):
    def test_read_only_skills_do_not_ask_for_write(self):
        for rel in ["operator-pass/SKILL.md", "skills/operator-pass-call/SKILL.md", "skills/operator-pass-data-atlas/SKILL.md"]:
            front = (ROOT / rel).read_text().split("\n---\n", 1)[0]
            self.assertNotRegex(front, r"(?m)^\s*-\s*Write\b|allowed-tools:.*\bWrite\b", rel)


class DataAtlasSkill(unittest.TestCase):
    def setUp(self):
        self.text = (SKILL / "SKILL.md").read_text()

    def test_frontmatter_name_matches_dir(self):
        self.assertTrue(self.text.startswith("---\nname: operator-pass-data-atlas\n"))

    def test_citation_and_honesty_rules(self):
        low = self.text.lower()
        for needle in ["last checked", "source_url", "last_verified_at", "from memory", "unknown", "drop", "data-atlas-dossier", "data-atlas-search"]:
            self.assertIn(needle.lower(), low, needle)

    def test_first_call_check_before_tools(self):
        self.assertIn("whoami", self.text)
        self.assertLess(self.text.index("python3 scripts/op_api.py whoami"), self.text.index("## How to query"))

    def test_main_skill_checks_key_with_whoami(self):
        main = (ROOT / "operator-pass" / "SKILL.md").read_text()
        self.assertIn("op_api.py whoami", main)

    def test_setup_reference_covers_platforms(self):
        ref = (SKILL / "references" / "mcp-setup.md").read_text()
        for needle in ["Claude Code", "Codex", "Cursor", "OPERATOR_PASS_API_KEY", "https://api.jaymountconsulting.com/mcp", "Bearer"]:
            self.assertIn(needle, ref, needle)
        self.assertNotIn("/mcp/free", ref)


class OpApiMcp(unittest.TestCase):
    def setUp(self):
        self.api = load_api()

    def run_cmd(self, fn, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = fn(*args)
        return rc, out.getvalue(), err.getvalue()

    def fake(self, status=200):
        tools = [{"name": "data-atlas-search", "description": "Search the Atlas.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}}}]
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"tools": tools}})
        self.calls = []

        def request(method, path, body_=None, **kw):
            self.calls.append((method, path, kw))
            if status != 200:
                return {"ok": False, "status": status, "data": {}}
            return {"ok": True, "status": 200, "data": body, "rate_remaining": "59"}

        self.api.request = request

    def test_parse_plain_json_and_sse(self):
        msg = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
        self.assertEqual(self.api.parse_mcp_body(json.dumps(msg)), msg)
        self.assertEqual(self.api.parse_mcp_body("event: message\ndata: " + json.dumps(msg) + "\n\n"), msg)
        with self.assertRaises(ValueError):
            self.api.parse_mcp_body("<html>gateway</html>")

    def test_whoami_uses_mcp_not_me(self):
        self.fake()
        rc, out, _ = self.run_cmd(self.api.cmd_whoami)
        self.assertEqual(rc, 0)
        self.assertEqual(self.calls[0][0:2], ("POST", "/mcp"))
        self.assertIn("accepted", out.lower())
        self.assertIn("1 tools", out)
        self.assertIn("unknown", out.lower())

    def test_whoami_rejected_key(self):
        self.fake(status=401)
        rc, out, _ = self.run_cmd(self.api.cmd_whoami)
        self.assertEqual(rc, 1)
        self.assertNotIn("accepted", out.lower())

    def test_schema_comes_from_tool_list(self):
        self.fake()
        rc, out, _ = self.run_cmd(self.api.cmd_schema, "data-atlas-search")
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["properties"]["query"]["type"], "string")

    def test_schema_unknown_slug_says_so(self):
        self.fake()
        rc, out, err = self.run_cmd(self.api.cmd_schema, "no-such-tool")
        self.assertEqual(rc, 1)
        self.assertIn("unknown tool", err.lower())
        self.assertEqual(out, "")

    def test_list_prints_slugs(self):
        self.fake()
        rc, out, _ = self.run_cmd(self.api.cmd_list)
        self.assertEqual(rc, 0)
        self.assertIn("data-atlas-search", out)
        self.assertIn("Total: 1", out)

    def test_malformed_tool_list_is_an_error(self):
        self.api.request = lambda *a, **k: {"ok": True, "status": 200, "data": "<html>", "rate_remaining": None}
        rc, _, err = self.run_cmd(self.api.cmd_list)
        self.assertEqual(rc, 1)
        self.assertIn("not valid", err.lower())


if __name__ == "__main__":
    unittest.main()
