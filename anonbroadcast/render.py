"""Render a communique to a metadata-culled MP4 plus a SHA-256 receipt.

ffmpeg must be on PATH. The Worker does not render video.

Author: Aziel Eliab.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import wave
from io import BytesIO
from pathlib import Path

from anonbroadcast import AUTHOR, PRODUCT, VERSION
from anonbroadcast.reel import FPS, frames_for
from anonbroadcast.voice import SAMPLE_RATE, synthesize

MAX_CHARS = 480


class RenderError(Exception):
    def __init__(self, message: str, code: int = 2) -> None:
        super().__init__(message)
        self.code = code


def check_text(text: str) -> str:
    if text is None:
        raise RenderError("Add the note text, then render again.", 2)
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not cleaned:
        raise RenderError("The note is empty. Add some text, then render again.", 2)
    if len(cleaned) > MAX_CHARS:
        raise RenderError(
            f"This reel holds {MAX_CHARS} characters. Shorten the note and render again.",
            2,
        )
    for ch in cleaned:
        if ch in "\n\t":
            continue
        if ord(ch) < 32 or ord(ch) > 126:
            raise RenderError(
                "This voice reads basic Latin letters, digits, and simple punctuation.",
                2,
            )
    return cleaned


def _ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if not found:
        raise RenderError(
            "ffmpeg is not on PATH. Install ffmpeg, then render again. The MP4 was not written.",
            3,
        )
    return found


def _pad_wav(wav: bytes, seconds: float) -> bytes:
    with wave.open(BytesIO(wav), "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        rate = wf.getframerate()
        width = wf.getsampwidth()
        channels = wf.getnchannels()
    have = len(frames) / (width * channels) / rate
    need = max(0.0, seconds - have)
    pad = b"\x00" * int(need * rate) * width * channels
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(width)
        wf.setframerate(rate)
        wf.writeframes(frames + pad)
    return buf.getvalue()


def render_mp4(text: str, out_path: str | os.PathLike[str]) -> dict:
    """Write the MP4 and a sibling .receipt.json. Return the receipt dict."""
    note = check_text(text)
    ffmpeg = _ffmpeg()
    destination = Path(out_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    wav = synthesize(note)
    with wave.open(BytesIO(wav), "rb") as wf:
        spoken = wf.getnframes() / float(wf.getframerate())
    frame_count = max(1, round(spoken * FPS))
    video_seconds = frame_count / FPS
    wav = _pad_wav(wav, video_seconds)
    frames = frames_for(note, frame_count)

    with tempfile.TemporaryDirectory(prefix="anon-broadcast-") as tmp:
        folder = Path(tmp)
        wav_path = folder / "voice.wav"
        wav_path.write_bytes(wav)
        for index, frame in enumerate(frames):
            (folder / f"frame_{index:04d}.ppm").write_bytes(frame)
        encoded = folder / "encoded.mp4"
        encode = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-framerate",
            str(FPS),
            "-i",
            str(folder / "frame_%04d.ppm"),
            "-i",
            str(wav_path),
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-fflags",
            "+bitexact",
            "-flags:v",
            "+bitexact",
            "-flags:a",
            "+bitexact",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "64k",
            "-shortest",
            str(encoded),
        ]
        # Remux drops the encoder name. Muxer handler atoms stay at their default.
        remux = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(encoded),
            "-map_metadata",
            "-1",
            "-c",
            "copy",
            "-fflags",
            "+bitexact",
            "-movflags",
            "+faststart",
            "-metadata:s:v:0",
            "encoder=",
            "-metadata:s:a:0",
            "encoder=",
            str(destination),
        ]
        try:
            subprocess.run(encode, check=True, capture_output=True)
            subprocess.run(remux, check=True, capture_output=True)
        except subprocess.CalledProcessError as exc:
            destination.unlink(missing_ok=True)
            detail = (exc.stderr or b"").decode("utf-8", "replace").strip()
            tail = detail.splitlines()[-1] if detail else "ffmpeg failed"
            raise RenderError(f"ffmpeg did not write the MP4. {tail}", 3) from exc

    payload = destination.read_bytes()
    if len(payload) < 32 or payload[4:8] != b"ftyp":
        destination.unlink(missing_ok=True)
        raise RenderError("The render finished without a readable MP4. Nothing was kept.", 3)

    receipt = {
        "product": PRODUCT,
        "version": VERSION,
        "author": AUTHOR,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "text_sha256": hashlib.sha256(note.encode("utf-8")).hexdigest(),
        "voice": "local-formant-en",
        "sample_rate": SAMPLE_RATE,
        "frames": frame_count,
        "fps": FPS,
        "metadata": "culled",
        "container": "mp4",
    }
    receipt_path = destination.with_suffix(".receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def write_preview_png(text: str, png_path: str | os.PathLike[str]) -> None:
    """Write one fully revealed frame as PNG, using ffmpeg."""
    note = check_text(text)
    ffmpeg = _ffmpeg()
    destination = Path(png_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame = frames_for(note, 1)[-1]
    with tempfile.TemporaryDirectory(prefix="anon-broadcast-preview-") as tmp:
        ppm = Path(tmp) / "frame.ppm"
        ppm.write_bytes(frame)
        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(ppm),
            "-frames:v",
            "1",
            str(destination),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
