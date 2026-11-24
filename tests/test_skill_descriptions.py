#!/usr/bin/env python3
"""Every skill must say when to use it and when not to, naming the sibling to
use instead where skills overlap, so the right one fires."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Every SKILL.md in the repo, so a new skill is checked without editing this list.
SKILL_FILES = sorted(p for p in ROOT.rglob("SKILL.md") if ".git" not in p.parts)
# The sibling each "Not for" clause must name, where skills overlap.
SIBLINGS = {
    "operator-pass": ["gtm-data-atlas"],
    "operator-pass-call": ["operator-pass-list"],
    "operator-pass-kickoff": ["operator-pass-onboarding"],
    "operator-pass-list": ["operator-pass-call"],
    "operator-pass-onboarding": ["operator-pass-kickoff"],
    "gtm-data-atlas": ["operator-pass-call"],
}


def frontmatter(path: Path) -> dict:
    """Top-level keys of the frontmatter; folded (>) values joined on spaces."""
    lines = path.read_text(encoding="utf-8").split("---", 2)[1].splitlines()
    front, key = {}, None
    for line in lines:
        match = re.match(r"^([A-Za-z-]+):\s*(.*)$", line)
        if match:
            key, value = match.groups()
            front[key] = "" if value in (">", "|", ">-") else value
        elif key and line.startswith("  "):
            front[key] = (front[key] + " " + line.strip()).strip()
    return front


class SkillDescriptionTest(unittest.TestCase):
    def test_finds_every_skill(self):
        names = {frontmatter(p).get("name") for p in SKILL_FILES}
        self.assertEqual(names, set(SIBLINGS))

    def test_use_when_and_not_for(self):
        for path in SKILL_FILES:
            front = frontmatter(path)
            name = front.get("name")
            with self.subTest(skill=name):
                desc = front.get("description", "")
                self.assertIn("Use when", desc)
                self.assertIn("Not for", desc)
                not_for = desc.split("Not for", 1)[1]
                for sibling in SIBLINGS.get(name, []):
                    self.assertIn(sibling, not_for)


if __name__ == "__main__":
    unittest.main()
