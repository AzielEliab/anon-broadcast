"""Lock the not-ready status. These tests fail if the command claims work it does not do."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    return subprocess.run(
        [sys.executable, "-m", "anon_broadcast", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class CliTests(unittest.TestCase):
    def test_bare_welcome_is_honest(self) -> None:
        result = run([])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("Aziel Eliab", result.stdout)
        self.assertIn("This package is not ready yet.", result.stdout)
        self.assertIn("When it ships, the next step will be", result.stdout)
        self.assertIn("That renderer is not in this package.", result.stdout)
        self.assertIn("anon-broadcast --help", result.stdout)
        self.assertNotIn("Traceback", result.stdout)
        self.assertNotIn("What this is not", result.stdout)

    def test_help_is_short(self) -> None:
        result = run(["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stdout)
        self.assertIn("Examples:", result.stdout)
        self.assertIn("This package is not ready yet.", result.stdout)
        self.assertLess(len(result.stdout.splitlines()), 30)
        self.assertNotIn("changelog", result.stdout.lower())

    def test_json_status(self) -> None:
        result = run(["--json"])
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["name"], "anon-broadcast")
        self.assertEqual(payload["author"], "Aziel Eliab")
        self.assertIs(payload["ready"], False)
        self.assertEqual(payload["summary"], "This package is not ready yet.")
        self.assertIn("not in this package", payload["next_step"])

    def test_unknown_command(self) -> None:
        result = run(["bogus"])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn('Unknown command "bogus".', result.stderr)
        self.assertIn("Try: anon-broadcast --help", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_unknown_option_json(self) -> None:
        result = run(["--json", "--bogus"])
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertIs(payload["ok"], False)
        self.assertIn("Unknown option", payload["error"])
        self.assertIn("anon-broadcast --help", payload["next"])
        self.assertEqual(result.stderr, "")

    def test_version_is_unreleased(self) -> None:
        result = run(["--version"])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "anon-broadcast unreleased")

    def test_directory_script(self) -> None:
        env = os.environ.copy()
        result = subprocess.run(
            [str(ROOT / "anon-broadcast"), "--help"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("This package is not ready yet.", result.stdout)

    def test_readme_matches_status(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Aziel Eliab", readme)
        self.assertIn("not ready", readme)
        self.assertIn("./anon-broadcast", readme)
        self.assertIn("./anon-broadcast --help", readme)
        self.assertIn("python3 -m pip install -e .", readme)
        self.assertIn("python3 -m anon_broadcast", readme)
        self.assertNotIn("What this is not", readme)
        self.assertLessEqual(readme.count("\n1. "), 1)
        self.assertLessEqual(readme.count("\n2. "), 1)
        self.assertLessEqual(readme.count("\n3. "), 1)


if __name__ == "__main__":
    unittest.main()
