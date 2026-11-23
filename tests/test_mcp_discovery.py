"""Offline protocol and result-presentation regression tests; no API calls."""
import contextlib
import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("op_api", ROOT / "scripts/op_api.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)

TOOL = {"name": "data-atlas-search", "description": "Find sources",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}}}


def rpc(result):
    return {"ok": True, "status": 200, "data": {"jsonrpc": "2.0", "id": 1, "result": result}}


class Discovery(unittest.TestCase):
    def run_command(self, command, responses):
        output = io.StringIO()
        with patch.object(api, "get_key", return_value="dummy-not-a-key"), patch.object(api, "request", side_effect=responses) as req, contextlib.redirect_stdout(output):
            code = command()
        return code, output.getvalue(), req

    def test_whoami_checks_authenticated_discovery_without_fabricating_account(self):
        code, out, req = self.run_command(api.cmd_whoami, [rpc({"tools": [TOOL]})])
        self.assertEqual(code, 0)
        self.assertIn("authenticated", out.lower())
        self.assertIn("unknown", out.lower())
        self.assertNotIn("User:", out)
        self.assertEqual(req.call_args.args[:2], ("POST", "/mcp"))
        self.assertEqual(req.call_args.kwargs["body"]["method"], "tools/list")

    def test_list_uses_names_and_follows_pagination(self):
        code, out, req = self.run_command(api.cmd_list, [rpc({"tools": [TOOL], "nextCursor": "page2"}), rpc({"tools": [{**TOOL, "name": "data-atlas-dossier"}]})])
        self.assertEqual(code, 0)
        self.assertIn("data-atlas-dossier", out)
        self.assertEqual(req.call_args.kwargs["body"]["params"], {"cursor": "page2"})

    def test_schema_selects_input_schema_from_catalog(self):
        code, out, req = self.run_command(lambda: api.cmd_schema("data-atlas-search"), [rpc({"tools": [TOOL]})])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), TOOL["inputSchema"])
        self.assertEqual(req.call_count, 1)

    def test_missing_tool_is_failure(self):
        with contextlib.redirect_stderr(io.StringIO()):
            code, _, _ = self.run_command(lambda: api.cmd_schema("missing"), [rpc({"tools": [TOOL]})])
        self.assertEqual(code, 1)

    def test_protocol_errors_and_malformed_results_fail(self):
        responses = [rpc({}), rpc({"tools": "wrong"}),
                     {"ok": True, "data": {"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Method not found"}}},
                     {"ok": False, "status": 401, "data": {}}]
        for response in responses:
            with self.subTest(response=response), contextlib.redirect_stderr(io.StringIO()):
                code, _, _ = self.run_command(api.cmd_whoami, [response])
                self.assertEqual(code, 1)

    def test_repeated_cursor_fails_instead_of_looping(self):
        with contextlib.redirect_stderr(io.StringIO()):
            code, _, req = self.run_command(api.cmd_list, [rpc({"tools": [], "nextCursor": "x"}), rpc({"tools": [], "nextCursor": "x"})])
        self.assertEqual(code, 1)
        self.assertEqual(req.call_count, 2)

    def test_wire_url_headers_and_bearer(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(rpc({"tools": []})["data"]).encode()
        response.status = 200
        with patch.dict(api.os.environ, {"OPERATOR_PASS_API_KEY": "dummy-not-a-key", "OPERATOR_PASS_BASE_URL": api.DEFAULT_BASE_URL}), patch.object(api.urllib.request, "build_opener") as opener, contextlib.redirect_stdout(io.StringIO()):
            opener.return_value.open.return_value = response
            self.assertEqual(api.cmd_whoami(), 0)
        req = opener.return_value.open.call_args.args[0]
        self.assertEqual(req.full_url, "https://api.jaymountconsulting.com/mcp")
        self.assertIn("text/event-stream", req.get_header("Accept"))
        self.assertEqual(req.get_header("Authorization"), "Bearer dummy-not-a-key")
        self.assertEqual(json.loads(req.data)["method"], "tools/list")

    def test_non_json_discovery_fails_cleanly(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b"<html>gateway failure</html>"
        response.status = 200
        with patch.dict(api.os.environ, {"OPERATOR_PASS_API_KEY": "dummy-not-a-key", "OPERATOR_PASS_BASE_URL": api.DEFAULT_BASE_URL}), patch.object(api.urllib.request, "build_opener") as opener, contextlib.redirect_stderr(io.StringIO()) as err:
            opener.return_value.open.return_value = response
            self.assertEqual(api.cmd_whoami(), 1)
        self.assertIn("not JSON", err.getvalue())

    def _wire(self, body, content_type):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = body.encode()
        response.status = 200
        response.headers = {"Content-Type": content_type}
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(api.os.environ, {"OPERATOR_PASS_API_KEY": "dummy-not-a-key", "OPERATOR_PASS_BASE_URL": api.DEFAULT_BASE_URL}), patch.object(api.urllib.request, "build_opener") as opener, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            opener.return_value.open.return_value = response
            code = api.cmd_list()
        return code, out.getvalue(), err.getvalue()

    def test_sse_discovery_succeeds(self):
        msg = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"tools": [TOOL]}})
        code, out, _ = self._wire(f"event: message\ndata: {msg}\n\n", "text/event-stream")
        self.assertEqual(code, 0)
        self.assertIn("data-atlas-search", out)

    def test_sse_skips_preceding_notifications_and_multiline_data(self):
        note = json.dumps({"jsonrpc": "2.0", "method": "notifications/message", "params": {"level": "info"}})
        msg = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"tools": [TOOL]}}, indent=1)
        data_lines = "\n".join("data: " + line for line in msg.splitlines())
        body = f": keepalive\n\nevent: message\ndata: {note}\n\nid: 7\nevent: message\n{data_lines}\n\n"
        code, out, _ = self._wire(body, "text/event-stream; charset=utf-8")
        self.assertEqual(code, 0)
        self.assertIn("data-atlas-search", out)

    def test_sse_error_response_fails(self):
        msg = json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Method not found"}})
        code, _, err = self._wire(f"event: message\ndata: {msg}\n\n", "text/event-stream")
        self.assertEqual(code, 1)
        self.assertIn("Method not found", err)

    def test_sse_without_matching_response_fails(self):
        note = json.dumps({"jsonrpc": "2.0", "method": "notifications/progress", "params": {}})
        code, _, err = self._wire(f"data: {note}\n\n", "text/event-stream")
        self.assertEqual(code, 1)
        self.assertIn("ERROR", err)

    def test_plugin_wires_only_member_mcp_with_env_placeholder(self):
        config = json.loads((ROOT / ".mcp.json").read_text())
        self.assertEqual(config, {"mcpServers": {"operator-pass": {"type": "http", "url": "https://api.jaymountconsulting.com/mcp", "headers": {"Authorization": "Bearer ${OPERATOR_PASS_API_KEY}"}}}})


class Presentation(unittest.TestCase):
    def test_envelope_summary_first_preserves_unknowns_and_status(self):
        env = {"summary": "No coverage measurement.", "status": "partial", "coverage": None,
               "confidence": {"value": 0.9, "basis": "model_self_report"}, "abstain": None,
               "unknowns": [{"field": "coverage", "why": "Not measured"}],
               "assumptions": [{"name": "region", "value": "CA", "source": "user"}],
               "evidence": [{"text": "Source", "url": "https://example.com", "date": None, "verified": False}],
               "limits": ["Public sources"], "next_action": "Collect a sample.",
               "receipt": {"tool": "data-atlas-search", "version": "1", "as_of": "2026-11-22"}}
        output = io.StringIO()
        with patch.object(api, "request", return_value={"ok": True, "data": env}), contextlib.redirect_stdout(output):
            self.assertEqual(api.cmd_call("data-atlas-search", {}), 0)
        text = output.getvalue()
        self.assertTrue(text.startswith(env["summary"]))
        for value in ["partial", "model_self_report", "Not measured", "Collect a sample.", "https://example.com", "2026-11-22", "CA"]:
            self.assertIn(value, text)
        self.assertIn("unknown", text.lower())
        self.assertEqual(env["coverage"], None)

    def test_http_success_with_server_error_status_fails_without_rewriting(self):
        data = {"summary": "Tool failed", "status": "error", "next_action": "Collect inputs"}
        output = io.StringIO()
        with patch.object(api, "request", return_value={"ok": True, "data": data}), contextlib.redirect_stdout(output):
            self.assertEqual(api.cmd_call("tool", {}), 1)
        self.assertIn("error", output.getvalue())
        self.assertEqual(data["status"], "error")

    def test_raw_opt_in_preserves_exact_response(self):
        data = {"summary": "Abstained", "status": "abstain", "score": None}
        output = io.StringIO()
        with patch.object(api, "request", return_value={"ok": True, "data": data}), contextlib.redirect_stdout(output):
            self.assertEqual(api.cmd_call("tool", {}, raw=True), 0)
        self.assertEqual(json.loads(output.getvalue()), data)


if __name__ == "__main__":
    unittest.main()
