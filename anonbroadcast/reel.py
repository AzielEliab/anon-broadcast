"""Desk-reel frames for a communique.

Each frame is a PPM image: a desk, a paper card, and the note revealing
as the voice plays. Glyphs are the public-domain 8x8 table in font8x8.py.

Author: Aziel Eliab.
"""

from __future__ import annotations

from anonbroadcast.font8x8 import FONT

WIDTH = 960
HEIGHT = 540
FPS = 8
SCALE = 3

DESK = (92, 70, 50)
DESK_EDGE = (72, 54, 38)
PAPER = (243, 234, 215)
INK = (42, 36, 28)
RULE = (138, 106, 50)
QUIET = (107, 94, 74)


def _canvas(color: tuple[int, int, int]) -> bytearray:
    pixel = bytes(color)
    return bytearray(pixel * (WIDTH * HEIGHT))


def _fill(
    buf: bytearray,
    x: int,
    y: int,
    rw: int,
    rh: int,
    color: tuple[int, int, int],
) -> None:
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(WIDTH, x + rw)
    y1 = min(HEIGHT, y + rh)
    if x0 >= x1 or y0 >= y1:
        return
    pixel = bytes(color)
    span = pixel * (x1 - x0)
    for yy in range(y0, y1):
        start = (yy * WIDTH + x0) * 3
        buf[start : start + len(span)] = span


def _glyph(ch: str) -> tuple[int, ...]:
    code = ord(ch)
    if 0 <= code < 128:
        row = FONT[code]
        if any(row):
            return row
    return FONT[ord("?")]


def _blit(buf: bytearray, ch: str, x: int, y: int, color: tuple[int, int, int]) -> None:
    bits_rows = _glyph(ch)
    for row_i, bits in enumerate(bits_rows):
        if not bits:
            continue
        for col in range(8):
            if bits & (1 << (7 - col)):
                _fill(buf, x + col * SCALE, y + row_i * SCALE, SCALE, SCALE, color)


def _text(buf: bytearray, text: str, x: int, y: int, color: tuple[int, int, int]) -> None:
    cursor = x
    for ch in text:
        _blit(buf, ch, cursor, y, color)
        cursor += 8 * SCALE


def wrap_lines(text: str, columns: int) -> list[str]:
    """Wrap on spaces. A single overlong word is split so it stays on the card."""
    columns = max(1, columns)
    lines: list[str] = []
    for paragraph in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            pieces = [word[i : i + columns] for i in range(0, len(word), columns)] or [""]
            for piece in pieces:
                trial = piece if not current else current + " " + piece
                if len(trial) <= columns:
                    current = trial
                else:
                    if current:
                        lines.append(current)
                    current = piece
        lines.append(current)
    return lines or [""]


def frame_ppm(text: str, reveal: int) -> bytes:
    """One desk-reel frame. reveal is how many wrapped characters are visible."""
    buf = _canvas(DESK)
    _fill(buf, 0, HEIGHT - 18, WIDTH, 18, DESK_EDGE)
    card_x, card_y, card_w, card_h = 150, 64, 660, 412
    _fill(buf, card_x, card_y, card_w, card_h, PAPER)
    _fill(buf, card_x + 28, card_y + 28, 72, 3, RULE)
    _text(buf, "NOTE", card_x + 28, card_y + 40, QUIET)
    columns = (card_w - 56) // (8 * SCALE)
    rows = wrap_lines(text, columns)
    max_rows = (card_h - 100) // (8 * SCALE + 6)
    rows = rows[:max_rows]
    budget = max(0, reveal)
    line_y = card_y + 78
    for line in rows:
        visible = line[:budget]
        if visible:
            _text(buf, visible, card_x + 28, line_y, INK)
        budget -= len(line)
        if budget > 0:
            budget -= 1  # the newline join between wrapped rows
        line_y += 8 * SCALE + 6
        if budget <= 0:
            break
    header = b"P6\n%d %d\n255\n" % (WIDTH, HEIGHT)
    return header + bytes(buf)


def frames_for(text: str, frame_count: int) -> list[bytes]:
    count = max(1, frame_count)
    columns = (660 - 56) // (8 * SCALE)
    wrapped = "\n".join(wrap_lines(text, columns))
    total = max(1, len(wrapped))
    frames = []
    for i in range(count):
        reveal = total if i == count - 1 else max(1, int(total * (i + 1) / count))
        frames.append(frame_ppm(text, reveal))
    return frames
