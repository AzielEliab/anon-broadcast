"""Small English formant voice.

This is a local synthesizer: letters become phonemes, phonemes become a
waveform. It is one pitched voice at a fixed fundamental. It is not a
recording of a person.

Author: Aziel Eliab.
"""

from __future__ import annotations

import math
import struct
import wave
from io import BytesIO

SAMPLE_RATE = 16000
F0 = 118.0

# kind, f1, f2, f3, milliseconds
# v = voiced formant, n = noise, m = voiced plus noise, s = stop, p = pause
_SPECS: dict[str, tuple[str, float, float, float, int]] = {
    "AA": ("v", 730, 1090, 2440, 120),
    "AE": ("v", 660, 1720, 2410, 110),
    "AH": ("v", 640, 1190, 2390, 90),
    "AO": ("v", 570, 840, 2410, 120),
    "EH": ("v", 530, 1840, 2480, 100),
    "ER": ("v", 490, 1350, 1690, 110),
    "IH": ("v", 390, 1990, 2550, 80),
    "IY": ("v", 270, 2290, 3010, 110),
    "OW": ("v", 570, 840, 2410, 120),
    "UW": ("v", 300, 870, 2240, 120),
    "UH": ("v", 440, 1020, 2240, 90),
    "AY": ("v", 730, 1090, 2440, 70),
    "AY2": ("v", 390, 1990, 2550, 70),
    "EY": ("v", 530, 1840, 2480, 60),
    "EY2": ("v", 270, 2290, 3010, 70),
    "OY": ("v", 570, 840, 2410, 60),
    "OY2": ("v", 390, 1990, 2550, 70),
    "AW": ("v", 730, 1090, 2440, 70),
    "AW2": ("v", 300, 870, 2240, 70),
    "S": ("n", 0, 3800, 6200, 90),
    "SH": ("n", 0, 2500, 5200, 100),
    "F": ("n", 0, 1800, 5600, 70),
    "TH": ("n", 0, 1600, 4800, 70),
    "HH": ("n", 500, 1400, 2800, 50),
    "Z": ("m", 280, 1500, 4800, 80),
    "V": ("m", 250, 1200, 3000, 70),
    "B": ("s", 220, 900, 2100, 55),
    "P": ("s", 220, 1100, 2300, 55),
    "D": ("s", 260, 1500, 2700, 50),
    "T": ("s", 280, 1700, 3200, 50),
    "K": ("s", 320, 1900, 2900, 55),
    "G": ("s", 300, 1500, 2500, 55),
    "CH": ("s", 320, 1900, 4800, 40),
    "CH2": ("n", 300, 1900, 5000, 70),
    "JH": ("s", 280, 1600, 4000, 40),
    "JH2": ("m", 280, 1600, 4200, 70),
    "M": ("v", 280, 900, 2200, 80),
    "N": ("v", 280, 1450, 2500, 70),
    "NG": ("v", 280, 1100, 2300, 80),
    "L": ("v", 400, 1200, 2600, 70),
    "R": ("v", 420, 1100, 1600, 70),
    "W": ("v", 320, 680, 2200, 70),
    "Y": ("v", 300, 2100, 2900, 60),
    "SP": ("p", 0, 0, 0, 70),
    "COMMA": ("p", 0, 0, 0, 150),
    "PERIOD": ("p", 0, 0, 0, 220),
}

_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("tion", ("SH", "AH", "N")),
    ("ture", ("CH", "ER")),
    ("igh", ("AY", "AY2")),
    ("ee", ("IY",)),
    ("ea", ("IY",)),
    ("oo", ("UW",)),
    ("ai", ("EY", "EY2")),
    ("ay", ("EY", "EY2")),
    ("oa", ("OW",)),
    ("ou", ("AW", "AW2")),
    ("ow", ("OW",)),
    ("oi", ("OY", "OY2")),
    ("oy", ("OY", "OY2")),
    ("ch", ("CH", "CH2")),
    ("sh", ("SH",)),
    ("th", ("TH",)),
    ("ph", ("F",)),
    ("wh", ("W",)),
    ("ng", ("NG",)),
    ("qu", ("K", "W")),
    ("ck", ("K",)),
    ("ar", ("AA", "R")),
    ("er", ("ER",)),
    ("ir", ("ER",)),
    ("or", ("AO", "R")),
    ("ur", ("ER",)),
)

_LETTERS: dict[str, tuple[str, ...]] = {
    "a": ("AE",),
    "b": ("B",),
    "c": ("K",),
    "d": ("D",),
    "e": ("EH",),
    "f": ("F",),
    "g": ("G",),
    "h": ("HH",),
    "i": ("IH",),
    "j": ("JH", "JH2"),
    "k": ("K",),
    "l": ("L",),
    "m": ("M",),
    "n": ("N",),
    "o": ("AA",),
    "p": ("P",),
    "q": ("K",),
    "r": ("R",),
    "s": ("S",),
    "t": ("T",),
    "u": ("AH",),
    "v": ("V",),
    "w": ("W",),
    "x": ("K", "S"),
    "y": ("IY",),
    "z": ("Z",),
}


def phonemes_for(text: str) -> list[str]:
    """Map basic Latin text to the phoneme sequence this voice can say."""
    lowered = text.lower()
    out: list[str] = []
    i = 0
    n = len(lowered)
    while i < n:
        ch = lowered[i]
        if ch == "\n":
            out.append("PERIOD")
            i += 1
            continue
        if ch in " \t":
            out.append("SP")
            i += 1
            continue
        if ch in ".!?":
            out.append("PERIOD")
            i += 1
            continue
        if ch in ",;:":
            out.append("COMMA")
            i += 1
            continue
        if ch in "-—/":
            out.append("SP")
            i += 1
            continue
        if ch in "'\"":
            i += 1
            continue
        matched = False
        for token, phones in _RULES:
            if lowered.startswith(token, i):
                out.extend(phones)
                i += len(token)
                matched = True
                break
        if matched:
            continue
        if ch in _LETTERS:
            out.extend(_LETTERS[ch])
            i += 1
            continue
        if ch.isdigit():
            out.extend(_LETTERS.get(ch, ("SP",)))
            # digits are spoken as their names via a tiny map below
            i += 1
            continue
        i += 1
    return _expand_digits(text, out)


_DIGIT_NAMES = {
    "0": ("Z", "IY", "R", "OW"),
    "1": ("W", "AH", "N"),
    "2": ("T", "UW"),
    "3": ("TH", "R", "IY"),
    "4": ("F", "AO", "R"),
    "5": ("F", "AY", "AY2", "V"),
    "6": ("S", "IH", "K", "S"),
    "7": ("S", "EH", "V", "AH", "N"),
    "8": ("EY", "EY2", "T"),
    "9": ("N", "AY", "AY2", "N"),
}


def _expand_digits(text: str, rough: list[str]) -> list[str]:
    """Replace the placeholder letter path for digits with number names.

    phonemes_for walks the original text for digits separately so a digit
    is a spoken name, not a skipped mark.
    """
    if not any(ch.isdigit() for ch in text):
        return rough
    out: list[str] = []
    i = 0
    lowered = text.lower()
    n = len(lowered)
    while i < n:
        ch = lowered[i]
        if ch.isdigit():
            if out and out[-1] != "SP":
                out.append("SP")
            out.extend(_DIGIT_NAMES[ch])
            out.append("SP")
            i += 1
            continue
        if ch == "\n":
            out.append("PERIOD")
            i += 1
            continue
        if ch in " \t-/—":
            out.append("SP")
            i += 1
            continue
        if ch in ".!?":
            out.append("PERIOD")
            i += 1
            continue
        if ch in ",;:":
            out.append("COMMA")
            i += 1
            continue
        if ch in "'\"":
            i += 1
            continue
        matched = False
        for token, phones in _RULES:
            if lowered.startswith(token, i):
                out.extend(phones)
                i += len(token)
                matched = True
                break
        if matched:
            continue
        if ch in _LETTERS:
            out.extend(_LETTERS[ch])
        i += 1
    return out


def _rng(seed: int):
    state = seed & 0xFFFFFFFF or 1

    def nxt() -> float:
        nonlocal state
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        return (state / 4294967295.0) * 2.0 - 1.0

    return nxt


def _two_pole(samples: list[float], freq: float, bw: float, sr: int) -> list[float]:
    if freq <= 0 or not samples:
        return samples
    radius = math.exp(-math.pi * bw / sr)
    a1 = 2.0 * radius * math.cos(2.0 * math.pi * freq / sr)
    a2 = -(radius * radius)
    y1 = 0.0
    y2 = 0.0
    out = [0.0] * len(samples)
    for i, sample in enumerate(samples):
        y = sample + a1 * y1 + a2 * y2
        y2 = y1
        y1 = y
        out[i] = y
    return out


def _envelope(n: int) -> list[float]:
    if n <= 1:
        return [1.0] * n
    edge = max(1, int(n * 0.12))
    env = [1.0] * n
    for i in range(edge):
        env[i] = i / edge
        env[-1 - i] = i / edge
    return env


def _render_phone(name: str, sr: int = SAMPLE_RATE) -> list[float]:
    kind, f1, f2, f3, ms = _SPECS[name]
    n = max(1, int(sr * ms / 1000))
    if kind == "p":
        return [0.0] * n
    noise = _rng(0xA11CE + sum(ord(c) for c in name) * 97 + n)
    period = max(1, int(sr / F0))
    src = [0.0] * n
    if kind == "s":
        burst_at = int(n * 0.45)
        burst_end = min(n, burst_at + max(1, int(sr * 0.012)))
        for i in range(n):
            if burst_at <= i < burst_end:
                src[i] = noise() * 0.85
            elif i >= burst_end and (i - burst_end) % period == 0:
                src[i] = 0.55
    elif kind == "n":
        prev = 0.0
        for i in range(n):
            raw = noise()
            src[i] = (raw - prev) * 0.9
            prev = raw
    elif kind == "m":
        for i in range(n):
            impulse = 0.7 if i % period == 0 else 0.0
            src[i] = impulse + noise() * 0.28
    else:
        for i in range(n):
            src[i] = 1.0 if i % period == 0 else 0.0
    b1 = _two_pole(src, f1, 90, sr) if f1 > 0 else [0.0] * n
    b2 = _two_pole(src, f2, 140, sr) if f2 > 0 else [0.0] * n
    b3 = _two_pole(src, f3, 200, sr) if f3 > 0 else [0.0] * n
    env = _envelope(n)
    mixed = [0.0] * n
    if kind == "n":
        w1, w2, w3 = 0.0, 0.85, 0.55
    else:
        w1, w2, w3 = 0.72, 0.38, 0.16
    for i in range(n):
        mixed[i] = (b1[i] * w1 + b2[i] * w2 + b3[i] * w3) * env[i]
    return mixed


def synthesize(text: str, sr: int = SAMPLE_RATE) -> bytes:
    """Return a mono 16-bit PCM WAV for text."""
    phones = phonemes_for(text)
    if not phones:
        phones = ["SP"]
    chunks: list[float] = []
    for phone in phones:
        chunks.extend(_render_phone(phone, sr))
    peak = max((abs(s) for s in chunks), default=0.0)
    scale = 12000.0 / peak if peak > 1e-8 else 0.0
    pcm = [int(max(-32767, min(32767, s * scale))) for s in chunks]
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b"".join(struct.pack("<h", sample) for sample in pcm))
    return buf.getvalue()


def zero_crossing_rate(wav: bytes) -> float:
    """Fraction of adjacent samples that change sign. Used by tests."""
    with wave.open(BytesIO(wav), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    samples = [s[0] for s in struct.iter_unpack("<h", raw)]
    if len(samples) < 2:
        return 0.0
    flips = 0
    for a, b in zip(samples, samples[1:]):
        if (a >= 0) != (b >= 0):
            flips += 1
    return flips / (len(samples) - 1)


def duration_seconds(wav: bytes) -> float:
    with wave.open(BytesIO(wav), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())
