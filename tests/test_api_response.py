#!/usr/bin/env python3
"""Malformed successful API responses fail cleanly without network access."""

import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

API = Path(__file__).resolve().parents[1] / "scripts" / "op_api.py"
RUNNER = textwrap.dedent("""
    import io
    import runpy
    import sys
    from unittest.mock import Mock, patch

    script, body, *args = sys.argv[1:]
    response = io.BytesIO(body.encode("utf-8"))
    response.status = 200
    response.headers = {}
    opener = Mock()
    opener.open.return_value = response
    sys.argv = [script, *args]
    with patch("urllib.request.build_opener", return_value=opener):
        runpy.run_path(script, run_name="__main__")
""")


class OpApiResponse(unittest.TestCase):
    def test_non_json_200_exits_cleanly(self):
        for body in ("<html>Proxy error</html>", '{"broken":'):
            for args in (["whoami"], ["list"], ["schema", "fixture"],
                         ["call", "fixture", "--input", "{}"]):
                with self.subTest(body=body, args=args):
                    result = subprocess.run(
                        [sys.executable, "-c", RUNNER, str(API), body, *args],
                        env={"OPERATOR_PASS_API_KEY": "dummy-not-a-real-key"},
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(
                        result.stderr,
                        "ERROR response: invalid JSON from the Operator Pass API\n",
                    )
                    self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
