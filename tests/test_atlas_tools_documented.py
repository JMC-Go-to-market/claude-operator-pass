#!/usr/bin/env python3
"""Run: python3 -m unittest tests.test_atlas_tools_documented (CI runs all of tests/).

Every Data Atlas tool the API serves is documented in the skill (catalog row,
section, routing) and has a usage line in the client (#22)."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATLAS_TOOLS = ["data-atlas-search", "data-atlas-dossier", "data-atlas-evidence"]


class AtlasToolsDocumented(unittest.TestCase):
    def setUp(self):
        self.skill = (ROOT / "operator-pass" / "SKILL.md").read_text()
        self.client = (ROOT / "scripts" / "op_api.py").read_text()

    def test_catalog_row(self):
        for slug in ATLAS_TOOLS:
            self.assertIn(f"| `{slug}` |", self.skill, slug)

    def test_section(self):
        for slug in ATLAS_TOOLS:
            self.assertIn(f"### `{slug}`", self.skill, slug)

    def test_routed(self):
        for slug in ATLAS_TOOLS:
            self.assertRegex(self.skill, rf"\| \"[^\n]*\" \| [^\n]*`{slug}`", slug)

    def test_client_usage_line(self):
        for slug in ATLAS_TOOLS:
            self.assertIn(f"call {slug} --input", self.client, slug)


if __name__ == "__main__":
    unittest.main()
