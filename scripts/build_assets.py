"""Build the counted source tarball, sigil, and a real desk-reel preview.

Author: Aziel Eliab.
"""

from __future__ import annotations

import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from anonbroadcast import ASSET_NAME, VERSION
from anonbroadcast.render import write_preview_png

PUBLIC = ROOT / "workers" / "download-tracker" / "public"
INCLUDE = (
    "README.md",
    "LICENSE",
    "NOTICE",
    "pyproject.toml",
    "anonbroadcast/__init__.py",
    "anonbroadcast/__main__.py",
    "anonbroadcast/cli.py",
    "anonbroadcast/font8x8.py",
    "anonbroadcast/reel.py",
    "anonbroadcast/render.py",
    "anonbroadcast/voice.py",
)


def build_tarball() -> Path:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    destination = PUBLIC / ASSET_NAME
    prefix = f"anon-broadcast-{VERSION}"
    with tarfile.open(destination, "w:gz") as tar:
        for relative in INCLUDE:
            tar.add(ROOT / relative, arcname=f"{prefix}/{relative}")
    return destination


def build_sigil() -> None:
    """Small paper-on-desk mark. Decorative, not a product screenshot."""
    w = h = 128
    desk = bytes((92, 70, 50))
    paper = bytes((243, 234, 215))
    rule = bytes((138, 106, 50))
    buf = bytearray(desk * (w * h))

    def fill(x, y, rw, rh, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(w, x + rw), min(h, y + rh)
        span = color * (x1 - x0)
        for yy in range(y0, y1):
            start = (yy * w + x0) * 3
            buf[start : start + len(span)] = span

    fill(28, 24, 72, 84, paper)
    fill(40, 40, 36, 4, rule)
    ppm = PUBLIC / "sigil.ppm"
    ppm.write_bytes(b"P6\n128 128\n255\n" + bytes(buf))
    import subprocess

    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(ppm), str(PUBLIC / "sigil.png")],
        check=True,
    )
    ppm.unlink()


def main() -> None:
    archive = build_tarball()
    write_preview_png("The note stays on this desk.", PUBLIC / "preview.png")
    build_sigil()
    print(archive)


if __name__ == "__main__":
    main()
