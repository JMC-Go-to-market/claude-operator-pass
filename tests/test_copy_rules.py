#!/usr/bin/env python3
"""Run: python3 -m unittest tests.test_copy_rules (CI runs all of tests/).

Reader-facing copy follows the org rules: no 'with Jay', no typed counts or
prices, no cadence promises, brand name, no internal labels or competitors."""

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
    # Planning labels per jaymount-site .specs/no-internal-labels-in-copy.md
    "internal label (jaymount-site spec)": r"(?i)soft (path|start|next step|cta|read|on-ramp)|start soft|\bHOLD\b|Pass Claim|no Claim|densify|Signal\+GA|product context",
    # Org copy rule, not in that spec: internal product and method names
    "internal name": r"(?i)compounding engine|methodology",
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
