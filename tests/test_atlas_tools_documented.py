#!/usr/bin/env python3
"""Run: python3 -m unittest tests.test_atlas_tools_documented (CI runs all of tests/).

Every Data Atlas tool the API serves is documented in the skill (catalog row,
section, routing) and has a usage line in the client (#22)."""

import json
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

    def evidence_section(self):
        return self.skill.split("### `data-atlas-evidence`\n", 1)[1].split("### Example", 1)[0]

    def test_evidence_is_stored_publisher_receipts(self):
        for misleading in ("What practitioners write", "What do people say", "check what practitioners",
                           "short third-party quote", "knowledge base has nothing on that question"):
            self.assertNotIn(misleading, self.skill)
        catalog = next(line for line in self.skill.splitlines() if line.startswith("| `data-atlas-evidence` |"))
        self.assertIn("stored", catalog)
        self.assertIn("publisher", catalog)
        self.assertIn("ranks stored claim receipts", self.evidence_section())

    def test_evidence_slug_constraints_and_missing_slug(self):
        section = self.evidence_section()
        for required in ("optional in the schema", "Without `source_slug`", "abstains",
                         "120", "^[a-z0-9][a-z0-9-]*$", "obtain a slug"):
            with self.subTest(required=required):
                self.assertIn(required, section)

    def test_evidence_output_example_has_envelope_and_check_date(self):
        section = self.evidence_section()
        output = json.loads(section.split("```json\n", 1)[1].split("```", 1)[0])
        self.assertEqual(output["status"], "ok")
        self.assertIsNone(output["abstain"])
        for field in ("summary", "confidence", "unknowns", "assumptions", "evidence",
                      "limits", "next_action", "receipt"):
            self.assertIn(field, output)
        passage = output["passages"][0]
        self.assertIn("checked_at", passage)
        self.assertEqual(passage["source_type"], "publisher")
        self.assertIsNone(passage["published_at"])

    def test_evidence_freshness_and_citations(self):
        section = self.evidence_section()
        for required in ("check date", "not re-read on each call", "may have changed",
                         "Read the linked page", "Quote the excerpt with its link",
                         "claims the excerpt does not make"):
            with self.subTest(required=required):
                self.assertIn(required, section)

    def test_evidence_abstention_reasons_and_next_action(self):
        section = self.evidence_section()
        for required in ("`status: abstain`", "missing slug", "unknown source",
                         "no stored receipts", "`abstain.reason`", "`abstain.to_collect`",
                         "`unknowns`", "`next_action`", "data-atlas-dossier"):
            with self.subTest(required=required):
                self.assertIn(required, section)


if __name__ == "__main__":
    unittest.main()
