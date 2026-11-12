"""Run the release workflow's shell with a fake gh; notes must stay data."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/release.yml'


def step_script(name):
    lines = WORKFLOW.read_text().splitlines()
    start = lines.index('      - name: ' + name)
    start = next(i for i in range(start, len(lines)) if lines[i] == '        run: |') + 1
    end = next((i for i in range(start, len(lines))
                if lines[i].strip() and not lines[i].startswith('          ')), len(lines))
    return textwrap.dedent('\n'.join(lines[start:end]))


class ReleaseNotes(unittest.TestCase):
    def run_release(self, exists, missing=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            notes = ('- Keep `inline code` and "quotes".\nEOF\n'
                     f'- Literal `touch {root}/backtick` and $(touch {root}/substitution).\n'
                     '- Keep $HOME and \\slashes.')
            (root / 'CHANGELOG.md').write_text('## [0.3.0]\n\n' + notes + '\n\n## [0.2.0]\nOld notes\n')
            version = '9.9.9' if missing else '0.3.0'
            env = {**os.environ, 'PATH': str(root) + os.pathsep + os.environ['PATH'],
                   'VERSION': version, 'TAG': 'v' + version, 'RUNNER_TEMP': str(root),
                   'GITHUB_OUTPUT': str(root / 'output'), 'GH_EXISTS': str(int(exists)),
                   'GH_RECORD': str(root / 'record')}
            fake_gh = root / 'gh'
            fake_gh.write_text('#!' + sys.executable + '\n' + textwrap.dedent('''
                import json, os, pathlib, sys
                args = sys.argv[1:]
                if args[:2] == ['release', 'view']:
                    sys.exit(0 if os.environ['GH_EXISTS'] == '1' else 1)
                if '--notes-file' in args:
                    notes = pathlib.Path(args[args.index('--notes-file') + 1]).read_text()
                else:
                    notes = args[args.index('--notes') + 1]
                pathlib.Path(os.environ['GH_RECORD']).write_text(json.dumps({'args': args, 'notes': notes}))
            '''))
            fake_gh.chmod(0o755)
            extract = step_script('Extract changelog notes for this version').replace('${{ steps.version.outputs.version }}', version)
            subprocess.run(['bash', '-e', '-c', extract], cwd=root, env=env, check=True, capture_output=True)
            expected = f'Release v{version}' if missing else notes
            publish = step_script('Create GitHub Release').replace('${{ steps.version.outputs.tag }}', 'v' + version).replace('${{ steps.notes.outputs.notes }}', expected)
            result = subprocess.run(['bash', '-e', '-c', publish], cwd=root, env=env, capture_output=True, text=True)
            self.assertFalse((root / 'backtick').exists(), 'notes executed as shell code')
            self.assertFalse((root / 'substitution').exists(), 'notes executed as shell code')
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads((root / 'record').read_text())
            self.assertEqual(record['notes'], expected)
            self.assertEqual(record['args'][:3], ['release', 'edit' if exists else 'create', 'v' + version])

    def test_new_release_preserves_literal_notes(self):
        self.run_release(False)

    def test_existing_release_preserves_literal_notes(self):
        self.run_release(True)

    def test_missing_version_uses_fallback(self):
        self.run_release(False, missing=True)
