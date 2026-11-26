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
    }
    for name, img in images.items():
        img.save(OUT / f"{name}.png")
        print(f"{name:12s} {img.size}")
    sheet = Image.new("RGBA", (sum(i.width + 3 for i in images.values()) + 2, 30), (0, 0, 0, 0))
    x = 2
    for img in images.values():
        sheet.alpha_composite(img, (x, 2))
        x += img.width + 3
    pt.preview(sheet, 4).save(PREVIEW)
    print(f"preview: {PREVIEW}")


if __name__ == "__main__":
    main()
