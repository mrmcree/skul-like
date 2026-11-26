"""Generate the HUD's pixel-art pieces (style taken from assets/raw/forest/0_mood.png).

Usage (from the project root):
    python tools/gen_ui.py

Writes assets/ui/:
  portrait.png              — cropped from the mood image and snapped to game resolution
  heart_full/half/empty.png — 11x10 hearts with black outline
  bar_frame.png             — 64x7 beige-framed bar (fill is drawn by the game)
  coin.png                  — 9x9 gold coin
  digits.png                — 0-9, 7x9 each, white with black outline
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

import pixel_tools as pt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "ui"
MOOD = ROOT / "assets" / "raw" / "forest" / "0_mood.png"
PREVIEW = ROOT / "assets" / "raw" / "ui_preview.png"
PORTRAIT_BOX = (48, 32, 135, 118)   # frame + face in the mood image (source px)
PORTRAIT_SIZE = (26, 26)

OUTLINE = (20, 10, 16, 255)
CLEAR = (0, 0, 0, 0)

HEART = [
    ".OOO...OOO.",
    "OrrrO.OrrrO",
    "OrwrrOrrrrO",
    "OrwrrrrrrrO",
    "OrrrrrrrrdO",
    ".OrrrrrrdO.",
    "..OrrrrdO..",
    "...OrrdO...",
    "....OdO....",
    ".....O.....",
]
HEART_COLORS = {"O": OUTLINE, "r": (214, 44, 44, 255), "d": (150, 22, 34, 255), "w": (255, 178, 160, 255)}
EMPTY_COLORS = {"O": OUTLINE, "r": (58, 40, 52, 255), "d": (44, 30, 40, 255), "w": (80, 60, 72, 255)}

COIN = [
    "..OOOOO..",
    ".OgggggO.",
    "OggdddgwO",
    "OgdggwdgO",
    "OgdgggdgO",
    "OgdggddgO",
    "OggdddggO",
    ".OgggggO.",
    "..OOOOO..",
]
COIN_COLORS = {"O": OUTLINE, "g": (226, 172, 64, 255), "d": (158, 104, 40, 255), "w": (255, 236, 170, 255)}

# 5x7 digit glyphs ("#" = ink)
DIGITS = {
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": [".###.", "#...#", "....#", "..##.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
}
DIGIT_INK = (242, 232, 226, 255)

BAR_W, BAR_H = 64, 7
BAR_BEIGE = (232, 218, 172, 255)
BAR_INNER = (34, 32, 30, 255)

# Shrine UI palette
WOOD_MID = (68, 42, 46, 255)
WOOD_HI = (106, 68, 62, 255)
WOOD_LO = (42, 24, 30, 255)
PLUM_BG = (28, 24, 38, 248)
PLUM_BAND = (24, 20, 33, 248)
GOLD_MID = (226, 172, 64, 255)
GOLD_HI = (255, 236, 170, 255)
GOLD_LO = (158, 104, 40, 255)
VERM_MID = (198, 54, 48, 255)
VERM_HI = (242, 118, 92, 255)
VERM_LO = (136, 28, 36, 255)
BTN_NORM_BG = (46, 36, 54, 255)
BTN_NORM_HI = (72, 58, 82, 255)
BTN_NORM_LO = (30, 22, 36, 255)
BTN_NORM_RIM = (168, 152, 128, 255)
BTN_HOV_BG = (142, 40, 44, 255)
BTN_HOV_HI = (182, 62, 58, 255)
BTN_HOV_LO = (96, 24, 30, 255)
BTN_PRESS_BG = (96, 26, 32, 255)
SLATE_OFF = (92, 88, 108, 255)
SLATE_HI = (138, 134, 158, 255)


def _notch_corners(img: Image.Image) -> None:
    w, h = img.size
    for c in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        img.putpixel(c, CLEAR)


def _draw_grid(rows: list[str], palette: dict[str, tuple[int, int, int, int]],
               base: Image.Image | None = None, ox: int = 0, oy: int = 0) -> Image.Image:
    out = base if base is not None else Image.new("RGBA", (len(rows[0]), len(rows)), CLEAR)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in palette:
                out.putpixel((ox + x, oy + y), palette[ch])
    return out


def btn_settings(hover: bool) -> Image.Image:
    w, h = 15, 15
    img = Image.new("RGBA", (w, h), OUTLINE)
    rim = GOLD_HI if hover else BAR_BEIGE
    fill = BTN_HOV_BG if hover else (36, 30, 46, 240)
    top_hi = BTN_HOV_HI if hover else (56, 46, 68, 240)
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            is_edge = x in (1, w - 2) or y in (1, h - 2)
            img.putpixel((x, y), rim if is_edge else (top_hi if y == 2 else fill))
    _notch_corners(img)
    for c in [(1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)]:
        img.putpixel(c, OUTLINE)
    gear = [
        "...g.g...",
        ".g.GGG.g.",
        "..GGGGG..",
        "gGG.O.GGg",
        ".GG.O.GG.",
        "gGG.O.GGg",
        "..GGGGG..",
        ".g.GGG.g.",
        "...g.g...",
    ]
    pal = {
        "G": GOLD_HI if hover else GOLD_MID,
        "g": GOLD_MID if hover else BAR_BEIGE,
        "O": OUTLINE,
    }
    return _draw_grid(gear, pal, img, 3, 3)


def panel_frame() -> Image.Image:
    w, h = 48, 48
    img = Image.new("RGBA", (w, h), OUTLINE)
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            d = min(x, y, w - 1 - x, h - 1 - y)
            if d == 1:
                c = WOOD_HI if y == 1 or x == 1 else WOOD_LO
            elif d in (2, 3):
                c = WOOD_MID
            elif d == 4:
                c = OUTLINE
            elif d == 5:
                c = BAR_BEIGE
            elif d == 6:
                c = OUTLINE
            else:
                c = PLUM_BAND if (y % 4 == 0) else PLUM_BG
            img.putpixel((x, y), c)
    _notch_corners(img)
    for c in [(1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)]:
        img.putpixel(c, OUTLINE)
    # Ornate gilded corner fittings (5x5 inside corners)
    corner_tl = [
        "OHHH.",
        "HGGGO",
        "HGOG.",
        "HGO..",
        ".O...",
    ]
    pal = {"O": OUTLINE, "H": GOLD_HI, "G": GOLD_MID}
    _draw_grid(corner_tl, pal, img, 1, 1)
    _draw_grid([r[::-1] for r in corner_tl], pal, img, w - 6, 1)
    _draw_grid(corner_tl[::-1], pal, img, 1, h - 6)
    _draw_grid([r[::-1] for r in corner_tl[::-1]], pal, img, w - 6, h - 6)
    return img


def plaque_button(bg: tuple[int, int, int, int], hi: tuple[int, int, int, int],
                  lo: tuple[int, int, int, int], rim: tuple[int, int, int, int],
                  studs: bool = False) -> Image.Image:
    w, h = 24, 20
    img = Image.new("RGBA", (w, h), OUTLINE)
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if x in (1, w - 2) or y in (1, h - 2):
                c = rim
            elif y == 2:
                c = hi
            elif y == h - 3:
                c = lo
            else:
                c = bg
            img.putpixel((x, y), c)
    _notch_corners(img)
    for c in [(1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)]:
        img.putpixel(c, OUTLINE)
    if studs:
        for sx, sy in [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]:
            img.putpixel((sx, sy), GOLD_HI)
    return img


def slider_track() -> Image.Image:
    w, h = 24, 9
    img = Image.new("RGBA", (w, h), OUTLINE)
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            is_edge = x in (1, w - 2) or y in (1, h - 2)
            img.putpixel((x, y), BAR_BEIGE if is_edge else BAR_INNER)
    _notch_corners(img)
    for c in [(1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)]:
        img.putpixel(c, OUTLINE)
    return img


def slider_fill(hi_col: tuple[int, int, int, int], mid_col: tuple[int, int, int, int],
                lo_col: tuple[int, int, int, int]) -> Image.Image:
    w, h = 16, 9
    img = Image.new("RGBA", (w, h), CLEAR)
    for y in range(2, h - 2):
        for x in range(2, w - 2):
            c = hi_col if y == 2 else (lo_col if y == h - 3 else mid_col)
            img.putpixel((x, y), c)
    return img


def slider_grabber(highlight: bool) -> Image.Image:
    rows = [
        "..OOOOO..",
        ".OHHHHHO.",
        "OHGGGGGOO",
        "OHGHHHGGO",
        "OGGHHHGG.",
        "OGGHHHGG.",
        "OGGHHHGG.",
        "OGGHHHGG.",
        "OGGHHHGG.",
        "OGGGGGGG.",
        "OLGGGGGLO",
        ".OLLLLLO.",
        "..OOOOO..",
    ]
    rows[4] = "OGGHHHGGD"
    for r in range(4, 10):
        rows[r] = "OGGHHHGGD" if r < 9 else "OGGGGGGGD"
    rows[2] = "OHGGGGGGD"
    rows[3] = "OHGHHHGGD"
    pal = {
        "O": OUTLINE,
        "H": GOLD_HI,
        "G": GOLD_HI if highlight else GOLD_MID,
        "L": GOLD_MID if highlight else GOLD_LO,
        "D": GOLD_MID if highlight else WOOD_LO,
    }
    return _draw_grid(rows, pal)


def divider() -> Image.Image:
    w, h = 96, 5
    img = Image.new("RGBA", (w, h), CLEAR)
    for x in range(4, w - 4):
        img.putpixel((x, 2), (232, 218, 172, 150))
    knot = [
        "..O..",
        ".OGO.",
        "OGHGO",
        ".OGO.",
        "..O..",
    ]
    _draw_grid(knot, {"O": OUTLINE, "G": VERM_MID, "H": GOLD_HI}, img, w // 2 - 2, 0)
    return img


def gem(lit: bool) -> Image.Image:
    rows = [
        "..OOO..",
        ".OHHGO.",
        "OHGGGG.",
        "OGGGGGO",
        ".OGGDO.",
        "..OOO..",
        ".......",
    ]
    rows[2] = "OHGGGGO"
    pal = {
        "O": OUTLINE,
        "H": GOLD_HI if lit else SLATE_HI,
        "G": GOLD_MID if lit else SLATE_OFF,
        "D": GOLD_LO if lit else WOOD_LO,
    }
    return _draw_grid(rows[:6], pal)


def draw(rows: list[str], colors: dict[str, tuple[int, int, int, int]]) -> Image.Image:
    img = Image.new("RGBA", (len(rows[0]), len(rows)), CLEAR)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in colors:
                img.putpixel((x, y), colors[ch])
    return img


def half_heart() -> Image.Image:
    full, empty = draw(HEART, HEART_COLORS), draw(HEART, EMPTY_COLORS)
    out = empty.copy()
    half = full.width // 2 + 1
    out.paste(full.crop((0, 0, half, full.height)), (0, 0))
    return out


def bar_frame() -> Image.Image:
    img = Image.new("RGBA", (BAR_W, BAR_H), OUTLINE)
    img.paste(Image.new("RGBA", (BAR_W - 2, BAR_H - 2), BAR_BEIGE), (1, 1))
    img.paste(Image.new("RGBA", (BAR_W - 4, BAR_H - 4), BAR_INNER), (2, 2))
    for corner in [(0, 0), (BAR_W - 1, 0), (0, BAR_H - 1), (BAR_W - 1, BAR_H - 1)]:
        img.putpixel(corner, CLEAR)
    return img


def digits_strip() -> Image.Image:
    """Each glyph gets a 1px outline, so every cell is 7x9."""
    strip = Image.new("RGBA", (7 * 10, 9), CLEAR)
    for i in range(10):
        glyph = draw(DIGITS[str(i)], {"#": DIGIT_INK})
        strip.paste(pt.add_outline(glyph, OUTLINE), (i * 7, 0))
    return strip


def portrait() -> Image.Image:
    crop = Image.open(MOOD).convert("RGBA").crop(PORTRAIT_BOX)
    palette = pt.make_palette([crop], 24)
    return pt.mode_downscale(crop, 0, palette, 24, size=PORTRAIT_SIZE)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    images = {
        "portrait": portrait(),
        "heart_full": draw(HEART, HEART_COLORS),
        "heart_half": half_heart(),
        "heart_empty": draw(HEART, EMPTY_COLORS),
        "bar_frame": bar_frame(),
        "coin": draw(COIN, COIN_COLORS),
        "digits": digits_strip(),
        "btn_settings": btn_settings(False),
        "btn_settings_hover": btn_settings(True),
        "panel_frame": panel_frame(),
        "btn_normal": plaque_button(BTN_NORM_BG, BTN_NORM_HI, BTN_NORM_LO, BTN_NORM_RIM, False),
        "btn_hover": plaque_button(BTN_HOV_BG, BTN_HOV_HI, BTN_HOV_LO, GOLD_HI, True),
        "btn_pressed": plaque_button(BTN_PRESS_BG, BTN_HOV_LO, WOOD_LO, GOLD_MID, True),
        "slider_track": slider_track(),
        "slider_fill": slider_fill(VERM_HI, VERM_MID, VERM_LO),
        "slider_fill_hi": slider_fill(GOLD_HI, GOLD_MID, GOLD_LO),
        "slider_grabber": slider_grabber(False),
        "slider_grabber_hi": slider_grabber(True),
        "divider": divider(),
        "gem_on": gem(True),
        "gem_off": gem(False),
    }
    for name, img in images.items():
        img.save(OUT / f"{name}.png")
        print(f"{name:18s} {img.size}")
    sheet_h = max(i.height for i in images.values()) + 4
    sheet = Image.new("RGBA", (sum(i.width + 3 for i in images.values()) + 2, sheet_h), (0, 0, 0, 0))
    x = 2
    for img in images.values():
        sheet.alpha_composite(img, (x, 2))
        x += img.width + 3
    pt.preview(sheet, 4).save(PREVIEW)
    print(f"preview: {PREVIEW}")


if __name__ == "__main__":
    main()
