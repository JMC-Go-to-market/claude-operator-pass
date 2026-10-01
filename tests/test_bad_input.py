#!/usr/bin/env python3
"""Operator Pass client rejects a foreign base URL before any socket."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "scripts" / "op_api.py"
TOKEN = "super-secret-token"
DUMMY_KEY = "dummy-not-a-real-key"


def run(args, env):
    return subprocess.run(
        [sys.executable, str(API), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=5,
    )


class OpApiBadInput(unittest.TestCase):
    def test_missing_key_exits_2(self):
        env = os.environ.copy()
        env.pop("OPERATOR_PASS_API_KEY", None)
        env.pop("OPERATOR_PASS_BASE_URL", None)
        result = run(["whoami"], env)
        self.assertEqual(result.returncode, 2)
        self.assertIn("OPERATOR_PASS_API_KEY", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_foreign_base_url_exits_before_connect(self):
        env = os.environ.copy()
        env["OPERATOR_PASS_API_KEY"] = DUMMY_KEY
        urls = [
            "https://evil.example/v1",
            "http://api.jaymountconsulting.com/v1",
            "https://user:pass@api.jaymountconsulting.com/v1",
            "https://api.jaymountconsulting.com/v1?x=1",
            "https://api.jaymountconsulting.com/v1/../admin",
        ]
        for url in urls:
            env["OPERATOR_PASS_BASE_URL"] = url
            result = run(["whoami"], env)
            self.assertEqual(result.returncode, 2, url)
            self.assertIn("OPERATOR_PASS_BASE_URL", result.stderr)
            self.assertNotIn(DUMMY_KEY, result.stderr + result.stdout)
            self.assertNotIn("Traceback", result.stderr)

    def test_call_input_hides_bytes_and_rejects_array(self):
        env = os.environ.copy()
        env["OPERATOR_PASS_API_KEY"] = DUMMY_KEY
        env["OPERATOR_PASS_BASE_URL"] = "https://api.jaymountconsulting.com/v1"
        bad = run(["call", "cold-email-linter", "--input", '{"email": "' + TOKEN], env)
        self.assertEqual(bad.returncode, 2)
        self.assertNotIn(TOKEN, bad.stderr + bad.stdout)
        array = run(["call", "cold-email-linter", "--input", "[]"], env)
        self.assertEqual(array.returncode, 2)
        self.assertIn("JSON must be an object", array.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            missing = run(
                ["call", "cold-email-linter", "--input-file", str(Path(tmp) / "nope.json")],
                env,
            )
        self.assertEqual(missing.returncode, 2)
        self.assertIn("file not found", missing.stderr)


if __name__ == "__main__":
    unittest.main()
