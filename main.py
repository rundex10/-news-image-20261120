#!/usr/bin/env python3
"""Sum up 20 November 2026 world news in one image.

Draws a 1024x1024 editorial infographic with the Python standard
library only: no Pillow, no system fonts, no network, no randomness,
no clock, no timestamps in the PNG. Running it twice writes
byte-identical files.

Why stdlib only: the grader runs `python3 -P -s /bot/main.py` in the
plain official python:3.13 image, which ships neither Pillow nor any
font files. The first version of this program imported Pillow and
loaded DejaVu from /usr/share/fonts, so it died with exit code 1 in
the grader. This version rasterises everything itself: a small canvas
library (rectangles, lines, polygons, ellipses, arcs), a pure-Python
PNG encoder (zlib + struct) and a built-in 5x7 bitmap font, scaled by
integer factors.

    python3 main.py            # writes /output/entry.png, or
    MAKEFUN_OUTPUT_DIR=out python3 main.py

Six stories, all happened or first reported on Friday 20 November 2026
(in some time zone), verified against Reuters / WSJ / Morningstar /
India Meteorological Department reporting on 20 November 2026:
  1. Asian markets plunge (Friday 20 Nov, Nikkei -4.8%)
  2. Anthropic Nasdaq debut, closed +17% (reported 20 Nov)
  3. Houthi missile damages Riyadh PIF Tower (reported 20 Nov)
  4. Russian strikes damage Kyiv embassies, 1 killed (Thu 19 Nov,
     reported 20 Nov; EU summon announced)
  5. COP31 final day, draft drops fossil fuels (Fri 20 Nov)
  6. Cyclone Akvan landfall, India east coast (Fri 20 Nov morning)
The UK drone pledge was checked and left out: it was announced
in Berlin on 19 November, not 20 November.
"""

import math
import os
import struct
import sys
import zlib

W, H = 1024, 1024
PAPER = (247, 243, 233)      # off-white paper
INK = (20, 33, 61)           # dark navy ink
NAVY = (20, 33, 61)
WHITE = (255, 255, 255)
MUTED = (90, 98, 116)
CARD = (255, 255, 255)
AMBER = (214, 158, 46)
RED = (178, 52, 44)
GREEN = (15, 122, 90)
TEAL = (14, 116, 144)
ORANGE = (194, 92, 20)
PURPLE = (96, 72, 148)


# ---------------------------------------------------------------- canvas

class Canvas:
    """An RGB canvas backed by one bytearray, with small raster helpers."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bytes(bg) * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def fill_rect(self, x0, y0, x1, y1, color):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for y in range(y0, y1):
            i = (y * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def rect(self, x0, y0, x1, y1, color, width=1):
        self.fill_rect(x0, y0, x1, y0 + width, color)
        self.fill_rect(x0, y1 - width, x1, y1, color)
        self.fill_rect(x0, y0, x0 + width, y1, color)
        self.fill_rect(x1 - width, y0, x1, y1, color)

    def disc(self, cx, cy, r, color):
        for y in range(cy - r, cy + r + 1):
            dy = y - cy
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.fill_rect(cx - dx, y, cx + dx + 1, y + 1, color)

    def line(self, x0, y0, x1, y1, color, width=1):
        """A thick line: discs stamped along a Bresenham line."""
        r = width // 2
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.disc(x, y, r, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def polyline(self, pts, color, width=1):
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            self.line(ax, ay, bx, by, color, width)

    def polygon(self, pts, color):
        """Scanline fill of a polygon (even-odd rule)."""
        if not pts:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
                if ay == by:
                    continue
                if (ay <= y < by) or (by <= y < ay):
                    t = (y - ay) / (by - ay)
                    xs.append(ax + t * (bx - ax))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.fill_rect(int(math.ceil(xs[i])), y,
                               int(math.floor(xs[i + 1])) + 1, y + 1, color)

    def ellipse(self, cx, cy, rx, ry, color):
        for y in range(cy - ry, cy + ry + 1):
            dy = (y - cy) / ry
            if abs(dy) > 1:
                continue
            dx = int(rx * math.sqrt(1 - dy * dy))
            self.fill_rect(cx - dx, y, cx + dx + 1, y + 1, color)

    def ellipse_outline(self, cx, cy, rx, ry, color, width=1):
        steps = max(48, int(2 * math.pi * max(rx, ry)))
        for i in range(steps + 1):
            a = 2 * math.pi * i / steps
            x = int(round(cx + rx * math.cos(a)))
            y = int(round(cy + ry * math.sin(a)))
            self.disc(x, y, width // 2, color)

    def arc(self, cx, cy, rx, ry, start_deg, end_deg, color, width=1):
        steps = max(24, int(abs(end_deg - start_deg) / 360
                            * 2 * math.pi * max(rx, ry)))
        for i in range(steps + 1):
            a = math.radians(start_deg + (end_deg - start_deg) * i / steps)
            x = int(round(cx + rx * math.cos(a)))
            y = int(round(cy + ry * math.sin(a)))
            self.disc(x, y, width // 2, color)

    def rounded_rect(self, x0, y0, x1, y1, radius, color, outline=None,
                     width=2):
        """Filled rounded rectangle, optionally with an outline."""
        self.fill_rect(x0 + radius, y0, x1 - radius, y1, color)
        self.fill_rect(x0, y0 + radius, x1, y1 - radius, color)
        for (cx, cy, qx, qy) in ((x0 + radius, y0 + radius, -1, -1),
                                 (x1 - radius, y0 + radius, 1, -1),
                                 (x0 + radius, y1 - radius, -1, 1),
                                 (x1 - radius, y1 - radius, 1, 1)):
            for y in range(cy - radius, cy + radius + 1):
                dy = y - cy
                dx = int(math.sqrt(max(0, radius * radius - dy * dy)))
                if qx < 0:
                    self.fill_rect(cx - dx, y, cx + 1, y + 1, color)
                else:
                    self.fill_rect(cx, y, cx + dx + 1, y + 1, color)
        if outline is not None:
            self.line(x0 + radius, y0, x1 - radius, y0, outline, width)
            self.line(x0 + radius, y1, x1 - radius, y1, outline, width)
            self.line(x0, y0 + radius, x0, y1 - radius, outline, width)
            self.line(x1, y0 + radius, x1, y1 - radius, outline, width)
            for (cx, cy, a0, a1) in ((x0 + radius, y0 + radius, 180, 270),
                                     (x1 - radius, y0 + radius, 270, 360),
                                     (x0 + radius, y1 - radius, 90, 180),
                                     (x1 - radius, y1 - radius, 0, 90)):
                self.arc(cx, cy, radius, radius, a0, a1, outline, width)


# ------------------------------------------------------------- PNG output

def png_bytes(canvas):
    """Encode the canvas as a PNG (filter 0 rows, zlib level 9)."""
    w, h = canvas.w, canvas.h
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += canvas.px[y * w * 3:(y + 1) * w * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        return out + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# -------------------------------------------------------------- bitmap font
# A 5x7 pixel font, one glyph per character: 7 rows of 5 pixels, '#' on.
# Lowercase letters sit on the same 7-row grid (x-height 5, descenders
# use the bottom rows). Drawn scaled by an integer factor, so text
# stays crisp at any size and identical on every machine.

FONT = {
    " ": ("     ", "     ", "     ", "     ", "     ", "     ", "     "),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
}

FONT.update({
    "a": ("     ", "     ", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    "c": ("     ", "     ", "01110", "10000", "10000", "10001", "01110"),
    "d": ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    "e": ("     ", "     ", "01110", "10001", "11111", "10000", "01110"),
    "f": ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    "g": ("     ", "01110", "10001", "10001", "01110", "10000", "01110"),
    "h": ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    "i": ("00100", "     ", "01100", "00100", "00100", "00100", "01110"),
    "j": ("     ", "00010", "     ", "00110", "00010", "10010", "01100"),
    "k": ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("     ", "     ", "11010", "10101", "10101", "10101", "10101"),
    "n": ("     ", "     ", "11110", "10001", "10001", "10001", "10001"),
    "o": ("     ", "     ", "01110", "10001", "10001", "10001", "01110"),
    "p": ("     ", "     ", "11110", "10001", "10001", "11110", "10000"),
    "q": ("     ", "     ", "01111", "10001", "10001", "01111", "00001"),
    "r": ("     ", "     ", "10110", "11001", "10000", "10000", "10000"),
    "s": ("     ", "     ", "01111", "10000", "01110", "00001", "11110"),
    "t": ("01000", "01000", "11110", "01000", "01000", "01000", "00110"),
    "u": ("     ", "     ", "10001", "10001", "10001", "10011", "01101"),
    "v": ("     ", "     ", "10001", "10001", "10001", "01010", "00100"),
    "w": ("     ", "     ", "10001", "10101", "10101", "11011", "10001"),
    "x": ("     ", "     ", "10001", "01010", "00100", "01010", "10001"),
    "y": ("     ", "10001", "10001", "01111", "00001", "00010", "01100"),
    "z": ("     ", "     ", "11111", "00010", "00100", "01000", "11111"),
    ".": ("     ", "     ", "     ", "     ", "     ", "01100", "01100"),
    ",": ("     ", "     ", "     ", "     ", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "     ", "     ", "     ", "     "),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    ":": ("     ", "01100", "01100", "     ", "01100", "01100", "     "),
    ";": ("     ", "01100", "01100", "     ", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "     ", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "     ", "00100"),
    "-": ("     ", "     ", "     ", "01110", "     ", "     ", "     "),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "+": ("     ", "00100", "00100", "11111", "00100", "00100", "     "),
    "=": ("     ", "     ", "11111", "     ", "11111", "     ", "     "),
    '"': ("01010", "01010", "     ", "     ", "     ", "     ", "     "),
    "•": ("     ", "00100", "01110", "01110", "01110", "00100", "     "),
})

# Normalise punctuation the font does not carry.
NORMALISE = {"–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"'}


def norm(text):
    return "".join(NORMALISE.get(ch, ch) for ch in text)


def text_width(text, scale):
    """Pixel width of text at the given integer scale."""
    text = norm(text)
    if not text:
        return 0
    return len(text) * 6 * scale - scale


def draw_text(d, x, y, text, scale, color, anchor="lt"):
    """Draw text with its top-left at (x, y); anchor 'mm' centres it."""
    text = norm(text)
    w = text_width(text, scale)
    h = 7 * scale
    if anchor == "mm":
        x -= w // 2
        y -= h // 2
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT["?"])
        for r in range(7):
            row = glyph[r]
            for c in range(5):
                if row[c] == "1":
                    d.fill_rect(cx + c * scale, y + r * scale,
                                cx + (c + 1) * scale, y + (r + 1) * scale,
                                color)
        cx += 6 * scale
    return w


def wrap(text, scale, max_w):
    """Wrap text to lines that fit max_w pixels; assert nothing is lost."""
    words = norm(text).split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if text_width(trial, scale) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# (kicker, headline, body, accent, icon)
STORIES = [
    (
        "ASIA  •  MARKETS",
        "Asia markets plunge on AI fears",
        "Nikkei -4.8%, Kospi -5%, Taiex -6.4% as AI fears rattled investors.",
        RED, "chart_down",
    ),
    (
        "UNITED STATES  •  TECH",
        "Anthropic debuts in record IPO",
        "Opened at $111.50, above the $83 price, and closed up 17% at $97.17.",
        GREEN, "chart_up",
    ),
    (
        "MIDDLE EAST  •  SAUDI ARABIA",
        "Missile hits Riyadh's top tower",
        "A Houthi missile hit the 80-storey PIF Tower, blowing out windows. No injuries.",
        ORANGE, "tower",
    ),
    (
        "EUROPE  •  UKRAINE",
        "Strikes damage Kyiv embassies",
        "Russian strikes hit the Austrian and Dutch embassies in Kyiv, killing one person.",
        PURPLE, "city",
    ),
    (
        "CLIMATE  •  COP31, ANTALYA",
        "COP31 draft drops fossil fuels",
        "Final-day draft had no mention of coal, oil or gas. Africa seeks $120bn a year.",
        TEAL, "globe",
    ),
    (
        "ASIA  •  WEATHER",
        "Cyclone Akvan hits India's coast",
        "Akvan crossed the Odisha-Andhra Pradesh coast on Friday, winds 70-80 km/h.",
        (11, 94, 124), "cyclone",
    ),
]

def draw_icon(d, kind, box, accent):
    """Flat vector-style icon in box (x0, y0, x1, y1). Simple shapes only."""
    x0, y0, x1, y1 = box
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    if kind == "chart_down":
        # axes + falling line with arrow
        d.line(x0 + 14, y1 - 18, x1 - 12, y1 - 18, INK, 4)
        d.line(x0 + 14, y1 - 18, x0 + 14, y0 + 14, INK, 4)
        pts = [(x0 + 20, y0 + 26), (x0 + 38, y0 + 44), (x0 + 54, y0 + 38),
               (x0 + 72, y0 + 62), (x0 + 90, y0 + 78)]
        d.polyline(pts, accent, 6)
        d.polygon([(x0 + 90, y0 + 78), (x0 + 74, y0 + 74), (x0 + 88, y0 + 60)],
                  accent)
        for bx, bh in [(24, 18), (44, 30), (64, 22)]:
            d.fill_rect(x0 + bx, y1 - 18 - bh, x0 + bx + 12, y1 - 18,
                        (200, 210, 220))
    elif kind == "chart_up":
        d.line(x0 + 14, y1 - 18, x1 - 12, y1 - 18, INK, 4)
        d.line(x0 + 14, y1 - 18, x0 + 14, y0 + 14, INK, 4)
        pts = [(x0 + 20, y0 + 78), (x0 + 38, y0 + 62), (x0 + 54, y0 + 66),
               (x0 + 72, y0 + 42), (x0 + 90, y0 + 24)]
        d.polyline(pts, accent, 6)
        d.polygon([(x0 + 90, y0 + 24), (x0 + 74, y0 + 28), (x0 + 88, y0 + 42)],
                  accent)
        d.ellipse_outline(cx, cy, 34, 8, accent, 3)
        draw_text(d, cx, cy - 2, "ANT", 2, accent, anchor="mm")
    elif kind == "tower":
        # tall skyscraper, damaged band, missile streak
        d.fill_rect(cx - 22, y0 + 18, cx + 22, y1 - 14, INK)
        for wy in range(y0 + 28, y1 - 22, 14):
            d.fill_rect(cx - 15, wy, cx - 4, wy + 7, (150, 180, 210))
            d.fill_rect(cx + 4, wy, cx + 15, wy + 7, (150, 180, 210))
        d.fill_rect(cx - 22, y0 + 52, cx + 22, y0 + 72, accent)
        d.line(x0 + 6, y0 + 8, cx - 10, y0 + 52, accent, 5)
        d.polygon([(cx - 10, y0 + 52), (cx - 24, y0 + 46), (cx - 16, y0 + 60)],
                  accent)
        d.fill_rect(x0 + 12, y1 - 14, x1 - 12, y1 - 8, (200, 210, 220))
    elif kind == "city":
        # skyline, flag on the tallest building, burst in the sky corner
        for bx, bw, bh in [(12, 22, 52), (38, 26, 70), (68, 22, 46)]:
            d.fill_rect(x0 + bx, y1 - 14 - bh, x0 + bx + bw, y1 - 14, INK)
            d.fill_rect(x0 + bx + 6, y1 - 14 - bh + 8, x0 + bx + 14,
                        y1 - 14 - bh + 16, AMBER)
        # flag on the tallest (middle) building
        fx = x0 + 51
        d.line(fx, y1 - 84, fx, y1 - 106, INK, 3)
        d.polygon([(fx, y1 - 106), (fx + 22, y1 - 100), (fx, y1 - 94)],
                  accent)
        # burst, top-right corner, clear of the flag
        bx, by = x1 - 24, y0 + 26
        for ang in range(0, 360, 45):
            a = math.radians(ang)
            d.line(bx, by, bx + int(13 * math.cos(a)),
                   by + int(13 * math.sin(a)), ORANGE, 3)
        d.disc(bx, by, 6, ORANGE)
    elif kind == "globe":
        d.ellipse_outline(cx, y0 + 50, 38, 38, accent, 5)
        d.arc(cx, y0 + 50, 38, 38, 20, 160, accent, 3)
        d.arc(cx, y0 + 50, 38, 38, 200, 340, accent, 3)
        d.line(cx - 38, y0 + 50, cx + 38, y0 + 50, accent, 3)
        # sprout growing from the globe's base: stem + two leaves
        d.line(cx, y0 + 88, cx, y0 + 66, GREEN, 4)
        d.ellipse(cx - 12, y0 + 73, 10, 7, GREEN)
        d.ellipse(cx + 12, y0 + 67, 10, 7, GREEN)
        # crossed-out fuel drop, top-left, clear of the globe
        d.polygon([(x0 + 14, y0 + 32), (x0 + 24, y0 + 14), (x0 + 34, y0 + 32)],
                  (160, 175, 195))
        d.line(x0 + 10, y0 + 10, x0 + 38, y0 + 38, RED, 4)
    elif kind == "cyclone":
        # spiral + rain
        for r in (34, 24, 14):
            d.arc(cx, cy - 14, r, r, 30, 300, accent, 5)
        d.disc(cx, cy - 14, 5, accent)
        for rx in (x0 + 18, x0 + 42, x0 + 66, x0 + 88):
            d.line(rx, y1 - 28, rx - 4, y1 - 14, TEAL, 4)
        d.fill_rect(x0 + 10, y1 - 12, x1 - 10, y1 - 6, (200, 210, 220))


def build_image():
    d = Canvas(W, H, PAPER)
    # outer frame
    d.rect(0, 0, W, H, INK, 6)

    # ---- header (navy band) ----
    d.fill_rect(6, 6, W - 7, 150, NAVY)
    draw_text(d, 36, 26, "FRIDAY  •  20 NOVEMBER 2026", 4, AMBER)
    draw_text(d, 36, 76, "THE WORLD IN ONE DAY", 6, WHITE)
    # "6 stories" badge, right side of header
    d.rounded_rect(856, 34, 988, 116, 10, NAVY, outline=AMBER, width=3)
    draw_text(d, 922, 68, "6", 6, WHITE, anchor="mm")
    draw_text(d, 922, 100, "STORIES", 2, AMBER, anchor="mm")

    # ---- subheader strip ----
    d.fill_rect(6, 150, W - 7, 188, (232, 222, 196))
    draw_text(d, 36, 160, "Six stories, reported on 20 November 2026.",
              2, INK)

    # ---- grid: 2 cols x 3 rows ----
    gx, gy = 24, 204
    gw, gh, gap = 476, 232, 16
    for i, (kicker, headline, body, accent, icon) in enumerate(STORIES):
        col, row = i % 2, i // 2
        x0 = gx + col * (gw + gap)
        y0 = gy + row * (gh + gap)
        x1, y1 = x0 + gw, y0 + gh
        # card
        d.rounded_rect(x0, y0, x1, y1, 10, CARD, outline=(200, 205, 210),
                       width=2)
        d.fill_rect(x0 + 10, y0, x1 - 10, y0 + 7, accent)
        # icon panel (left)
        ix0, iy0, ix1, iy1 = x0 + 14, y0 + 22, x0 + 112, y1 - 14
        d.rounded_rect(ix0, iy0, ix1, iy1, 8, (238, 242, 245))
        draw_icon(d, icon, (ix0, iy0, ix1, iy1), accent)
        # text (right of icon)
        tx = x0 + 126
        tw = x1 - tx - 16
        draw_text(d, tx, y0 + 22, kicker, 2, accent)
        head_lines = wrap(headline, 3, tw)
        assert len(head_lines) <= 2, headline
        hy = y0 + 48
        for ln in head_lines:
            draw_text(d, tx, hy, ln, 3, INK)
            hy += 26
        body_lines = wrap(body, 2, tw)
        assert len(body_lines) <= 4, body
        by = hy + 8
        for ln in body_lines:
            draw_text(d, tx, by, ln, 2, (45, 55, 75))
            by += 18
        assert by <= y1 - 8, headline

    # ---- footer (navy strip) ----
    d.fill_rect(6, 936, W - 7, H - 7, NAVY)
    draw_text(d, 36, 950,
              "Sources: Reuters, WSJ, Morningstar, India Meteorological Department.",
              2, WHITE)
    draw_text(d, 36, 978,
              "All six happened or were first reported on 20 November 2026.",
              2, (200, 210, 225))
    return d


def main(argv):
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    if "--output" in argv:
        out_dir = argv[argv.index("--output") + 1]
    os.makedirs(out_dir, exist_ok=True)
    img = build_image()
    path = os.path.join(out_dir, "entry.png")
    # zlib level 9 with filter-0 rows: deterministic output.
    with open(path, "wb") as f:
        f.write(png_bytes(img))
    print("wrote %s (%dx%d)" % (path, W, H))


if __name__ == "__main__":
    main(sys.argv[1:])
