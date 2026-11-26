"""Shared helpers for turning AI-generated 'pixel-style' images into real low-res pixel art."""

from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage

MIN_COVERAGE = 0.45   # an output pixel is opaque if this share of its source block is


def hue_saturation_value(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-pixel HSV, each 0..1."""
    arr = rgb.astype(np.float32) / 255.0
    mx, mn = arr.max(axis=-1), arr.min(axis=-1)
    delta = np.where(mx - mn == 0, 1e-6, mx - mn)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    hue = np.select(
        [mx == r, mx == g],
        [((g - b) / delta) % 6, (b - r) / delta + 2],
        (r - g) / delta + 4,
    ) / 6.0
    saturation = np.where(mx == 0, 0, (mx - mn) / np.where(mx == 0, 1, mx))
    return hue, saturation, mx


def magenta_background(rgb: np.ndarray) -> np.ndarray:
    """Bright, saturated magenta/pink backdrop (darker pinks like mushroom caps survive)."""
    hue, sat, val = hue_saturation_value(rgb)
    return (hue > 0.78) & (hue < 0.97) & (sat > 0.45) & (val > 0.72)


def green_background(rgb: np.ndarray) -> np.ndarray:
    r, g, b = (rgb[..., i].astype(np.int32) for i in range(3))
    return (g > 90) & (g * 4 > r * 5) & (g * 4 > b * 5)


def cyan_background(rgb: np.ndarray) -> np.ndarray:
    """Bright, saturated cyan (#00FFFF) backdrop."""
    hue, sat, val = hue_saturation_value(rgb)
    return (hue > 0.43) & (hue < 0.58) & (sat > 0.45) & (val > 0.65)


def erase_corner(mask: np.ndarray, width_frac: float = 0.15, height_frac: float = 0.1) -> np.ndarray:
    """Clear the bottom-right corner of a foreground mask (AI watermark)."""
    out = mask.copy()
    h, w = out.shape
    out[int(h * (1 - height_frac)):, int(w * (1 - width_frac)):] = False
    return out


def despill(rgb: np.ndarray, key: str) -> np.ndarray:
    """Pull the key colour out of anti-aliased edge pixels."""
    out = rgb.astype(np.int32).copy()
    if key == "green":
        out[..., 1] = np.minimum(out[..., 1], np.maximum(out[..., 0], out[..., 2]))
    elif key == "magenta":
        limit = out[..., 1] + 40
        out[..., 0] = np.minimum(out[..., 0], np.maximum(limit, out[..., 2] // 2 + out[..., 1] // 2))
        out[..., 2] = np.minimum(out[..., 2], np.maximum(limit, out[..., 0] // 2 + out[..., 1] // 2))
    return out.clip(0, 255).astype(np.uint8)


def despill_edge(rgb: np.ndarray, mask: np.ndarray, key: str, width: int = 4) -> np.ndarray:
    """Pull the key colour out of boundary pixels only, leaving interior colours intact."""
    edge = mask & ~ndimage.binary_erosion(mask, iterations=width)
    if not edge.any():
        return rgb.copy()
    out = rgb.astype(np.int32).copy()
    if key == "cyan":
        limit = out[..., 0] + 35
        out[..., 1] = np.where(edge, np.minimum(out[..., 1], limit), out[..., 1])
        out[..., 2] = np.where(edge, np.minimum(out[..., 2], limit), out[..., 2])
    elif key == "green":
        clamped = np.minimum(out[..., 1], np.maximum(out[..., 0], out[..., 2]))
        out[..., 1] = np.where(edge, clamped, out[..., 1])
    elif key == "magenta":
        limit = out[..., 1] + 40
        r_clamped = np.minimum(out[..., 0], np.maximum(limit, out[..., 2] // 2 + out[..., 1] // 2))
        b_clamped = np.minimum(out[..., 2], np.maximum(limit, out[..., 0] // 2 + out[..., 1] // 2))
        out[..., 0] = np.where(edge, r_clamped, out[..., 0])
        out[..., 2] = np.where(edge, b_clamped, out[..., 2])
    return out.clip(0, 255).astype(np.uint8)


def to_rgba(rgb: np.ndarray, mask: np.ndarray) -> Image.Image:
    return Image.fromarray(np.dstack([rgb, mask.astype(np.uint8) * 255]), "RGBA")


def make_palette(images: list[Image.Image], colors: int) -> Image.Image:
    """Median-cut palette from a coarse sample of every image's opaque pixels."""
    samples = []
    for img in images:
        small = np.array(img.resize((max(1, img.width // 6), max(1, img.height // 6)), Image.Resampling.NEAREST))
        samples.append(small[small[..., 3] > 0][:, :3])
    pixels = np.concatenate(samples)
    mosaic = Image.fromarray(pixels.reshape(1, -1, 3).astype(np.uint8), "RGB")
    return mosaic.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)


def mode_downscale(img: Image.Image, scale: float, palette: Image.Image, colors: int,
                   size: tuple[int, int] | None = None) -> Image.Image:
    """Quantize at full res, then shrink taking the most common colour of each block,
    which keeps pixel art crisp instead of averaging it into mud."""
    index = np.array(img.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE))
    opaque = np.array(img.getchannel("A")) > 0
    out_w, out_h = size or (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    xs = np.linspace(0, img.width, out_w + 1).astype(int)
    ys = np.linspace(0, img.height, out_h + 1).astype(int)
    lut = np.array(palette.getpalette()[: colors * 3], dtype=np.uint8).reshape(-1, 3)
    out = np.zeros((out_h, out_w, 4), dtype=np.uint8)
    for j in range(out_h):
        for i in range(out_w):
            block_alpha = opaque[ys[j]:ys[j + 1], xs[i]:xs[i + 1]]
            if block_alpha.size == 0 or block_alpha.mean() < MIN_COVERAGE:
                continue
            block = index[ys[j]:ys[j + 1], xs[i]:xs[i + 1]][block_alpha]
            out[j, i, :3] = lut[np.bincount(block, minlength=colors).argmax()]
            out[j, i, 3] = 255
    return Image.fromarray(out, "RGBA")


def add_outline(sprite: Image.Image, color: tuple[int, int, int, int]) -> Image.Image:
    """1px outline around the silhouette (image grows by 1px on each side)."""
    padded = np.pad(np.array(sprite), ((1, 1), (1, 1), (0, 0)))
    solid = padded[..., 3] > 0
    padded[ndimage.binary_dilation(solid) & ~solid] = color
    return Image.fromarray(padded, "RGBA")


def seamless_x(img: Image.Image, overlap: int) -> Image.Image:
    """Cross-fade the right edge into the left so the image tiles horizontally.
    The result is `overlap` px narrower."""
    arr = np.array(img).astype(np.float32)
    w = arr.shape[1]
    out = arr[:, : w - overlap].copy()
    t = np.linspace(0.0, 1.0, overlap)[None, :, None]
    out[:, :overlap] = arr[:, w - overlap:] * (1 - t) + arr[:, :overlap] * t
    out[..., 3] = np.where(out[..., 3] >= 128, 255, 0)
    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA")


def components(mask: np.ndarray, link: int, min_area: int) -> list[tuple[slice, slice, np.ndarray]]:
    """Separate objects on a sheet: (row slice, col slice, mask) per object, reading order."""
    labels, count = ndimage.label(ndimage.binary_dilation(mask, iterations=link))
    found = []
    for i, sl in enumerate(ndimage.find_objects(labels), start=1):
        piece = (labels[sl] == i) & mask[sl]
        if piece.sum() >= min_area:
            found.append((sl[0], sl[1], piece))
    height = mask.shape[0]
    row_h = height / 8
    found.sort(key=lambda f: (int(((f[0].start + f[0].stop) / 2) // row_h), f[1].start))
    return found


def preview(img: Image.Image, scale: int = 3, background=(40, 36, 52, 255)) -> Image.Image:
    canvas = Image.new("RGBA", img.size, background)
    canvas.alpha_composite(img)
    return canvas.resize((img.width * scale, img.height * scale), Image.Resampling.NEAREST)
