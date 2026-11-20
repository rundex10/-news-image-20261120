#!/usr/bin/env python3
"""Sum up 20 November 2026 world news in one image.

Draws a 1024x1024 editorial infographic with Pillow only: no network,
no randomness, no clock, no timestamps in the PNG. Running it twice
writes byte-identical files.

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

import os
import sys
from PIL import Image, ImageDraw, ImageFont

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

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


F_SERIF_B = lambda s: font("DejaVuSerif-Bold.ttf", s)      # noqa: E731
F_SANS_B = lambda s: font("DejaVuSans-Bold.ttf", s)        # noqa: E731
F_SANS = lambda s: font("DejaVuSans.ttf", s)               # noqa: E731


# (kicker, headline, body, accent, icon)
STORIES = [
    (
        "ASIA  •  MARKETS",
        "Asia markets plunge on AI fears",
        "Nikkei fell 4.8%, Kospi over 5% and Taiwan's Taiex 6.4% on Friday as AI valuations rattled investors.",
        RED, "chart_down",
    ),
    (
        "UNITED STATES  •  TECH",
        "Anthropic debuts in record IPO",
        "Shares opened at $111.50, above the $83 price, and closed up 17% at $97.17 in the largest IPO on record.",
        GREEN, "chart_up",
    ),
    (
        "MIDDLE EAST  •  SAUDI ARABIA",
        "Missile hits Riyadh's tallest tower",
        "A Houthi missile damaged the 80-storey PIF Tower, blowing out windows on seven floors. No injuries reported.",
        ORANGE, "tower",
    ),
    (
        "EUROPE  •  UKRAINE",
        "Strikes damage Kyiv embassies",
        "Russian strikes hit the Austrian and Dutch embassies in Kyiv on Thursday, killing one person. The EU will summon Russia's envoy.",
        PURPLE, "city",
    ),
    (
        "CLIMATE  •  COP31, ANTALYA",
        "COP31 draft drops fossil fuels",
        "On its final day, the draft deal had no mention of coal, oil or gas. Africa seeks $120bn a year in adaptation finance.",
        TEAL, "globe",
    ),
    (
        "ASIA  •  WEATHER",
        "Cyclone Akvan hits India's coast",
        "Akvan crossed the Odisha-Andhra Pradesh coast on Friday morning, with winds of 70-80 km/h, gusting to 90.",
        (11, 94, 124), "cyclone",
    ),
]


def wrap(draw, text, fnt, max_w):
    """Wrap text to lines that fit max_w pixels; assert nothing is lost."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_icon(d, kind, box, accent):
    """Flat vector-style icon in box (x0, y0, x1, y1). Simple shapes only."""
    x0, y0, x1, y1 = box
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    if kind == "chart_down":
        # axes + falling line with arrow
        d.line([(x0 + 14, y1 - 18), (x1 - 12, y1 - 18)], fill=INK, width=4)
        d.line([(x0 + 14, y1 - 18), (x0 + 14, y0 + 14)], fill=INK, width=4)
        pts = [(x0 + 20, y0 + 26), (x0 + 38, y0 + 44), (x0 + 54, y0 + 38),
               (x0 + 72, y0 + 62), (x0 + 90, y0 + 78)]
        d.line(pts, fill=accent, width=6, joint="curve")
        d.polygon([(x0 + 90, y0 + 78), (x0 + 74, y0 + 74), (x0 + 88, y0 + 60)],
                  fill=accent)
        for bx, bh in [(24, 18), (44, 30), (64, 22)]:
            d.rectangle([x0 + bx, y1 - 18 - bh, x0 + bx + 12, y1 - 18],
                        fill=(200, 210, 220))
    elif kind == "chart_up":
        d.line([(x0 + 14, y1 - 18), (x1 - 12, y1 - 18)], fill=INK, width=4)
        d.line([(x0 + 14, y1 - 18), (x0 + 14, y0 + 14)], fill=INK, width=4)
        pts = [(x0 + 20, y0 + 78), (x0 + 38, y0 + 62), (x0 + 54, y0 + 66),
               (x0 + 72, y0 + 42), (x0 + 90, y0 + 24)]
        d.line(pts, fill=accent, width=6, joint="curve")
        d.polygon([(x0 + 90, y0 + 24), (x0 + 74, y0 + 28), (x0 + 88, y0 + 42)],
                  fill=accent)
        d.ellipse([cx - 34, cy - 8, cx + 34, cy + 8], outline=accent, width=3)
        d.text((cx, cy - 2), "ANT", font=F_SANS_B(13), fill=accent, anchor="mm")
    elif kind == "tower":
        # tall skyscraper, damaged band, missile streak
        d.rectangle([cx - 22, y0 + 18, cx + 22, y1 - 14], fill=INK)
        for wy in range(y0 + 28, y1 - 22, 14):
            d.rectangle([cx - 15, wy, cx - 4, wy + 7], fill=(150, 180, 210))
            d.rectangle([cx + 4, wy, cx + 15, wy + 7], fill=(150, 180, 210))
        d.rectangle([cx - 22, y0 + 52, cx + 22, y0 + 72], fill=accent)
        d.line([(x0 + 6, y0 + 8), (cx - 10, y0 + 52)], fill=accent, width=5)
        d.polygon([(cx - 10, y0 + 52), (cx - 24, y0 + 46), (cx - 16, y0 + 60)],
                  fill=accent)
        d.rectangle([x0 + 12, y1 - 14, x1 - 12, y1 - 8], fill=(200, 210, 220))
    elif kind == "city":
        # skyline, flag on the tallest building, burst in the sky corner
        for bx, bw, bh in [(12, 22, 52), (38, 26, 70), (68, 22, 46)]:
            d.rectangle([x0 + bx, y1 - 14 - bh, x0 + bx + bw, y1 - 14],
                        fill=INK)
            d.rectangle([x0 + bx + 6, y1 - 14 - bh + 8, x0 + bx + 14,
                         y1 - 14 - bh + 16], fill=AMBER)
        # flag on the tallest (middle) building
        fx = x0 + 51
        d.line([(fx, y1 - 84), (fx, y1 - 106)], fill=INK, width=3)
        d.polygon([(fx, y1 - 106), (fx + 22, y1 - 100), (fx, y1 - 94)],
                  fill=accent)
        # burst, top-right corner, clear of the flag
        bx, by = x1 - 24, y0 + 26
        for ang in range(0, 360, 45):
            import math
            a = math.radians(ang)
            d.line([(bx, by),
                    (bx + int(13 * math.cos(a)), by + int(13 * math.sin(a)))],
                   fill=ORANGE, width=3)
        d.ellipse([bx - 6, by - 6, bx + 6, by + 6], fill=ORANGE)
    elif kind == "globe":
        d.ellipse([cx - 38, y0 + 12, cx + 38, y0 + 88], outline=accent, width=5)
        d.arc([cx - 38, y0 + 12, cx + 38, y0 + 88], 20, 160, fill=accent, width=3)
        d.arc([cx - 38, y0 + 12, cx + 38, y0 + 88], 200, 340, fill=accent, width=3)
        d.line([(cx - 38, y0 + 50), (cx + 38, y0 + 50)], fill=accent, width=3)
        # sprout growing from the globe's base: stem + two leaves
        d.line([(cx, y0 + 88), (cx, y0 + 66)], fill=GREEN, width=4)
        d.ellipse([cx - 22, y0 + 66, cx - 2, y0 + 80], fill=GREEN)
        d.ellipse([cx + 2, y0 + 60, cx + 22, y0 + 74], fill=GREEN)
        # crossed-out fuel drop, top-left, clear of the globe
        d.polygon([(x0 + 14, y0 + 32), (x0 + 24, y0 + 14), (x0 + 34, y0 + 32)],
                  fill=(160, 175, 195))
        d.line([(x0 + 10, y0 + 10), (x0 + 38, y0 + 38)], fill=RED, width=4)
    elif kind == "cyclone":
        # spiral + rain
        for r in (34, 24, 14):
            d.arc([cx - r, cy - 14 - r, cx + r, cy - 14 + r], 30, 300,
                  fill=accent, width=5)
        d.ellipse([cx - 5, cy - 19, cx + 5, cy - 9], fill=accent)
        for rx in (x0 + 18, x0 + 42, x0 + 66, x0 + 88):
            d.line([(rx, y1 - 28), (rx - 4, y1 - 14)], fill=TEAL, width=4)
        d.rectangle([x0 + 10, y1 - 12, x1 - 10, y1 - 6], fill=(200, 210, 220))


def build_image():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    # outer frame
    d.rectangle([0, 0, W - 1, H - 1], outline=INK, width=6)

    # ---- header (navy band) ----
    d.rectangle([6, 6, W - 7, 150], fill=NAVY)
    d.text((36, 26), "FRIDAY  •  20 NOVEMBER 2026", font=F_SANS_B(34),
           fill=AMBER)
    d.text((36, 76), "THE WORLD IN ONE DAY", font=F_SERIF_B(46), fill=WHITE)
    # "6 stories" badge, right side of header
    d.rounded_rectangle([856, 34, 988, 116], radius=10,
                        outline=AMBER, width=3)
    d.text((922, 56), "6", font=F_SERIF_B(44), fill=WHITE, anchor="mm")
    d.text((922, 96), "STORIES", font=F_SANS_B(16), fill=AMBER, anchor="mm")

    # ---- subheader strip ----
    d.rectangle([6, 150, W - 7, 188], fill=(232, 222, 196))
    d.text((36, 160), "Six stories, reported on 20 November 2026 — markets, AI, war, climate and weather.",
           font=F_SANS(19), fill=INK)

    # ---- grid: 2 cols x 3 rows ----
    gx, gy = 24, 204
    gw, gh, gap = 476, 232, 16
    for i, (kicker, headline, body, accent, icon) in enumerate(STORIES):
        col, row = i % 2, i // 2
        x0 = gx + col * (gw + gap)
        y0 = gy + row * (gh + gap)
        x1, y1 = x0 + gw, y0 + gh
        # card
        d.rounded_rectangle([x0, y0, x1, y1], radius=10, fill=CARD,
                            outline=(200, 205, 210), width=2)
        d.rectangle([x0 + 10, y0, x1 - 10, y0 + 7], fill=accent)
        # icon panel (left)
        ix0, iy0, ix1, iy1 = x0 + 14, y0 + 22, x0 + 128, y1 - 14
        d.rounded_rectangle([ix0, iy0, ix1, iy1], radius=8,
                            fill=(238, 242, 245))
        draw_icon(d, icon, (ix0, iy0, ix1, iy1), accent)
        # text (right of icon)
        tx = x0 + 142
        tw = x1 - tx - 16
        d.text((tx, y0 + 22), kicker, font=F_SANS_B(15), fill=accent)
        head_lines = wrap(d, headline, F_SANS_B(26), tw)
        assert len(head_lines) <= 2, headline
        hy = y0 + 48
        for ln in head_lines:
            d.text((tx, hy), ln, font=F_SANS_B(26), fill=INK)
            hy += 32
        body_lines = wrap(d, body, F_SANS(19), tw)
        assert len(body_lines) <= 4, body
        by = hy + 8
        for ln in body_lines:
            d.text((tx, by), ln, font=F_SANS(19), fill=(45, 55, 75))
            by += 25
        assert by <= y1 - 8, headline

    # ---- footer (navy strip) ----
    d.rectangle([6, 936, W - 7, H - 7], fill=NAVY)
    d.text((36, 950), "Sources: Reuters, WSJ, Morningstar, India Meteorological Department.",
           font=F_SANS_B(18), fill=WHITE)
    d.text((36, 978), "All six stories happened or were first reported on 20 November 2026, in some time zone.",
           font=F_SANS(18), fill=(200, 210, 225))
    return img


def main(argv):
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    if "--output" in argv:
        out_dir = argv[argv.index("--output") + 1]
    os.makedirs(out_dir, exist_ok=True)
    img = build_image()
    path = os.path.join(out_dir, "entry.png")
    # PIL writes no timestamp chunk by default; deterministic output.
    img.save(path, format="PNG", optimize=True)
    print("wrote %s (%dx%d)" % (path, W, H))


if __name__ == "__main__":
    main(sys.argv[1:])
