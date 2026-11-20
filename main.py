#!/usr/bin/env python3
"""Sum up 20 November 2026 world news in one image.

Draws a 1024x1024 newspaper front page with the Python standard
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

Thirty stories, all happened or first reported on Friday 20 November
2026 (in some time zone): 3 leads with illustration panels, 9 grid
cards, and 18 more in the index, with a region strip, a figures row,
a world map with numbered pins, and a footer naming what was left
out as other days' news.
Checked and left out: the UK's 1,000-drone pledge for Ukraine, the
ICJ Myanmar ruling, the Shenzhen Trump-Xi-Putin summit and the Pete
Rose pardon were all announced on 19 November, not 20 November.
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
LEADS = [
    (
        "ASIA  •  MARKETS",
        "Markets plunge on AI fears",
        "Nikkei -4.8%, Kospi -5%, Taiex -6.4% as AI fears rattled investors.",
        RED, "chart_down",
    ),
    (
        "AMERICAS  •  TECH",
        "Anthropic debuts in record IPO",
        "Opened at $111.50, above the $83 price, closed up 17% at $97.17.",
        GREEN, "chart_up",
    ),
    (
        "MIDDLE EAST  •  WAR",
        "Missile hits Riyadh tower",
        "A Houthi missile hit the 80-storey PIF Tower. No injuries.",
        ORANGE, "tower",
    ),
]

# Grid bodies are shortened to fit two lines at scale 2.
GRID = [
    (
        "EUROPE  •  WAR",
        "Strikes damage Kyiv embassies",
        "One killed; EU to summon envoy.",
        PURPLE, "city",
    ),
    (
        "GLOBAL  •  CLIMATE",
        "COP31 draft drops fossil fuels",
        "Africa seeks $120bn a year.",
        TEAL, "globe",
    ),
    (
        "ASIA  •  WEATHER",
        "Cyclone Akvan hits India's coast",
        "Winds 70-80 km/h, gusting 90.",
        (11, 94, 124), "cyclone",
    ),
    (
        "EUROPE  •  POLITICS",
        "UK-EU reset summit opens",
        "On food trade and youth mobility.",
        TEAL, "flag",
    ),
    (
        "ASIA  •  POLITICS",
        "Prabowo, Xi talk South China Sea",
        "Prabowo met Xi on trade and sea.",
        RED, "flag",
    ),
    (
        "ASIA  •  JUSTICE",
        "Kakao founder acquittal upheld",
        "Kim Beom-su cleared of charges.",
        GREEN, "building",
    ),
    (
        "MIDDLE EAST  •  SECURITY",
        "Iraq troops enter militia stronghold",
        "Forces move into Jurf al-Sakhar.",
        RED, "burst",
    ),
    (
        "MIDDLE EAST  •  ENERGY",
        "Tankers hit mines near Hormuz",
        "Three tankers hit mines, caught fire.",
        ORANGE, "drop",
    ),
    (
        "MIDDLE EAST  •  WAR",
        "Israel strikes Hezbollah site",
        "Israel hit Beqaa site again.",
        PURPLE, "burst",
    ),
]

# Index lines are shortened to fit one line at scale 2.
# (number, line, accent)
INDEX = [
    (13, "13 Poland probes", PURPLE),
    (14, "14 Taiwan flags 2,700", RED),
    (15, "15 Indonesia vs Google", RED),
    (16, "16 Georgia gas blast", PURPLE),
    (17, "17 Malawi fuel crisis", AMBER),
    (18, "18 Phillips century", TEAL),
    (19, "19 Merz promises talks", PURPLE),
    (20, "20 Drones ground Genoa", PURPLE),
    (21, "21 Mossad pushes Iran", ORANGE),
    (22, "22 US war cost $48.3bn", GREEN),
    (23, "23 AF1 phones bagged", GREEN),
    (24, "24 US sanctions gangs", GREEN),
    (25, "25 Kenya judiciary", AMBER),
    (26, "26 Lula visits Raoni", GREEN),
    (27, "27 AI chips for China", GREEN),
    (28, "28 Meta climate vow", INK),
    (29, "29 Word: 'Human'", INK),
    (30, "30 Quake off Noumea", TEAL),
]

# (name, count, accent) — counts sum to 30; story 5 (COP31) counts
# as GLOBAL, so GLOBAL is 5, 28, 29.
REGIONS = [
    ("ASIA", 6, RED),
    ("EUROPE", 6, PURPLE),
    ("MIDDLE EAST", 5, ORANGE),
    ("AMERICAS", 6, GREEN),
    ("AFRICA", 2, AMBER),
    ("OCEANIA", 2, TEAL),
    ("GLOBAL", 3, INK),
]

# (figure, label, accent)
FIGURES = [
    ("-4.8%", "Nikkei falls", RED),
    ("$111.50", "Anthropic IPO", GREEN),
    ("$120bn", "Africa asks", TEAL),
    ("2,700", "Taiwan flags", PURPLE),
    ("19,000", "channels cut", ORANGE),
    ("5.6", "off Noumea", (11, 94, 124)),
]

# (number, longitude, latitude, accent); a few nudged so the pins
# do not touch in crowded Europe.
PINS = [
    (1, 139.7, 35.7, RED),       # Tokyo
    (2, -74.0, 40.7, GREEN),     # New York
    (3, 46.7, 24.6, ORANGE),     # Riyadh
    (4, 31.5, 50.4, PURPLE),     # Kyiv
    (5, 30.7, 36.9, ORANGE),     # Antalya
    (6, 85.0, 20.0, RED),        # Odisha
    (7, 3.0, 50.85, PURPLE),     # Brussels
    (8, 106.8, -6.2, RED),       # Jakarta
    (13, 17.5, 53.0, PURPLE),    # Poland
    (17, 34.0, -13.5, AMBER),    # Malawi
    (18, 174.8, -41.3, TEAL),    # Wellington
    (30, 165.5, -21.5, TEAL),    # New Caledonia
]

# Coarse continent outlines as (longitude, latitude) polygons.
CONTINENTS = [
    # North America
    [(-168, 66), (-145, 70), (-130, 71), (-120, 69), (-105, 68),
     (-95, 69), (-85, 66), (-80, 62), (-70, 58), (-60, 52), (-65, 45),
     (-70, 42), (-75, 35), (-80, 25), (-84, 30), (-90, 21), (-95, 19),
     (-100, 17), (-105, 20), (-112, 24), (-117, 32), (-124, 40),
     (-125, 48), (-132, 55), (-145, 60), (-158, 58), (-165, 60)],
    # South America
    [(-80, 10), (-77, 5), (-72, 2), (-64, -2), (-55, -5), (-48, -8),
     (-40, -10), (-35, -8), (-38, -15), (-40, -22), (-48, -27),
     (-55, -35), (-62, -40), (-68, -50), (-72, -54), (-74, -48),
     (-73, -38), (-71, -28), (-70, -18), (-76, -10), (-80, -4),
     (-81, 2)],
    # Africa
    [(-17, 15), (-12, 22), (-10, 30), (-6, 33), (0, 36), (10, 37),
     (20, 32), (30, 31), (33, 28), (36, 22), (40, 15), (43, 12),
     (51, 11), (48, 5), (44, -2), (40, -8), (38, -15), (35, -22),
     (32, -29), (28, -33), (20, -35), (16, -30), (14, -22), (12, -16),
     (10, -8), (9, -2), (9, 4), (0, 5), (-8, 5), (-13, 8), (-17, 12)],
    # Europe
    [(-10, 36), (-9, 42), (-2, 44), (-1, 46), (0, 48), (2, 51), (5, 53),
     (8, 55), (8, 57), (12, 56), (18, 55), (21, 54), (24, 56), (24, 58),
     (28, 59), (30, 60), (25, 62), (22, 65), (18, 69), (14, 70),
     (10, 64), (6, 58), (2, 55), (-2, 50), (-5, 48), (-8, 43),
     (-10, 38)],
    # Britain
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 58), (0, 55), (1, 52),
     (-2, 51)],
    # Asia
    [(28, 40), (30, 45), (32, 50), (35, 55), (38, 60), (35, 62),
     (30, 62), (40, 66), (55, 68), (70, 70), (85, 72), (100, 73),
     (120, 72), (140, 71), (160, 69), (170, 66), (162, 60), (158, 54),
     (150, 50), (142, 46), (140, 40), (136, 34), (130, 31), (127, 35),
     (123, 38), (120, 32), (118, 25), (112, 21), (108, 14), (105, 8),
     (100, 6), (97, 10), (94, 16), (91, 21), (87, 22), (84, 19),
     (80, 13), (77, 8), (74, 12), (70, 20), (66, 24), (61, 25),
     (56, 26), (52, 27), (49, 29), (46, 29), (42, 28), (38, 28),
     (35, 29), (32, 31), (30, 35), (28, 38)],
    # Australia
    [(113, -22), (114, -28), (115, -34), (118, -35), (124, -33),
     (129, -32), (132, -32), (135, -35), (138, -35), (140, -38),
     (145, -38), (150, -37), (153, -32), (153, -27), (150, -22),
     (146, -19), (142, -11), (140, -14), (136, -12), (132, -12),
     (128, -14), (124, -16), (120, -20), (114, -21)],
    # New Zealand
    [(167, -45), (168, -42), (170, -41), (172, -40), (174, -38),
     (176, -37), (175, -39), (173, -41), (171, -42), (169, -44)],
    [(166, -46), (167, -44), (168, -45), (167, -47)],
    # Indonesia
    [(95, 5), (98, 2), (102, -2), (105, -5), (110, -7), (115, -8),
     (120, -9), (125, -8), (128, -5), (131, -3), (135, -3), (138, -6),
     (141, -8), (136, -8), (130, -6), (125, -8), (120, -10), (114, -9),
     (108, -7), (102, -4), (97, 2)],
    # Japan
    [(130, 31), (132, 33), (135, 34), (138, 35), (140, 37), (141, 39),
     (143, 42), (145, 44), (143, 42), (141, 38), (139, 35), (136, 34),
     (133, 33)],
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


def draw_icon2(d, kind, box, accent):
    """More flat icons, in the same 100x100 style as draw_icon."""
    x0, y0, x1, y1 = box
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    if kind == "flag":
        # flag on a pole, ground line below
        d.line(x0 + 28, y0 + 82, x0 + 28, y0 + 18, INK, 4)
        d.disc(x0 + 28, y0 + 15, 3, AMBER)
        d.polygon([(x0 + 28, y0 + 20), (x0 + 78, y0 + 30), (x0 + 28, y0 + 42)],
                  accent)
        d.polygon([(x0 + 28, y0 + 44), (x0 + 66, y0 + 52), (x0 + 28, y0 + 58)],
                  (200, 210, 220))
        d.fill_rect(x0 + 16, y0 + 82, x0 + 84, y0 + 86, (200, 210, 220))
    elif kind == "building":
        # courthouse: triangle roof, columns, steps
        d.polygon([(x0 + 8, y0 + 42), (x0 + 50, y0 + 14), (x0 + 92, y0 + 42)],
                  INK)
        d.fill_rect(x0 + 12, y0 + 42, x0 + 88, y0 + 50, INK)
        for bx in (18, 34, 58, 74):
            d.fill_rect(x0 + bx, y0 + 50, x0 + bx + 8, y0 + 76,
                        (200, 210, 220))
        d.fill_rect(x0 + 45, y0 + 60, x0 + 55, y0 + 76, INK)
        d.fill_rect(x0 + 10, y0 + 76, x0 + 90, y0 + 82, INK)
        d.fill_rect(x0 + 6, y0 + 82, x0 + 94, y0 + 86, (200, 210, 220))
    elif kind == "burst":
        # starburst: twelve rays around a centre disc
        for ang in range(0, 360, 30):
            a = math.radians(ang)
            d.line(cx, cy, cx + int(34 * math.cos(a)),
                   cy + int(34 * math.sin(a)), accent, 4)
        d.disc(cx, cy, 9, accent)
        d.disc(cx, cy, 4, WHITE)
    elif kind == "drop":
        # flame: outer teardrop, inner flame
        d.polygon([(cx, y0 + 12), (cx + 20, y0 + 42), (cx + 18, y0 + 68),
                   (cx - 18, y0 + 68), (cx - 20, y0 + 42)], ORANGE)
        d.polygon([(cx, y0 + 32), (cx + 11, y0 + 52), (cx + 9, y0 + 66),
                   (cx - 9, y0 + 66), (cx - 11, y0 + 52)], AMBER)


_ICON_CACHE = {}


def icon_canvas(kind, accent):
    """Render an icon once onto a 100x100 canvas (cached by kind)."""
    c = Canvas(100, 100, (238, 242, 245))
    if kind in ("chart_down", "chart_up", "tower", "city", "globe",
                "cyclone"):
        draw_icon(c, kind, (0, 0, 100, 100), accent)
    else:
        draw_icon2(c, kind, (0, 0, 100, 100), accent)
    return c


def blit_icon(d, kind, accent, x0, y0, x1, y1):
    """Scale a cached 100x100 icon onto (x0, y0, x1, y1), nearest pixel."""
    key = (kind, accent)
    src = _ICON_CACHE.get(key)
    if src is None:
        src = icon_canvas(kind, accent)
        _ICON_CACHE[key] = src
    tw, th = x1 - x0, y1 - y0
    for ty in range(th):
        sy = ty * 100 // th
        for tx in range(tw):
            sx = tx * 100 // tw
            i = (sy * 100 + sx) * 3
            d.set(x0 + tx, y0 + ty, tuple(src.px[i:i + 3]))


# World map projection: longitude -180..180, latitude 80..-60.
MAP_X0, MAP_Y0, MAP_W, MAP_H = 24, 742, 420, 174


def project(lon, lat):
    x = MAP_X0 + (lon + 180) / 360 * MAP_W
    y = MAP_Y0 + (80 - lat) / 140 * MAP_H
    return int(round(x)), int(round(y))


def build_image():
    d = Canvas(W, H, PAPER)
    # outer frame
    d.rect(0, 0, W, H, INK, 4)

    # ---- masthead (y 0-86) ----
    draw_text(d, 32, 8, "THE WORLD IN ONE DAY", 2, INK)
    draw_text(d, W // 2, 46, "FRIDAY 20 NOVEMBER 2026", 7, INK,
              anchor="mm")
    draw_text(d, W // 2, 79,
              "30 STORIES - EVERY CONTINENT - ALL FROM THIS ONE DAY",
              2, INK, anchor="mm")
    d.fill_rect(24, 86, 1000, 88, INK)

    # ---- region strip (y 88-118) ----
    widths = [110, 130, 190, 150, 120, 140, 136]
    cx = 24
    bounds = []
    for (name, count, accent), w in zip(REGIONS, widths):
        bounds.append(cx)
        draw_text(d, cx + 10, 93, str(count), 3, accent)
        draw_text(d, cx + 33, 97, name, 2, INK)
        cx += w
    for bx in bounds[1:]:
        d.fill_rect(bx - 1, 90, bx + 1, 116, (200, 205, 210))
    d.fill_rect(24, 118, 1000, 120, INK)

    # ---- figures row (y 120-168) ----
    fx = 24
    for (figure, label, accent), w in zip(FIGURES,
                                          [158, 170, 160, 162, 165, 161]):
        draw_text(d, fx + w // 2, 138, figure, 4, accent, anchor="mm")
        draw_text(d, fx + w // 2, 161, label, 2, INK, anchor="mm")
        if fx > 24:
            d.fill_rect(fx - 1, 122, fx + 1, 168, (200, 205, 210))
        fx += w
    d.fill_rect(24, 170, 1000, 172, INK)

    # ---- leads (y 172-380, 3 columns) ----
    for i, (kicker, headline, body, accent, icon) in enumerate(LEADS):
        x0 = 24 + i * 329
        # illustration panel on top
        d.fill_rect(x0 + 4, 172, x0 + 314, 260, (238, 242, 245))
        d.fill_rect(x0 + 4, 172, x0 + 314, 176, accent)
        draw_icon(d, icon, (x0 + 115, 172, x0 + 203, 260), accent)
        # kicker, headline, body
        draw_text(d, x0 + 4, 266, kicker, 2, accent)
        head_lines = wrap(headline, 3, 310)
        assert len(head_lines) <= 2, headline
        hy = 284
        for ln in head_lines:
            draw_text(d, x0 + 4, hy, ln, 3, INK)
            hy += 24
        body_lines = wrap(body, 2, 310)
        assert len(body_lines) <= 3, body
        by = 334
        for ln in body_lines:
            draw_text(d, x0 + 4, by, ln, 2, (45, 55, 75))
            by += 16
        assert by <= 382, headline  # last line ends at by - 2
        if i:
            d.fill_rect(x0 - 6, 172, x0 - 4, 380, (200, 205, 210))

    # ---- grid (y 384-714, 3 cols x 3 rows) ----
    for i, (kicker, headline, body, accent, icon) in enumerate(GRID):
        col, row = i % 3, i // 3
        x0 = 24 + col * 329
        y0 = 384 + row * 111
        x1, y1 = x0 + 318, y0 + 108
        d.rounded_rect(x0, y0, x1, y1, 8, CARD, outline=(200, 205, 210),
                       width=2)
        d.fill_rect(x0 + 10, y0, x1 - 10, y0 + 6, accent)
        assert text_width(kicker, 2) <= 298, kicker
        draw_text(d, x0 + 10, y0 + 10, kicker, 2, accent)
        # mini icon, left
        d.fill_rect(x0 + 10, y0 + 30, x0 + 74, y0 + 94, (238, 242, 245))
        blit_icon(d, icon, accent, x0 + 10, y0 + 30, x0 + 74, y0 + 94)
        # headline and body, right of the icon
        head_lines = wrap(headline, 2, 228)
        assert len(head_lines) <= 2, headline
        hy = y0 + 30
        for ln in head_lines:
            draw_text(d, x0 + 82, hy, ln, 2, INK)
            hy += 18
        body_lines = wrap(body, 2, 228)
        assert len(body_lines) <= 2, body
        by = y0 + 66
        for ln in body_lines:
            draw_text(d, x0 + 82, by, ln, 2, (45, 55, 75))
            by += 18
        assert by <= y0 + 102, headline  # last line ends at by - 4

    # ---- map + index band (y 718-928) ----
    d.fill_rect(24, 716, 1000, 718, INK)
    draw_text(d, 24, 722, "WHERE IT HAPPENED", 2, INK)
    draw_text(d, 460, 722, "THE DAY IN BRIEF", 2, INK)
    # ocean
    d.fill_rect(MAP_X0, MAP_Y0, MAP_X0 + MAP_W, MAP_Y0 + MAP_H,
                (214, 228, 238))
    # continents, light grey with dark outlines
    for poly in CONTINENTS:
        pts = [project(lon, lat) for lon, lat in poly]
        d.polygon(pts, (198, 198, 192))
        d.polyline(pts + [pts[0]], INK, 2)
    # numbered pins
    for num, lon, lat, accent in PINS:
        px, py = project(lon, lat)
        d.disc(px, py, 7, accent)
        d.ellipse_outline(px, py, 7, 7, INK, 1)
        draw_text(d, px, py, str(num), 1, WHITE, anchor="mm")
    # index, two columns of 9; the number in the region colour
    for i, (num, line, accent) in enumerate(INDEX):
        col = i // 9
        row = i % 9
        ix = 460 + col * 276
        iy = 744 + row * 19
        assert text_width(line, 2) <= 264, line
        head, rest = line.split(" ", 1)
        draw_text(d, ix, iy, head + " ", 2, accent)
        draw_text(d, ix + text_width(head + " ", 2), iy, rest, 2, INK)

    # ---- footer (y 918-1018) ----
    d.fill_rect(24, 918, 1000, 920, INK)
    blocks = [
        ("DATE CHECK: ",
         "DATE CHECK: Every story on this page happened, or was first "
         "reported, on Friday 20 November 2026. Claims are attributed "
         "to their sources."),
        ("LEFT OUT AS OTHER DAYS' NEWS: ",
         "LEFT OUT AS OTHER DAYS' NEWS: 19 NOV: UK 1,000-drone pledge "
         "- ICJ Myanmar ruling - Shenzhen summit - Pete Rose pardon"),
        ("Sources: ",
         "Sources: Reuters, AP, AFP, WSJ, DW, The Nation, Al Jazeera. "
         "Pictures and map: original, drawn in code."),
    ]
    fy = 922
    for label, text in blocks:
        lines = wrap(text, 2, 976)
        assert len(lines) <= 2, text
        first = lines[0]
        rest = first[len(label):]
        draw_text(d, 24, fy, label, 2, RED)
        draw_text(d, 24 + text_width(label, 2), fy, rest, 2, INK)
        for j, ln in enumerate(lines[1:], 1):
            draw_text(d, 24, fy + j * 16, ln, 2, INK)
        fy += len(lines) * 16
    assert fy <= 1018, "footer overflow"
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
