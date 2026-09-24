"""AnonBroadcast renders a real MP4 and an honest receipt."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from anonbroadcast import VERSION
from anonbroadcast.render import RenderError, render_mp4
from anonbroadcast.voice import duration_seconds, synthesize, zero_crossing_rate


class VoiceTests(unittest.TestCase):
    def test_fricative_is_noisier_than_vowel(self) -> None:
        vowel = zero_crossing_rate(synthesize("a"))
        fricative = zero_crossing_rate(synthesize("s"))
        self.assertGreater(fricative, vowel + 0.2)

    def test_longer_text_speaks_longer(self) -> None:
        short = duration_seconds(synthesize("Hi."))
        longer = duration_seconds(synthesize("The note stays on this desk."))
        self.assertGreater(longer, short)


class RenderTests(unittest.TestCase):
    def test_mp4_receipt_and_culled_tags(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "communique.mp4"
            receipt = render_mp4("The note stays on this desk.", dest)
            payload = dest.read_bytes()
            self.assertEqual(payload[4:8], b"ftyp")
            self.assertEqual(receipt["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(receipt["version"], VERSION)
            self.assertEqual(receipt["author"], "Aziel Eliab")
            self.assertEqual(receipt["voice"], "local-formant-en")
            self.assertEqual(receipt["metadata"], "culled")
            on_disk = json.loads(dest.with_suffix(".receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(on_disk["sha256"], receipt["sha256"])
            probe = json.loads(
                subprocess.check_output(
                    ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(dest)],
                    text=True,
                )
            )
            banned = {"title", "comment", "artist", "album", "location", "creation_time", "date", "encoder"}
            format_tags = {k.lower() for k in (probe["format"].get("tags") or {})}
            self.assertFalse(banned & format_tags)
            self.assertGreaterEqual(len(probe["streams"]), 2)
            kinds = {stream["codec_type"] for stream in probe["streams"]}
            self.assertEqual(kinds, {"video", "audio"})
            for stream in probe["streams"]:
                tags = {k.lower() for k in (stream.get("tags") or {})}
                self.assertFalse(banned & tags)

    def test_empty_text_is_refused(self) -> None:
        with self.assertRaises(RenderError) as caught:
            render_mp4("   ", "/tmp/should-not-exist-anon-broadcast.mp4")
        self.assertIn("empty", str(caught.exception).lower())

    def test_non_latin_is_refused(self) -> None:
        with self.assertRaises(RenderError) as caught:
            render_mp4("café", "/tmp/should-not-exist-anon-broadcast.mp4")
        self.assertIn("Latin", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
