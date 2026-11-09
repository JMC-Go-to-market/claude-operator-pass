#!/usr/bin/env python3
"""Reader-facing copy follows the org rules: no 'with Jay', no typed counts or
prices, no cadence promises, brand name, no internal labels or competitors.

"Internal label" is defined by JMC-Go-to-market/jaymount-site .specs/no-internal-labels-in-copy.md.
Runs in CI (.github/workflows/ci.yml, "Reader-facing copy follows the org rules")."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {"CHANGELOG.md", "LICENSE", "SOUL.md"}  # SOUL.md is the user's own template


def copy_files():
    files = [ROOT / ".claude-plugin" / "plugin.json"]
    for p in ROOT.rglob("*.md"):
        rel = p.relative_to(ROOT)
        if rel.parts[0] in {".git", ".github", "tests"} or rel.name in SKIP:
            continue
        files.append(p)
    return [f for f in files if f.exists()]


RULES = {
    "office hours 'with Jay'": r"(?i)\bwith jay\b",
    "cadence promise": r"(?i)\b(weekly|monthly|daily|every \w+day)\b",
    "typed count": r"(?i)\b\d+\+?\s*(free\s+)?(tools?|courses?|modules?|packs?|more)\b|\b\d+-tool\b|and \d+ more",
    "typed price": r"\$\s?\d",
    "legal name as brand": r"Jay Mount Consulting",
    "internal label": r"(?i)compounding engine|soft path|methodology",
    "competitor": r"(?i)coldiq|\btreg\b|superdesign",
}


class CopyRules(unittest.TestCase):
    def test_rules(self):
        hits = []
        for f in copy_files():
            text = f.read_text(encoding="utf-8")
            for name, pat in RULES.items():
                for m in re.finditer(pat, text):
                    line = text.count("\n", 0, m.start()) + 1
                    hits.append(f"{f.relative_to(ROOT)}:{line} {name}: {m.group(0)!r}")
        self.assertEqual(hits, [], "\n" + "\n".join(hits))


if __name__ == "__main__":
    unittest.main()
