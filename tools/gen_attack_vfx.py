"""Generate 2x pixel-density twilight katana attack VFX sheets for the heroine.

Produces:
  - assets/raw/vfx/hero_slashes.png  (combined 3-row x 5-col master sheet on #00FFFF)
  - assets/vfx/slash_1.png           (88x48 x 5 frames, horizontal forward cut)
  - assets/vfx/slash_2.png           (76x84 x 5 frames, upward rising slash)
  - assets/vfx/slash_3.png           (112x44 x 5 frames, heavy horizontal piercing thrust)

Usage:
  python tools/gen_attack_vfx.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "assets" / "raw" / "vfx"
OUT_DIR = ROOT / "assets" / "vfx"

# Stepped 5-stop twilight katana palette (RGBA)
TRANSPARENT = (0, 0, 0, 0)
PLUM = (74, 20, 43, 210)
DARK_RED = (148, 30, 48, 240)
CRIMSON = (226, 62, 56, 255)
GOLD = (255, 190, 107, 255)
CORE = (255, 247, 230, 255)
CYAN_KEY = (0, 255, 255, 255)

PALETTE = [TRANSPARENT, PLUM, DARK_RED, CRIMSON, GOLD, CORE]


def _bezier2(p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, t: np.ndarray) -> np.ndarray:
    u = 1.0 - t
    return (u[:, None] ** 2) * p0 + (2.0 * u * t)[:, None] * p1 + (t[:, None] ** 2) * p2


def _paint_arc(
    w: int,
    h: int,
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    u_start: float,
    u_end: float,
    max_half_thick: float,
    intensity: float,
    breakup: float,
    rng: np.random.Generator,
    skew_dir: tuple[float, float] = (1.0, 0.0),
) -> np.ndarray:
    """Render a tapered, asymmetric pixel-art sword crescent into a palette-index grid."""
    grid = np.zeros((h, w), dtype=np.uint8)
    ts = np.linspace(u_start, u_end, 360)
    pts = _bezier2(np.array(p0), np.array(p1), np.array(p2), ts)

    # Tangent & outward normal
    dpts = np.gradient(pts, axis=0)
    norms = np.linalg.norm(dpts, axis=1, keepdims=True).clip(min=1e-5)
    tangents = dpts / norms
    normals = np.stack([-tangents[:, 1], tangents[:, 0]], axis=1)
    # Orient normal consistently toward skew_dir
    if np.dot(normals[len(normals) // 2], np.array(skew_dir)) < 0:
        normals = -normals

    yy, xx = np.mgrid[0:h, 0:w]
    px = xx.astype(np.float32) + 0.5
    py = yy.astype(np.float32) + 0.5

    # Normalized progress along active arc
    rel_u = (ts - u_start) / max(u_end - u_start, 1e-4)
    # Taper profile: thin tail, thick leading belly at ~0.72, razor tip at 1.0
    taper = np.sin(np.pi * (rel_u ** 0.85)) ** 0.75 * (0.45 + 0.75 * rel_u)
    half_w = max_half_thick * taper

    # Compute signed distance to curve & shift core toward leading outer rim
    best_dist = np.full((h, w), 1e6, dtype=np.float32)
    best_idx = np.zeros((h, w), dtype=np.int32)
    best_signed = np.zeros((h, w), dtype=np.float32)

    for k in range(len(ts)):
        dx = px - pts[k, 0]
        dy = py - pts[k, 1]
        d2 = dx * dx + dy * dy
        mask = d2 < best_dist
        best_dist = np.where(mask, d2, best_dist)
        best_idx = np.where(mask, k, best_idx)
        best_signed = np.where(mask, dx * normals[k, 0] + dy * normals[k, 1], best_signed)

    dist = np.sqrt(best_dist)
    hw = half_w[best_idx]
    local_u = rel_u[best_idx]

    # Asymmetric ribbon: sharper outer edge (+normal), softer wake (-normal)
    eff_dist = np.where(best_signed >= 0.0, dist * 1.35, dist * 0.88)
    ratio = eff_dist / np.maximum(hw, 0.35)

    # Breakup noise for late recovery frames
    noise = rng.random((h, w))
    wake_gate = 1.0 - breakup * (0.65 + 0.35 * (1.0 - local_u))
    alive = (hw > 0.4) & (ratio <= 1.0) & (noise < wake_gate + (1.0 - ratio) * 0.4)

    # Core shifted slightly toward outer edge & leading head
    core_score = (1.0 - ratio) * intensity * (0.65 + 0.45 * local_u)
    core_score = np.where(best_signed >= -0.8, core_score * 1.15, core_score * 0.78)

    grid = np.where(alive & (core_score > 0.08), 1, grid)
    grid = np.where(alive & (core_score > 0.22), 2, grid)
    grid = np.where(alive & (core_score > 0.38), 3, grid)
    grid = np.where(alive & (core_score > 0.62), 4, grid)
    grid = np.where(alive & (core_score > 0.80), 5, grid)
    return grid


def _add_sparks_and_streaks(
    grid: np.ndarray,
    points: list[tuple[int, int, int, int]],
) -> np.ndarray:
    """Stamp crisp 1-2px pixel sparks/streaks (x, y, length_x, color_idx)."""
    h, w = grid.shape
    for x, y, lx, c in points:
        for dx in range(lx):
            xi = x + dx
            if 0 <= xi < w and 0 <= y < h and grid[y, xi] < c:
                grid[y, xi] = c
    return grid


def _grid_to_rgba(grid: np.ndarray) -> Image.Image:
    lut = np.array(PALETTE, dtype=np.uint8)
    return Image.fromarray(lut[grid], "RGBA")


def build_slash_1() -> list[Image.Image]:
    """Horizontal forward cut: 88x48, pivot (20, 24)."""
    w, h = 88, 48
    rng = np.random.default_rng(101)
    p0, p1, p2 = (14.0, 34.0), (104.0, 24.0), (22.0, 10.0)
    configs = [
        # (u_start, u_end, max_half_thick, intensity, breakup, sparks)
        (0.12, 0.86, 6.2, 1.05, 0.00, [(72, 17, 4, 4), (77, 25, 3, 3), (62, 31, 3, 2)]),
        (0.04, 0.98, 7.6, 1.15, 0.05, [(78, 20, 5, 5), (81, 23, 4, 4), (69, 13, 3, 3), (66, 33, 4, 3), (46, 26, 6, 3)]),
        (0.10, 0.96, 5.4, 0.85, 0.35, [(80, 18, 3, 4), (75, 29, 3, 3), (58, 12, 2, 2), (42, 22, 5, 2)]),
        (0.22, 0.92, 3.6, 0.62, 0.65, [(79, 16, 2, 3), (73, 28, 2, 2), (61, 13, 2, 2), (50, 33, 2, 1)]),
        (0.35, 0.85, 2.2, 0.40, 0.84, [(76, 17, 2, 3), (68, 29, 1, 2), (59, 13, 1, 2)]),
    ]
    frames = []
    for us, ue, th, inten, brk, sp in configs:
        g = _paint_arc(w, h, p0, p1, p2, us, ue, th, inten, brk, rng, skew_dir=(1.0, 0.0))
        g = _add_sparks_and_streaks(g, sp)
        frames.append(_grid_to_rgba(g))
    return frames


def build_slash_2() -> list[Image.Image]:
    """Upward rising slash: 76x84, pivot (20, 46)."""
    w, h = 76, 84
    rng = np.random.default_rng(202)
    # Sweeps from bottom-front (36, 74) forward through (78, 42) up to crest (28, 8)
    p0, p1, p2 = (34.0, 74.0), (84.0, 40.0), (26.0, 8.0)
    configs = [
        (0.05, 0.80, 6.2, 1.05, 0.00, [(58, 20, 2, 4), (62, 28, 3, 3), (52, 62, 2, 2)]),
        (0.02, 0.98, 7.6, 1.15, 0.05, [(36, 7, 4, 5), (44, 11, 3, 4), (65, 34, 3, 4), (56, 56, 2, 3), (46, 26, 2, 3)]),
        (0.14, 0.98, 5.2, 0.85, 0.35, [(32, 6, 3, 4), (48, 12, 2, 3), (63, 26, 2, 2), (54, 48, 2, 2)]),
        (0.28, 0.95, 3.6, 0.62, 0.65, [(31, 7, 2, 3), (43, 11, 2, 2), (59, 22, 2, 2), (52, 38, 1, 1)]),
        (0.45, 0.92, 2.2, 0.42, 0.84, [(33, 8, 2, 3), (41, 12, 1, 2), (53, 18, 1, 2)]),
    ]
    frames = []
    for us, ue, th, inten, brk, sp in configs:
        g = _paint_arc(w, h, p0, p1, p2, us, ue, th, inten, brk, rng, skew_dir=(1.0, -0.5))
        g = _add_sparks_and_streaks(g, sp)
        frames.append(_grid_to_rgba(g))
    return frames


def build_slash_3() -> list[Image.Image]:
    """Heavy horizontal piercing thrust: 112x44, pivot (18, 22)."""
    w, h = 112, 44
    rng = np.random.default_rng(303)
    yy, xx = np.mgrid[0:h, 0:w]
    px = xx.astype(np.float32) + 0.5
    py = yy.astype(np.float32) + 0.5
    cy = 20.0  # matches katana thrust height (game y=-16 inside -15 pivot)

    configs = [
        # (x_start, x_tip, half_h, ring_rx, ring_ry, ring_cx, inten, brk, streaks)
        (16.0, 90.0, 5.2, 4.5, 11.0, 32.0, 1.05, 0.00, [(14, 15, 14, 3), (20, 25, 12, 3), (86, 19, 8, 5)]),
        (14.0, 108.0, 6.4, 6.5, 14.5, 38.0, 1.18, 0.04, [(10, 13, 22, 4), (16, 27, 20, 4), (48, 11, 18, 3), (54, 29, 16, 3), (96, 19, 12, 5)]),
        (22.0, 106.0, 4.4, 8.0, 16.5, 42.0, 0.86, 0.30, [(18, 12, 16, 3), (26, 28, 14, 3), (68, 14, 14, 2), (72, 26, 12, 2)]),
        (34.0, 102.0, 3.0, 9.0, 17.5, 45.0, 0.60, 0.62, [(30, 13, 10, 2), (42, 27, 9, 2), (78, 16, 8, 3), (84, 23, 6, 2)]),
        (50.0, 98.0, 1.8, 9.5, 18.0, 46.0, 0.38, 0.84, [(56, 18, 4, 3), (72, 21, 5, 2), (88, 19, 3, 3), (64, 14, 3, 2)]),
    ]

    frames = []
    for xs, xt, hh, rx, ry, rcx, inten, brk, streaks in configs:
        grid = np.zeros((h, w), dtype=np.uint8)
        # Straight tapered horizontal piercing lance
        u = np.clip((px - xs) / max(xt - xs, 1.0), 0.0, 1.0)
        in_x = (px >= xs) & (px <= xt)
        # Lance swells quickly near base then tapers razor-sharp to xt
        profile = np.where(u < 0.22, 0.4 + 0.6 * (u / 0.22), (1.0 - (u - 0.22) / 0.78) ** 0.78)
        local_hh = hh * profile
        dy = np.abs(py - cy)
        ratio = dy / np.maximum(local_hh, 0.25)

        noise = rng.random((h, w))
        alive = in_x & (local_hh > 0.3) & (ratio <= 1.0) & (noise < (1.0 - brk * (0.75 - 0.35 * u)) + (1.0 - ratio) * 0.4)
        score = (1.0 - ratio) * inten * (0.85 + 0.25 * u)

        # Tilted elliptical shockwave ring around hilt/mid-blade
        skew_x = (px - rcx) - (py - cy) * 0.18
        ring_r = np.sqrt((skew_x / rx) ** 2 + ((py - cy) / ry) ** 2)
        ring_band = np.abs(ring_r - 1.0) < (0.20 if brk < 0.2 else 0.14)
        ring_alive = ring_band & (noise < (1.0 - brk * 1.05))
        ring_score = (1.0 - np.abs(ring_r - 1.0) / 0.22) * inten * 0.88

        comb = np.maximum(np.where(alive, score, 0.0), np.where(ring_alive, ring_score, 0.0))
        has_any = alive | ring_alive

        grid = np.where(has_any & (comb > 0.08), 1, grid)
        grid = np.where(has_any & (comb > 0.24), 2, grid)
        grid = np.where(has_any & (comb > 0.42), 3, grid)
        grid = np.where(has_any & (comb > 0.65), 4, grid)
        grid = np.where(has_any & (comb > 0.82), 5, grid)
        grid = _add_sparks_and_streaks(grid, streaks)
        frames.append(_grid_to_rgba(grid))
    return frames


def pack_strip(frames: list[Image.Image]) -> Image.Image:
    fw, fh = frames[0].size
    strip = Image.new("RGBA", (fw * len(frames), fh), TRANSPARENT)
    for i, f in enumerate(frames):
        strip.paste(f, (i * fw, 0))
    return strip


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = {
        "slash_1": build_slash_1(),
        "slash_2": build_slash_2(),
        "slash_3": build_slash_3(),
    }
    for name, frames in rows.items():
        strip = pack_strip(frames)
        strip.save(OUT_DIR / f"{name}.png")
        print(f"wrote {name}.png: {strip.size} ({len(frames)} frames of {frames[0].size})")

    # Also build combined 3-row x 5-col master sheet on #00FFFF
    cell_w = max(f[0].width for f in rows.values()) + 12
    cell_h = max(f[0].height for f in rows.values()) + 12
    master = Image.new("RGBA", (cell_w * 5, cell_h * 3), CYAN_KEY)
    for r, frames in enumerate(rows.values()):
        for c, f in enumerate(frames):
            ox = c * cell_w + (cell_w - f.width) // 2
            oy = r * cell_h + (cell_h - f.height) // 2
            master.alpha_composite(f, (ox, oy))
    master.save(RAW_DIR / "hero_slashes.png")
    print(f"wrote hero_slashes.png: {master.size}")


if __name__ == "__main__":
    main()
