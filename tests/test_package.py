"""Package version stays aligned with the landing and the tarball name."""

from __future__ import annotations

import tarfile
import unittest
from pathlib import Path

from anonbroadcast import ASSET_NAME, VERSION

ROOT = Path(__file__).resolve().parents[1]
HOME = (ROOT / "workers/download-tracker/src/home.js").read_text(encoding="utf-8")
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")


class PackageTests(unittest.TestCase):
    def test_version_is_shared(self) -> None:
        self.assertIn(f'version = "{VERSION}"', PYPROJECT)
        self.assertIn(f'export const VERSION = "{VERSION}";', HOME)
        self.assertIn(ASSET_NAME, HOME)
        self.assertNotIn("THIS IS NOT", HOME)
        self.assertNotIn("identity-lock", HOME)
        self.assertIn("prefers-color-scheme: dark", HOME)
        self.assertIn(":focus-visible", HOME)
        self.assertIn('class="download"', HOME)
        self.assertIn("Download", HOME)

    def test_tarball_is_the_source_package(self) -> None:
        asset = ROOT / "workers/download-tracker/public" / ASSET_NAME
        self.assertTrue(asset.is_file(), "run scripts/build_assets.py")
        with tarfile.open(asset, "r:gz") as tar:
            names = tar.getnames()
        prefix = f"anon-broadcast-{VERSION}/"
        self.assertIn(prefix + "anonbroadcast/cli.py", names)
        self.assertIn(prefix + "anonbroadcast/render.py", names)
        self.assertIn(prefix + "pyproject.toml", names)
        self.assertIn(prefix + "LICENSE", names)
        self.assertIn(prefix + "README.md", names)
        self.assertFalse(any(name.endswith(".tar.gz") for name in names))


if __name__ == "__main__":
    unittest.main()
