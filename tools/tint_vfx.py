"""Recolour a VFX sprite sheet to another sheet's palette, and/or blank its first frames.

Usage (from the project root):
    python tools/tint_vfx.py <sheet> [--like <reference>] [--frame-width N --clear-first K]

  --like        map every pixel of <sheet> to the <reference> colour of the closest brightness
                (keeps the shape and shading, swaps the colour scheme)
  --clear-first blank the first K frames (e.g. a stray "spawn dot" frame); needs --frame-width
The original is kept once as assets/raw/vfx_originals/<name>.png (never overwritten).
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ORIGINALS = ROOT / "assets" / "raw" / "vfx_originals"


def luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def tint_like(arr: np.ndarray, reference: np.ndarray) -> np.ndarray:
    ref = reference[reference[..., 3] > 0][:, :3].astype(np.float32)
    ramp = np.unique(ref, axis=0)
    cool = ramp[ramp[:, 2] >= ramp[:, 0]]   # drop warm accent colours (e.g. ember sparks)
    ramp = cool if len(cool) >= 4 else ramp
    ramp = ramp[np.argsort(luminance(ramp))]
    ramp_lum = luminance(ramp)
    out = arr.copy()
    solid = arr[..., 3] > 0
    lum = luminance(arr[..., :3].astype(np.float32))[solid]
    # Stretch brightness to the reference's range, then pick the nearest ramp colour.
    lo, hi = np.percentile(lum, 2), np.percentile(lum, 98)
    target = ramp_lum[0] + (np.clip(lum, lo, hi) - lo) / max(hi - lo, 1) * (ramp_lum[-1] - ramp_lum[0])
    idx = np.abs(ramp_lum[None, :] - target[:, None]).argmin(axis=1)
    out[..., :3][solid] = ramp[idx].astype(np.uint8)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sheet")
    ap.add_argument("--like")
    ap.add_argument("--frame-width", type=int)
    ap.add_argument("--clear-first", type=int, default=0)
    args = ap.parse_args()

    path = Path(args.sheet)
    ORIGINALS.mkdir(parents=True, exist_ok=True)
    original = ORIGINALS / path.name
    if not original.exists():
        shutil.copy(path, original)
    arr = np.array(Image.open(original).convert("RGBA"))

    if args.like:
        arr = tint_like(arr, np.array(Image.open(args.like).convert("RGBA")))
    if args.clear_first:
        if not args.frame_width:
            raise SystemExit("--clear-first needs --frame-width")
        arr[:, : args.frame_width * args.clear_first] = 0
    Image.fromarray(arr, "RGBA").save(path)
    print(f"wrote {path} (from {original})")


if __name__ == "__main__":
    main()
