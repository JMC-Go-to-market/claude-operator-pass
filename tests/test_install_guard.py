#!/usr/bin/env python3
"""operator-pass installer refuses a bad clone before it deletes a skill."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAFE_PATH = "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"


def git(repo: Path, *args):
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.email=test@example.com", "-c", "user.name=test", *args],
        check=True,
        capture_output=True,
        text=True,
    )


def make_repo(repo: Path, kind: str) -> None:
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "operator-pass").mkdir()
    (repo / "operator-pass" / "SKILL.md").write_text("---\nname: operator-pass\n---\n", encoding="utf-8")
    skills = repo / "skills"
    skills.mkdir()
    if kind == "symlink":
        (skills / "operator-pass-evil").symlink_to(repo / "operator-pass")
    elif kind == "upper":
        bad = skills / "operator-pass-Bad"
        bad.mkdir()
        (bad / "SKILL.md").write_text("nope", encoding="utf-8")
    else:
        good = skills / "operator-pass-list"
        good.mkdir()
        (good / "SKILL.md").write_text("---\nname: operator-pass-list\n---\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "fixture")


def installer(repo: Path, dest: Path) -> None:
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    text = text.replace(
        'REPO_URL="https://github.com/JMC-Go-to-market/claude-operator-pass"',
        f'REPO_URL="{repo.as_uri()}"',
    )
    dest.write_text(text, encoding="utf-8")


def invoke(script: Path, home: Path):
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["PATH"] = SAFE_PATH
    return subprocess.run(
        ["bash", str(script)],
        env=env,
        capture_output=True,
        text=True,
    )


class OperatorPassInstallGuard(unittest.TestCase):
    def test_clean_local_clone_installs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            home = root / "home"
            home.mkdir()
            make_repo(repo, "clean")
            script = root / "install.sh"
            installer(repo, script)
            result = invoke(script, home)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((home / ".claude" / "skills" / "operator-pass" / "SKILL.md").is_file())
            self.assertTrue(
                (home / ".claude" / "skills" / "operator-pass-list" / "SKILL.md").is_file()
            )

    def test_symlink_refuses_before_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            home = root / "home"
            home.mkdir()
            make_repo(repo, "symlink")
            keep = home / ".claude" / "skills" / "operator-pass" / "KEEP"
            keep.parent.mkdir(parents=True)
            keep.write_text("keep", encoding="utf-8")
            script = root / "install.sh"
            installer(repo, script)
            result = invoke(script, home)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("symlink", result.stderr)
            self.assertEqual(keep.read_text(encoding="utf-8"), "keep")

    def test_uppercase_refuses_before_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            home = root / "home"
            home.mkdir()
            make_repo(repo, "upper")
            keep = home / ".claude" / "skills" / "operator-pass" / "KEEP"
            keep.parent.mkdir(parents=True)
            keep.write_text("keep", encoding="utf-8")
            script = root / "install.sh"
            installer(repo, script)
            result = invoke(script, home)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("lowercase", result.stderr)
            self.assertEqual(keep.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
