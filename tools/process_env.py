"""Turn AI-generated environment art (backgrounds, ground strip, prop sheets) into game-ready
pixel art.

Usage (from the project root):
    python tools/process_env.py <level>          e.g.  python tools/process_env.py forest

Reads assets/raw/<level>/env.json (see assets/raw/forest/env.json):
  layers  — parallax backgrounds, made horizontally tileable. Either "pixel": N (the source
            draws on an N-px grid: snap to it) or "height": on-screen px. "zoom": integer
            in-game upscale (chunkier, cleaner pixels for distant layers)
  ground  — a side-view ground strip: keeps `rows` px from the top of the grass, tileable
  sheets  — sheets of separate objects on a key colour, cut out in reading order and
            named by `items` (each sized by target `height` or `width` in game px)
"density" (on a layer or sheet): texels per game pixel, e.g. 2 = art drawn at twice the game
resolution and shown at scale 0.5 (the game renders at window resolution, so the detail shows).
Writes PNGs to `out_dir` plus metrics.json (per image: texels, display "scale", "size" and
"surface" = first solid row, both in game px) and preview contact images.
Set "watermark": true on an entry to erase its bottom-right corner (AI logo).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import pixel_tools as pt

ROOT = Path(__file__).resolve().parent.parent
SOLID_ROW = 0.6       # a row counts as the walkable surface once this share of it is opaque
OBJECT_LINK = 6
OBJECT_MIN_AREA = 1500
FRINGE_PX = 3          # source px shaved off keyed edges


def load_keyed(path: Path, key: str, watermark: bool = False, fringe: int = FRINGE_PX) -> Image.Image:
    rgb = np.array(Image.open(path).convert("RGB"))
    if key == "none":
        return pt.to_rgba(rgb, np.ones(rgb.shape[:2], dtype=bool))
    if key == "magenta":
        background = pt.magenta_background(rgb)
    elif key == "cyan":
        background = pt.cyan_background(rgb)
    else:
        background = pt.green_background(rgb)
    mask = ~background
    if watermark:
        mask = pt.erase_corner(mask)
    mask = ndimage.binary_opening(mask, iterations=2)
    # Shave the anti-aliased fringe, which is a key-colour blend (pinkish/cyan speckles).
    if fringe > 0:
        mask = ndimage.binary_erosion(mask, iterations=fringe)
    despilled = pt.despill_edge(rgb, mask, key, width=4) if key == "cyan" else pt.despill(rgb, key)
    return pt.to_rgba(despilled, mask)


def surface_row(img: Image.Image) -> int:
    """First row that is mostly solid — where feet / collision should go."""
    alpha = np.array(img.getchannel("A")) > 0
    widths = alpha.sum(axis=1)
    span = alpha.any(axis=0).sum() or 1
    rows = np.nonzero(widths >= span * SOLID_ROW)[0]
    return int(rows[0]) if len(rows) else 0


def pixelate(img: Image.Image, scale: float, colors: int) -> Image.Image:
    return pt.mode_downscale(img, scale, pt.make_palette([img], colors), colors)


def process_layer(raw: Path, spec: dict) -> Image.Image:
    img = load_keyed(raw / spec["file"], spec["key"], spec.get("watermark", False))
    if spec["key"] != "none":
        top = int(np.nonzero(np.array(img.getchannel("A")).any(axis=1))[0][0])
        img = img.crop((0, top, img.width, img.height))
    overlap = int(img.width * spec.get("seamless", 0))
    if overlap:
        img = pt.seamless_x(img, overlap)
    # "pixel": the source's own pixel-grid size (snap to it exactly);
    # otherwise "height" is the on-screen height (game px), times "density", over "zoom".
    if "pixel" in spec:
        scale = 1.0 / spec["pixel"]
    else:
        scale = spec["height"] * spec.get("density", 1) / spec.get("zoom", 1) / img.height
    return pixelate(img, scale, spec["colors"])


def process_ground(raw: Path, spec: dict) -> Image.Image:
    img = load_keyed(raw / spec["file"], spec["key"], spec.get("watermark", False), spec.get("fringe", FRINGE_PX))
    alpha = np.array(img.getchannel("A")) > 0
    rows = np.nonzero(alpha.any(axis=1))[0]
    top = int(rows[0])
    if "height" in spec:
        bottom = int(rows[-1]) + 1
        img = img.crop((0, top, img.width, bottom))
        scale = spec["height"] * spec.get("density", 1) / (bottom - top)
    else:
        img = img.crop((0, top, img.width, min(img.height, top + int(spec["rows"] / spec["scale"]))))
        scale = spec["scale"]
    overlap = int(img.width * spec.get("seamless", 0))
    if overlap:
        img = pt.seamless_x(img, overlap)
    return pixelate(img, scale, spec["colors"])


def _fill_small_holes(mask: np.ndarray, max_area: int = 80) -> np.ndarray:
    """Fill tiny interior transparent holes caused by anti-aliased speckles."""
    filled = ndimage.binary_fill_holes(mask)
    holes = filled & ~mask
    if not holes.any():
        return mask
    labels, _ = ndimage.label(holes)
    counts = np.bincount(labels.ravel())
    small = (labels > 0) & (counts[labels] <= max_area)
    return mask | small


def process_sheet(raw: Path, spec: dict) -> dict[str, Image.Image]:
    img = load_keyed(raw / spec["file"], spec["key"], spec.get("watermark", False), spec.get("fringe", FRINGE_PX))
    rgba = np.array(img)
    alpha = rgba[..., 3] > 0
    if spec.get("fill_small_holes", False):
        alpha = _fill_small_holes(alpha)
        rgba[..., 3] = np.where(alpha, 255, 0)
    items = spec["items"]
    if spec.get("solo", False):
        if len(items) != 1:
            raise ValueError(f"{spec['file']}: solo=true requires exactly 1 item")
        labels, _ = ndimage.label(ndimage.binary_dilation(alpha, iterations=OBJECT_LINK))
        counts = np.bincount(labels.ravel())
        keep = (labels > 0) & (counts[labels] >= 200) & alpha
        ys, xs = np.nonzero(keep)
        if len(ys) == 0:
            raise ValueError(f"{spec['file']}: solo=true found no foreground pixels")
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        found = [(slice(y0, y1), slice(x0, x1), keep[y0:y1, x0:x1])]
    else:
        found = pt.components(alpha, OBJECT_LINK, OBJECT_MIN_AREA)
        if spec.get("sort") == "x":
            found.sort(key=lambda f: f[1].start)
        if len(found) != len(items):
            raise ValueError(f"{spec['file']}: found {len(found)} objects, config names {len(items)}")
    cut = [Image.fromarray(np.where(m[..., None], rgba[ys, xs], 0).astype(np.uint8), "RGBA")
           for ys, xs, m in found]
    palette = pt.make_palette(cut, spec["colors"])
    density = spec.get("density", 1)
    out = {}
    for item, piece in zip(items, cut):
        scale = item["height"] / piece.height if "height" in item else item["width"] / piece.width
        out[item["name"]] = pt.mode_downscale(piece, scale * density, palette, spec["colors"])
    return out


def contact_sheet(images: dict[str, Image.Image]) -> Image.Image:
    pad, width = 4, 480
    x = y = row_h = 0
    places = {}
    for name, img in images.items():
        if x + img.width > width:
            x, y, row_h = 0, y + row_h + pad, 0
        places[name] = (x, y)
        x += img.width + pad
        row_h = max(row_h, img.height)
    sheet = Image.new("RGBA", (width, y + row_h), (0, 0, 0, 0))
    for name, img in images.items():
        sheet.alpha_composite(img, places[name])
    return sheet


def build(level: str) -> None:
    raw = ROOT / "assets" / "raw" / level
    cfg = json.loads((raw / "env.json").read_text(encoding="utf-8"))
    out_dir = ROOT / cfg["out_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, Image.Image] = {}
    for layer in cfg["layers"]:
        outputs[layer["name"]] = process_layer(raw, layer)
    outputs[cfg["ground"]["name"]] = process_ground(raw, cfg["ground"])
    props: dict[str, Image.Image] = {}
    for sheet in cfg["sheets"]:
        props.update(process_sheet(raw, sheet))
    outputs.update(props)

    # Display scale in game px per texel: zoom / density (e.g. 0.5 = 2x-detail art).
    display = {layer["name"]: layer.get("zoom", 1) / layer.get("density", 1) for layer in cfg["layers"]}
    display[cfg["ground"]["name"]] = 1 / cfg["ground"].get("density", 1)
    for sheet in cfg["sheets"]:
        display.update({item["name"]: 1 / sheet.get("density", 1) for item in sheet["items"]})
    metrics = {}
    for name, img in outputs.items():
        img.save(out_dir / f"{name}.png")
        s = display.get(name, 1)
        metrics[name] = {
            "texels": list(img.size),
            "scale": s,
            "size": [round(img.width * s), round(img.height * s)],   # in game px
            "surface": round(surface_row(img) * s),                  # in game px
        }
        print(f"{name:16s} texels {img.size}  game px {metrics[name]['size']}  scale {s}")
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    previews = ROOT / "assets" / "raw" / level / "previews"
    previews.mkdir(exist_ok=True)
    pt.preview(contact_sheet(props), 3).save(previews / "props.png")
    for layer in [*cfg["layers"], cfg["ground"]]:
        pt.preview(outputs[layer["name"]], 2).save(previews / f"{layer['name']}.png")
    print(f"wrote {len(outputs)} images to {out_dir}")


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    build(sys.argv[1])


if __name__ == "__main__":
    main()
