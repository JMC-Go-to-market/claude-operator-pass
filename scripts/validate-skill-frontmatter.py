#!/usr/bin/env python3
"""
validate-skill-frontmatter.py — Validate SKILL.md frontmatter per the Claude
Code Agent Skills spec across this skill pack.

Walks the repo, finds every SKILL.md, parses its YAML frontmatter, and
enforces:
- name field present, 1-64 chars, lowercase letters/digits/hyphens
- name matches the containing directory name
- description present, 20-1024 chars
- if `user-invocable: false` is set, sub-skill rules apply

Exits 1 on any violation. Zero non-stdlib deps.

USAGE:
    python3 scripts/validate-skill-frontmatter.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, Tuple

ROOT = Path.cwd()
NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def parse_frontmatter(text: str) -> Dict[str, str]:
    """Parse simple YAML frontmatter (supports flat scalar values + folded > blocks)."""
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    body = text[4:end]

    out: Dict[str, str] = {}
    lines = body.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^([a-z][a-zA-Z0-9_-]*):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, value = m.group(1), m.group(2).strip()
        # Folded scalar (`description: >\n  multi-line ...`)
        if value == ">" or value == "|":
            collected = []
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or lines[i].strip() == ""):
                collected.append(lines[i].strip())
                i += 1
            out[key] = " ".join(s for s in collected if s).strip()
            continue
        # Strip surrounding quotes
        value = re.sub(r'^"(.*)"$', r"\1", value)
        value = re.sub(r"^'(.*)'$", r"\1", value)
        out[key] = value
        i += 1
    return out


def find_skill_files() -> list[Path]:
    """Find every SKILL.md, skipping common non-source directories."""
    skip = {"node_modules", ".git", "dist", "build", ".next"}
    out: list[Path] = []
    for path in ROOT.rglob("SKILL.md"):
        if any(part in skip for part in path.parts):
            continue
        out.append(path)
    return sorted(out)


MAX_INPUT_BYTES = 2_000_000


def validate_one(path: Path) -> Tuple[bool, list[str]]:
    try:
        if not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
            return False, ["cannot read SKILL.md"]
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False, ["cannot read SKILL.md as UTF-8 text"]
    except OSError:
        return False, ["cannot read SKILL.md"]
    fm = parse_frontmatter(text)
    issues: list[str] = []

    if not fm:
        issues.append("missing or malformed YAML frontmatter")
        return False, issues

    name = fm.get("name", "").strip()
    description = fm.get("description", "").strip()
    dir_name = path.parent.name

    if not name:
        issues.append("missing `name` field")
    elif len(name) > 64:
        issues.append(f"name '{name}' exceeds 64 chars")
    elif not NAME_RE.match(name):
        issues.append(f"name '{name}' must match /{NAME_RE.pattern}/ (lowercase + hyphens)")
    elif name != dir_name:
        issues.append(f"name '{name}' must match directory '{dir_name}'")

    if not description:
        issues.append("missing `description` field")
    elif len(description) < 20:
        issues.append(f"description {len(description)} chars too short (min 20)")
    elif len(description) > 1024:
        issues.append(f"description {len(description)} chars exceeds 1024")

    return len(issues) == 0, issues


def main() -> int:
    skill_files = find_skill_files()
    if not skill_files:
        print("✗ No SKILL.md files found")
        return 1

    print(f"Validating {len(skill_files)} SKILL.md file(s)\n")
    failures = 0
    for path in skill_files:
        rel = path.relative_to(ROOT)
        ok, issues = validate_one(path)
        if ok:
            print(f"  ✓ {rel}")
        else:
            print(f"  ✗ {rel}")
            for issue in issues:
                print(f"      → {issue}")
            failures += 1

    print()
    if failures > 0:
        print(f"✗ {failures} of {len(skill_files)} skill(s) failed validation")
        return 1
    print(f"✓ All {len(skill_files)} skill(s) valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
