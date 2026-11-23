#!/usr/bin/env python3
"""This repository is public. Tracked files must not name private repositories,
their issues or pull requests, internal servers or internal rollout notes.

.github/ holds files synced from the org template; they are out of scope here."""

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve().relative_to(ROOT).as_posix()

PATTERNS = {
    "org repo other than this one": r"JMC-Go-to-market/(?!claude-operator-pass\b)[A-Za-z0-9._-]+",
    "cross-repo issue or PR": r"\b[a-z][a-z0-9_.-]*#\d+",
    "internal repo name": r"\bjmc-[a-z]",
    "internal server": r"(?i)gtm-context|knowledge-mcp|content-mcp|jaymount-site",
    "internal machine": r"(?i)new-mini|mini-2",
    "internal rollout note": r"(?i)leak check|knowledge pack",
}


def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    for rel in out.splitlines():
        if rel.startswith(".github/") or rel == SELF:
            continue
        path = ROOT / rel
        if path.is_file():
            yield rel, path


class PublicContent(unittest.TestCase):
    def test_no_private_references(self):
        hits = []
        for rel, path in tracked_files():
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for name, pat in PATTERNS.items():
                for m in re.finditer(pat, text):
                    line = text.count("\n", 0, m.start()) + 1
                    hits.append(f"{rel}:{line} {name}: {m.group(0)!r}")
        self.assertEqual(hits, [], "\n" + "\n".join(hits))


if __name__ == "__main__":
    unittest.main()
