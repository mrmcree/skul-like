"""Extract the 3-row x 5-col katana VFX sheet (assets/raw/vfx/hero_slashes.png)
into spatially locked, 2x pixel-density strips in assets/vfx/:
  - slash_1.png (92x44 x 5, horizontal forward cut)
  - slash_2.png (68x84 x 5, upward rising slash)
  - slash_3.png (120x56 x 5, heavy horizontal piercing thrust)

Usage:
  python tools/process_vfx.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import pixel_tools as pt

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "assets" / "raw" / "vfx" / "hero_slashes.png"
OUT_DIR = ROOT / "assets" / "vfx"
PREVIEW_PATH = Path(
    r"C:\Users\123\.gemini\antigravity\brain\453c4ad9-7c9e-47c4-b2ac-552b2408ce48\scratch\vfx_preview.png"
)

MIN_COVERAGE = 0.25


def key_cyan_vfx(rgb: np.ndarray) -> Image.Image:
    """Remove solid cyan (#00FFFF) + pale cyan JPEG halo without eroding 1-2px sparks."""
    h, w = rgb.shape[:2]
    r = rgb[..., 0].astype(np.int32)
    g = rgb[..., 1].astype(np.int32)
    b = rgb[..., 2].astype(np.int32)
    bg = pt.cyan_background(rgb)
    cyan_tint = (g > r + 38) & (b > r + 38) & (b > 140)
    mask = ~(bg | cyan_tint)
    # Remove bottom-right watermark cleanly without clipping Row 2 Frame 4.
    mask[int(h * 0.91):, int(w * 0.85):] = False
    clean_rgb = pt.despill_edge(rgb, mask, "cyan", width=3)
    return pt.to_rgba(clean_rgb, mask)


def downscale_crisp(
    img: Image.Image,
    scale: float,
    palette: Image.Image,
    colors: int,
    min_cov: float = MIN_COVERAGE,
) -> Image.Image:
    """Mode-downscale preserving thin 1-2px pixel sparks and speed-lines."""
    index = np.array(img.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE))
    opaque = np.array(img.getchannel("A")) > 0
    out_w = max(1, round(img.width * scale))
    out_h = max(1, round(img.height * scale))
    xs = np.linspace(0, img.width, out_w + 1).astype(int)
    ys = np.linspace(0, img.height, out_h + 1).astype(int)
    lut = np.array(palette.getpalette()[: colors * 3], dtype=np.uint8).reshape(-1, 3)
    out = np.zeros((out_h, out_w, 4), dtype=np.uint8)
    for j in range(out_h):
        for i in range(out_w):
            block_alpha = opaque[ys[j]:ys[j + 1], xs[i]:xs[i + 1]]
            if block_alpha.size == 0 or block_alpha.mean() < min_cov:
                continue
            block = index[ys[j]:ys[j + 1], xs[i]:xs[i + 1]][block_alpha]
            out[j, i, :3] = lut[np.bincount(block, minlength=colors).argmax()]
            out[j, i, 3] = 255
    return Image.fromarray(out, "RGBA")


def find_row_frames(mask: np.ndarray, y0: int, y1: int) -> list[tuple[int, int, int, int]]:
    """Find the 5 horizontal frame bounding boxes inside row band [y0, y1)."""
    sub = mask[y0:y1]
    col_has = sub.any(axis=0)
    bridged = ndimage.binary_dilation(col_has, iterations=18)
    labels, count = ndimage.label(bridged)
    boxes = []
    for idx in range(1, count + 1):
        xs = np.nonzero((labels == idx) & col_has)[0]
        if len(xs) == 0:
            continue
        x0, x1 = int(xs[0]), int(xs[-1]) + 1
        ys = np.nonzero(sub[:, x0:x1].any(axis=1))[0]
        boxes.append((x0, y0 + int(ys[0]), x1, y0 + int(ys[-1]) + 1))
    if len(boxes) != 5:
        raise ValueError(f"Row {y0}..{y1}: expected 5 frames, found {len(boxes)}: {boxes}")
    return boxes


def ring_center_x(mask: np.ndarray, box: tuple[int, int, int, int]) -> float:
    """Locate the shockwave ring X center in Row 2 from tall vertical-span columns."""
    x0, y0, x1, y1 = box
    sub = mask[y0:y1, x0:x1]
    tall_cols = []
    for c in range(sub.shape[1]):
        ys = np.nonzero(sub[:, c])[0]
        if len(ys) and (ys[-1] - ys[0]) >= 34:
            tall_cols.append(x0 + c)
    if tall_cols:
        return float(np.mean(tall_cols))
    return float(x0 + 25)


def pack_row(
    rgba_img: Image.Image,
    mask: np.ndarray,
    boxes: list[tuple[int, int, int, int]],
    scale: float,
    frame_size: tuple[int, int],
    palette: Image.Image,
    colors: int,
    anchor_mode: str,
    params: dict,
) -> Image.Image:
    fw, fh = frame_size
    strip = Image.new("RGBA", (fw * 5, fh), (0, 0, 0, 0))
    for i, box in enumerate(boxes):
        x0, y0, x1, y1 = box
        crop = rgba_img.crop((x0, y0, x1, y1))
        piece = downscale_crisp(crop, scale, palette, colors)

        if anchor_mode == "slash_1":
            px = params["x_max_targets"][i] - piece.width
            py = round(params["y_out"] + (y0 - params["y_ref"]) * scale)
        elif anchor_mode == "slash_2":
            px = params["x_max_targets"][i] - piece.width
            py = round(params["y_out"] + (y0 - params["y_ref_top"]) * scale)
        elif anchor_mode == "slash_3":
            rcx = ring_center_x(mask, box)
            px = round(params["ring_out_x"] - (rcx - x0) * scale)
            py = round(params["y_out"] + (y0 - params["y_ref"]) * scale)
        else:
            raise ValueError(anchor_mode)

        px = max(0, min(fw - piece.width, px))
        py = max(0, min(fh - piece.height, py))
        strip.alpha_composite(piece, (i * fw + px, py))
    return strip


def save_preview(strips: dict[str, tuple[Image.Image, tuple[int, int], tuple[int, int]]]) -> None:
    PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    w = max(s[0].width for s in strips.values())
    h = sum(s[0].height + 8 for s in strips.values())
    canvas = Image.new("RGBA", (w, h), (30, 26, 40, 255))
    draw = ImageDraw.Draw(canvas)
    y = 0
    for name, (strip, (fw, fh), (piv_x, piv_y)) in strips.items():
        canvas.alpha_composite(strip, (0, y))
        for i in range(5):
            cx, cy = i * fw + piv_x, y + piv_y
            draw.line([(cx - 3, cy), (cx + 3, cy)], fill=(80, 255, 180, 220))
            draw.line([(cx, cy - 3), (cx, cy + 3)], fill=(80, 255, 180, 220))
            draw.rectangle([(i * fw, y), ((i + 1) * fw - 1, y + fh - 1)], outline=(70, 65, 90, 160))
        y += fh + 8
    canvas.resize((w * 2, h * 2), Image.Resampling.NEAREST).save(PREVIEW_PATH)


def main() -> None:
    rgb = np.array(Image.open(RAW_PATH).convert("RGB"))
    rgba_img = key_cyan_vfx(rgb)
    mask = np.array(rgba_img.getchannel("A")) > 0
    h = rgb.shape[0]
    row_bands = [(0, h // 3), (h // 3, (2 * h) // 3), ((2 * h) // 3, h)]
    all_boxes = [find_row_frames(mask, y0, y1) for y0, y1 in row_bands]

    # Build one shared 24-color palette across all 15 frames
    crops = [rgba_img.crop(box) for boxes in all_boxes for box in boxes]
    colors = 24
    palette = pt.make_palette(crops, colors)

    specs = [
        (
            "slash_1",
            all_boxes[0],
            0.60,
            (92, 44),
            (20, 22),
            "slash_1",
            {"x_max_targets": [76, 88, 84, 86, 82], "y_ref": 74.5, "y_out": 22},
        ),
        (
            "slash_2",
            all_boxes[1],
            0.64,
            (68, 84),
            (18, 48),
            "slash_2",
            {"x_max_targets": [58, 62, 60, 62, 56], "y_ref_top": 166.0, "y_out": 4},
        ),
        (
            "slash_3",
            all_boxes[2],
            0.60,
            (120, 56),
            (18, 28),
            "slash_3",
            {"ring_out_x": 30, "y_ref": 387.5, "y_out": 28},
        ),
    ]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    preview_data = {}
    for name, boxes, scale, fsize, pivot, mode, params in specs:
        strip = pack_row(rgba_img, mask, boxes, scale, fsize, palette, colors, mode, params)
        strip.save(OUT_DIR / f"{name}.png")
        preview_data[name] = (strip, fsize, pivot)
        print(f"wrote {name}.png: {strip.size} (5 x {fsize})")

    save_preview(preview_data)
    print(f"wrote preview: {PREVIEW_PATH}")


if __name__ == "__main__":
    main()
