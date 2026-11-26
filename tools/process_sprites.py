"""Turn AI-generated (e.g. Jimeng) green-screen animation strips into a clean pixel-art sheet.

Usage (from the project root):
    python tools/process_sprites.py <character>        e.g.  python tools/process_sprites.py skeleton

Input:  assets/raw/<character>/sprite.json  — config (see below)
        assets/raw/<character>/<images>     — one image per animation, green background,
                                              frames left-to-right (possibly several rows)
Output: assets/characters/<character>/<character>.png  — one row per animation (config order),
            cell-sized frames, feet of every frame at `anchor`, shared palette, hard alpha
        assets/characters/<character>/preview.png      — 4x upscaled check image

sprite.json:
{
  "cell": [80, 48],            frame size in the output sheet
  "anchor": [40, 45],          where the feet go inside each cell (keep x centred for flipping)
  "target_height": 32,         standing-pose height in game pixels (first frame of each strip)
  "palette_colors": 24,
  "torso_hue": [0.92, 0.04],   optional: hue range (0..1, may wrap) of the body colour used to
                               centre frames horizontally; omit to centre on the whole silhouette
  "strips": [
    {"name": "idle", "file": "Idle.png", "frames": 6, "watermark": true},
    {"name": "death", "file": "Death.jpg", "frames": 6, "scale_from": "attack"}
  ]
}
"row": for a sheet holding several animations (one per row), which row this strip is.
"watermark_box": [x0, y0, x1, y1] fractions erased when "watermark" is set (default bottom-right).
"anchor_band": [lo, hi] height fractions above the feet used for horizontal centring.
"enhance": {"brightness": 1.2, "contrast": 1.1, "saturation": 1.1} to lift dark art.
"feet_ignore_bright": true to find the feet ignoring bright pixels (a blade below the feet).
"watermark": erase the bottom-right corner (Jimeng logo). "scale_from": reuse another strip's
scale when this strip has no standing first frame (lying down, crouching...).
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
RAW_ROOT = ROOT / "assets" / "raw"
OUT_ROOT = ROOT / "assets" / "characters"

MIN_BLOB_AREA = 150        # source pixels; smaller specks are noise
LINK_RADIUS = 5            # dilation used to keep a weapon attached to its owner
BODY_FRACTION = 0.3        # blobs smaller than this share of the largest are debris
MIN_COVERAGE = 0.45        # an output pixel is opaque if this share of its block is
TORSO_MIN_SATURATION = 0.35
OUTLINE_COLOR = (20, 6, 18, 255)


@dataclass(frozen=True)
class Strip:
    name: str
    file: str
    frames: int
    watermark: bool = False
    scale_from: str | None = None
    row: int | None = None          # which row of a multi-row sheet (0-based)


@dataclass(frozen=True)
class Config:
    cell: tuple[int, int]
    anchor: tuple[int, int]
    target_height: int
    palette_colors: int
    torso_hue: tuple[float, float] | None
    strips: list[Strip]
    watermark_box: tuple[float, float, float, float] = (0.76, 0.80, 1.0, 1.0)
    anchor_band: tuple[float, float] | None = None
    feet_ignore_bright: bool = False
    enhance: tuple[float, float, float] = (1.0, 1.0, 1.0)   # brightness, contrast, saturation

    @staticmethod
    def load(path: Path) -> Config:
        data = json.loads(path.read_text(encoding="utf-8"))
        hue = data.get("torso_hue")
        return Config(
            cell=tuple(data["cell"]),
            anchor=tuple(data["anchor"]),
            target_height=int(data["target_height"]),
            palette_colors=int(data.get("palette_colors", 24)),
            torso_hue=tuple(hue) if hue else None,
            strips=[Strip(**s) for s in data["strips"]],
            watermark_box=tuple(data.get("watermark_box", (0.76, 0.80, 1.0, 1.0))),
            anchor_band=tuple(data["anchor_band"]) if "anchor_band" in data else None,
            feet_ignore_bright=bool(data.get("feet_ignore_bright", False)),
            enhance=(
                float(data.get("enhance", {}).get("brightness", 1.0)),
                float(data.get("enhance", {}).get("contrast", 1.0)),
                float(data.get("enhance", {}).get("saturation", 1.0)),
            ),
        )


# --- segmentation ---------------------------------------------------------------

def foreground_mask(rgb: np.ndarray, watermark: bool, box=(0.76, 0.80, 1.0, 1.0)) -> np.ndarray:
    r, g, b = (rgb[..., i].astype(np.int32) for i in range(3))
    background = (g > 90) & (g * 4 > r * 5) & (g * 4 > b * 5)
    mask = ~background
    if watermark:
        h, w = mask.shape
        mask[int(h * box[1]):int(h * box[3]), int(w * box[0]):int(w * box[2])] = False
    return ndimage.binary_opening(mask, iterations=1)


def find_frames(mask: np.ndarray, expected: int) -> list[np.ndarray]:
    """Return one boolean mask per frame, in reading order."""
    linked = ndimage.binary_dilation(mask, iterations=LINK_RADIUS)
    labels, count = ndimage.label(linked)
    blobs = [(labels == i) & mask for i in range(1, count + 1)]
    blobs = [b for b in blobs if b.sum() >= MIN_BLOB_AREA]
    if not blobs:
        raise ValueError("no character found — is the background green?")
    blobs.sort(key=lambda b: b.sum(), reverse=True)

    # Bodies are the big blobs; small ones (loose bones, a falling hat) are debris.
    largest = blobs[0].sum()
    bodies = [b for b in blobs[:expected] if b.sum() >= largest * BODY_FRACTION]
    debris = blobs[len(bodies):]
    while len(bodies) < expected:
        bodies = _split_widest(bodies)
    for piece in debris:
        _nearest(bodies, piece)[...] |= piece
    return _reading_order(bodies, mask.shape[0])


def _nearest(bodies: list[np.ndarray], piece: np.ndarray) -> np.ndarray:
    cy, cx = ndimage.center_of_mass(piece)
    return min(bodies, key=lambda b: np.hypot(*(np.subtract(ndimage.center_of_mass(b), (cy, cx)))))


def _split_widest(bodies: list[np.ndarray]) -> list[np.ndarray]:
    """Two touching frames came out as one blob: cut it at its thinnest column."""
    widths = [np.ptp(np.nonzero(b.any(axis=0))[0]) for b in bodies]
    i = int(np.argmax(widths))
    blob = bodies[i]
    cols = np.nonzero(blob.any(axis=0))[0]
    lo, hi = cols[0] + int(len(cols) * 0.35), cols[0] + int(len(cols) * 0.65)
    cut = lo + int(np.argmin(blob[:, lo:hi].sum(axis=0)))
    left, right = blob.copy(), blob.copy()
    left[:, cut:] = False
    right[:, :cut] = False
    return bodies[:i] + [left, right] + bodies[i + 1:]


def _reading_order(bodies: list[np.ndarray], height: int) -> list[np.ndarray]:
    centers = [ndimage.center_of_mass(b) for b in bodies]
    row_of = [round(cy / (height * 0.5)) for cy, _ in centers]
    order = sorted(range(len(bodies)), key=lambda i: (row_of[i], centers[i][1]))
    return [bodies[i] for i in order]


# --- per-frame processing -----------------------------------------------------------

def hue_saturation(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-pixel HSV hue (0..1) and saturation."""
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
    return hue, saturation


def anchor_x(rgb: np.ndarray, frame: np.ndarray, torso_hue: tuple[float, float] | None,
             band: tuple[float, float] | None = None) -> float:
    """Horizontal anchor: centre of the torso colour (stable across poses), else silhouette.
    `band` limits it to a height range measured up from the feet (fractions of frame height),
    e.g. waist-to-chest, so a flowing scarf or cape doesn't drag the anchor around."""
    pick = frame
    if band:
        ys = np.nonzero(frame.any(axis=1))[0]
        top, feet = ys[0], ys[-1]
        height = feet - top + 1
        rows = np.zeros_like(frame)
        rows[int(feet - band[1] * height):int(feet - band[0] * height) + 1] = True
        frame = frame & rows
        pick = frame if frame.any() else pick
    if torso_hue:
        hue, sat = hue_saturation(rgb)
        lo, hi = torso_hue
        in_range = (hue >= lo) | (hue <= hi) if lo > hi else (hue >= lo) & (hue <= hi)
        torso = frame & in_range & (sat > TORSO_MIN_SATURATION)
        if torso.sum() > 50:
            pick = torso
    return float(np.nonzero(pick)[1].mean())


def frame_height(frame: np.ndarray) -> int:
    rows = np.nonzero(frame.any(axis=1))[0]
    return int(rows[-1] - rows[0] + 1)


@dataclass(frozen=True)
class Cut:
    """One frame at source resolution, plus where its torso is."""
    image: Image.Image   # RGBA, hard alpha
    anchor_x: float      # torso x inside the crop (source px)
    scale: float
    feet_y: float = -1   # feet row inside the crop (source px); -1 = bottom of the crop


def feet_row(rgb: np.ndarray, frame: np.ndarray) -> int:
    """Lowest row of non-bright pixels: ignores a white blade hanging below the feet."""
    bright = rgb.astype(np.int32).min(axis=-1) > 170
    rows = np.nonzero((frame & ~bright).any(axis=1))[0]
    return int(rows[-1]) if len(rows) else int(np.nonzero(frame.any(axis=1))[0][-1])


def cut_frame(rgb: np.ndarray, frame: np.ndarray, scale: float, torso_hue, band=None,
              ignore_bright: bool = False) -> Cut:
    """Crop one frame at full resolution and despill the green fringe."""
    ys, xs = np.nonzero(frame)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    crop = rgb[y0:y1, x0:x1].astype(np.int32)
    crop[..., 1] = np.minimum(crop[..., 1], np.maximum(crop[..., 0], crop[..., 2]))
    alpha = frame[y0:y1, x0:x1].astype(np.uint8) * 255
    image = Image.fromarray(np.dstack([crop.clip(0, 255).astype(np.uint8), alpha]), "RGBA")
    feet = feet_row(rgb, frame) - y0 if ignore_bright else -1
    return Cut(image, anchor_x(rgb, frame, torso_hue, band) - x0, scale, feet)


# --- palette + pixel downscale -----------------------------------------------------

def shared_palette(cuts: list[Cut], colors: int) -> Image.Image:
    """Median-cut palette from a small mosaic of every frame's opaque pixels."""
    thumbs = [np.array(c.image.resize((max(1, c.image.width // 6), max(1, c.image.height // 6)),
                                      Image.Resampling.NEAREST)) for c in cuts]
    pixels = np.concatenate([t[t[..., 3] > 0][:, :3] for t in thumbs])
    mosaic = Image.fromarray(pixels.reshape(1, -1, 3).astype(np.uint8), "RGB")
    return mosaic.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)


def pixelate(cut: Cut, palette: Image.Image, colors: int) -> Image.Image:
    """Quantize at full res, then shrink by taking the most common colour per block,
    which keeps colours crisp instead of averaging them into mud."""
    index = np.array(cut.image.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE))
    opaque = np.array(cut.image.getchannel("A")) > 0
    out_w = max(1, round(cut.image.width * cut.scale))
    out_h = max(1, round(cut.image.height * cut.scale))
    xs = np.linspace(0, cut.image.width, out_w + 1).astype(int)
    ys = np.linspace(0, cut.image.height, out_h + 1).astype(int)
    lut = np.array(palette.getpalette()[: colors * 3], dtype=np.uint8).reshape(-1, 3)
    out = np.zeros((out_h, out_w, 4), dtype=np.uint8)
    for j in range(out_h):
        for i in range(out_w):
            block_alpha = opaque[ys[j]:ys[j + 1], xs[i]:xs[i + 1]]
            if block_alpha.size == 0 or block_alpha.mean() < MIN_COVERAGE:
                continue
            block = index[ys[j]:ys[j + 1], xs[i]:xs[i + 1]][block_alpha]
            out[j, i, :3] = lut[np.bincount(block).argmax()]
            out[j, i, 3] = 255
    return Image.fromarray(out, "RGBA")


def add_outline(sprite: Image.Image) -> Image.Image:
    """1px dark outline around the silhouette, so it reads on any background."""
    padded = np.pad(np.array(sprite), ((1, 1), (1, 1), (0, 0)))
    solid = padded[..., 3] > 0
    padded[ndimage.binary_dilation(solid) & ~solid] = OUTLINE_COLOR
    return Image.fromarray(padded, "RGBA")


# --- sheet assembly -----------------------------------------------------------------

def place_in_cell(sprite: Image.Image, cut: Cut, cfg: Config, label: str) -> Image.Image:
    """Put the sprite in a cell with its torso/feet on the anchor; overflow is clipped."""
    if sprite.width > cfg.cell[0] or sprite.height > cfg.cell[1]:
        print(f"  warning: {label} {sprite.size} exceeds cell {cfg.cell}")
    # +1 / -1 account for the outline pixel added on each side.
    x = round(cfg.anchor[0] - (cut.anchor_x * cut.scale + 1))
    feet = sprite.height - 1 if cut.feet_y < 0 else cut.feet_y * cut.scale + 1
    y = round(cfg.anchor[1] - feet)
    if x < 0 or y < 0:
        print(f"  note: {label} shifted to fit cell (dest {x},{y})")
    cell = Image.new("RGBA", cfg.cell, (0, 0, 0, 0))
    cell.alpha_composite(sprite, (max(0, x), max(0, y)))
    return cell


def load_rgb(path: Path, enhance: tuple[float, float, float]) -> np.ndarray:
    """Load an image as RGB, optionally brightening / adding contrast / saturating it."""
    img = Image.open(path).convert("RGB")
    brightness, contrast, saturation = enhance
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if saturation != 1.0:
        img = ImageEnhance.Color(img).enhance(saturation)
    return np.array(img)


def split_rows(frames: list[np.ndarray]) -> list[list[np.ndarray]]:
    """Group frames of a multi-row sheet into rows: cluster by vertical centre, then sort by x."""
    centers = [ndimage.center_of_mass(f) for f in frames]
    gap = 0.5 * float(np.median([frame_height(f) for f in frames]))
    order = sorted(range(len(frames)), key=lambda i: centers[i][0])
    rows: list[list[int]] = [[order[0]]]
    for prev, cur in zip(order, order[1:]):
        if centers[cur][0] - centers[prev][0] > gap:
            rows.append([])
        rows[-1].append(cur)
    return [[frames[i] for i in sorted(row, key=lambda i: centers[i][1])] for row in rows]


def sheet_rows(raw_dir: Path, cfg: Config, file: str, cache: dict) -> tuple[np.ndarray, list]:
    """Load a multi-row sheet once and return (rgb, rows of frame masks)."""
    if file not in cache:
        strips = [s for s in cfg.strips if s.file == file]
        rgb = load_rgb(raw_dir / file, cfg.enhance)
        mask = foreground_mask(rgb, any(s.watermark for s in strips), cfg.watermark_box)
        rows = split_rows(find_frames(mask, sum(s.frames for s in strips)))
        counts = [len(r) for r in rows]
        expected = [s.frames for s in sorted(strips, key=lambda s: s.row)]
        if counts != expected:
            raise ValueError(f"{file}: rows have {counts} frames, config expects {expected}")
        cache[file] = (rgb, rows)
    return cache[file]


def load_rows(raw_dir: Path, cfg: Config) -> list[list[Cut]]:
    scales: dict[str, float] = {}
    rows: list[list[Cut]] = []
    cache: dict = {}
    for strip in cfg.strips:
        if not (raw_dir / strip.file).exists():
            # e.g. a new Skills.png not generated yet; the game falls back for missing rows.
            # Keep such strips at the end of the config, or the rows after them shift up.
            print(f"skip {strip.name}: {strip.file} not found")
            continue
        if strip.row is not None:
            rgb, sheet = sheet_rows(raw_dir, cfg, strip.file, cache)
            frames = sheet[strip.row]
        else:
            rgb = load_rgb(raw_dir / strip.file, cfg.enhance)
            frames = find_frames(foreground_mask(rgb, strip.watermark, cfg.watermark_box), strip.frames)
        if strip.scale_from:
            scale = scales[strip.scale_from]
        else:
            scale = cfg.target_height / frame_height(frames[0])
        scales[strip.name] = scale
        rows.append([cut_frame(rgb, f, scale, cfg.torso_hue, cfg.anchor_band, cfg.feet_ignore_bright)
                     for f in frames])
        print(f"row {len(rows) - 1}: {strip.name} — {len(frames)} frames, scale {scale:.4f}")
    return rows


def build(character: str) -> None:
    raw_dir = RAW_ROOT / character
    cfg = Config.load(raw_dir / "sprite.json")
    rows = load_rows(raw_dir, cfg)

    palette = shared_palette([cut for row in rows for cut in row], cfg.palette_colors)
    columns = max(len(row) for row in rows)
    sheet = Image.new("RGBA", (cfg.cell[0] * columns, cfg.cell[1] * len(rows)), (0, 0, 0, 0))
    for r, row in enumerate(rows):
        for c, cut in enumerate(row):
            sprite = add_outline(pixelate(cut, palette, cfg.palette_colors))
            cell = place_in_cell(sprite, cut, cfg, f"{cfg.strips[r].name}[{c}]")
            sheet.paste(cell, (c * cfg.cell[0], r * cfg.cell[1]))

    out_dir = OUT_ROOT / character
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet.save(out_dir / f"{character}.png")
    preview = Image.new("RGBA", sheet.size, (40, 36, 52, 255))
    preview.alpha_composite(sheet)
    preview.resize((sheet.width * 4, sheet.height * 4), Image.Resampling.NEAREST).save(out_dir / "preview.png")
    print(f"wrote {out_dir / f'{character}.png'} {sheet.size}")


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    character = sys.argv[1]
    if not (RAW_ROOT / character / "sprite.json").exists():
        sys.exit(f"missing {RAW_ROOT / character / 'sprite.json'}")
    build(character)


if __name__ == "__main__":
    main()
