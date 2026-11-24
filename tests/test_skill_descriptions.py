#!/usr/bin/env python3
"""The sub-skills that route to each other must say when to use them and when
not to, naming the sibling to use instead, so the right one fires."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    "operator-pass-call": ["operator-pass-list"],
    "operator-pass-kickoff": ["operator-pass-onboarding"],
    "operator-pass-onboarding": ["operator-pass-kickoff"],
}


def description(name: str) -> str:
    text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    front = text.split("---", 2)[1]
    match = re.search(r"^description:\s*(.+)$", front, re.MULTILINE)
    assert match, f"{name}: no description"
    return match.group(1)


class SkillDescriptionTest(unittest.TestCase):
    def test_use_when_and_not_for(self):
        for name, siblings in SKILLS.items():
            with self.subTest(skill=name):
                desc = description(name)
                self.assertIn("Use when", desc)
                self.assertIn("Not for", desc)
                not_for = desc.split("Not for", 1)[1]
                for sibling in siblings:
                    self.assertIn(sibling, not_for)


if __name__ == "__main__":
    unittest.main()
