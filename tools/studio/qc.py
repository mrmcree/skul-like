"""Automatic quality checks for processed sprite sheets and environment art.

Each check returns Issue records; the studio shows them next to the frames they refer to.
Levels: "error" (broken, must fix), "warning" (probably wrong, have a look).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image

# Rows whose poses legitimately change size or float (not checked for size / jitter).
NON_STANDING = ("jump", "fall", "hurt", "hit", "death", "dash", "attack")
LOOPING = ("idle", "run", "walk")
SIZE_TOLERANCE = 0.2        # frame height may differ this much from the row median
FEET_TOLERANCE = 2          # texels
JITTER_TOLERANCE = 4.0      # texels, std of horizontal centre in a looping row
RESIDUE_RATIO = 0.003       # share of opaque pixels that may look like key colour
SEAM_TOLERANCE = 40.0       # mean abs difference between left and right edge columns


@dataclass(frozen=True)
class Issue:
    level: str          # "error" | "warning"
    code: str
    message: str
    row: int | None = None
    frame: int | None = None


def _key_residue(rgba: np.ndarray) -> float:
    """Share of opaque pixels that look like leftover green-screen or magenta key colour."""
    solid = rgba[..., 3] > 0
    if not solid.any():
        return 0.0
    r, g, b = (rgba[..., i].astype(np.int32) for i in range(3))
    green = (g > 120) & (g * 10 > r * 13) & (g * 10 > b * 13)
    magenta = (r > 170) & (b > 140) & (g * 2 < r) & (g * 2 < b)
    return float(((green | magenta) & solid).sum()) / float(solid.sum())


def _feet_row(cell: np.ndarray) -> int | None:
    solid = cell[..., 3] > 0
    bright = cell[..., :3].min(axis=-1) > 170
    rows = np.nonzero((solid & ~bright).any(axis=1))[0]
    if not len(rows):
        rows = np.nonzero(solid.any(axis=1))[0]
    return int(rows[-1]) if len(rows) else None


def _frame_issues(cell: np.ndarray, row: int, frame: int, anchor_y: int) -> list[Issue]:
    solid = cell[..., 3] > 0
    if not solid.any():
        return [Issue("error", "empty", "空帧：这一格没有任何内容", row, frame)]
    issues = []
    border = np.concatenate([solid[0], solid[-1], solid[:, 0], solid[:, -1]])
    if border.any():
        issues.append(Issue("warning", "clipped", "贴到格子边缘，可能被裁掉了一部分", row, frame))
    if _key_residue(cell) > RESIDUE_RATIO:
        issues.append(Issue("warning", "residue", "残留绿幕/洋红色像素", row, frame))
    feet = _feet_row(cell)
    if feet is not None and abs(feet - anchor_y) > FEET_TOLERANCE:
        issues.append(Issue("warning", "feet", f"脚底不在锚点上（差 {feet - anchor_y} 像素）", row, frame))
    return issues


def _row_issues(cells: list[np.ndarray], name: str, row: int) -> list[Issue]:
    solid_cells = [c for c in cells if (c[..., 3] > 0).any()]
    if len(solid_cells) < 2:
        return []
    issues = []
    lowered = name.lower()
    if not any(word in lowered for word in NON_STANDING):
        heights = [np.ptp(np.nonzero((c[..., 3] > 0).any(axis=1))[0]) + 1 for c in solid_cells]
        median = float(np.median(heights))
        for i, h in enumerate(heights):
            if abs(h - median) > median * SIZE_TOLERANCE:
                issues.append(Issue("warning", "size", f"大小和同一行其它帧不一致（高 {h}，中位数 {median:.0f}）", row, i))
    if any(word in lowered for word in LOOPING):
        centers = [float(np.nonzero(c[..., 3] > 0)[1].mean()) for c in solid_cells]
        if float(np.std(centers)) > JITTER_TOLERANCE:
            issues.append(Issue("warning", "jitter", f"播放时左右抖动（水平偏移标准差 {np.std(centers):.1f}）", row))
    return issues


def check_sprite_sheet(config: dict, sheet_path: Path) -> list[Issue]:
    """QC a sheet built by process_sprites.py from its sprite.json config."""
    if not sheet_path.exists():
        return [Issue("error", "missing", "还没有处理结果，请先点「处理」")]
    sheet = np.array(Image.open(sheet_path).convert("RGBA"))
    cw, ch = config["cell"]
    anchor_y = config["anchor"][1]
    strips = config["strips"]
    expected = (ch * len(strips), cw * max(s["frames"] for s in strips))
    if sheet.shape[:2] != expected:
        return [Issue("error", "stale", "精灵图尺寸和配置不符，配置改过后需要重新处理")]
    issues: list[Issue] = []
    for r, strip in enumerate(strips):
        cells = [sheet[r * ch:(r + 1) * ch, f * cw:(f + 1) * cw] for f in range(strip["frames"])]
        for f, cell in enumerate(cells):
            issues.extend(_frame_issues(cell, r, f, anchor_y))
        issues.extend(_row_issues(cells, strip["name"], r))
    return issues


def _seam_issue(path: Path) -> Issue | None:
    arr = np.array(Image.open(path).convert("RGBA")).astype(np.int32)
    left, right = arr[:, 0], arr[:, -1]
    both = (left[:, 3] > 0) & (right[:, 3] > 0)
    if not both.any():
        return None
    diff = float(np.abs(left[both, :3] - right[both, :3]).mean())
    if diff > SEAM_TOLERANCE:
        return Issue("warning", "seam", f"{path.stem}：左右边缘差异大（{diff:.0f}），重复拼接时可能看到接缝")
    return None


def check_environment(config: dict, project_root: Path) -> list[Issue]:
    """QC the images written by process_env.py from its env.json config."""
    out_dir = project_root / config["out_dir"]
    metrics_path = out_dir / "metrics.json"
    if not metrics_path.exists():
        return [Issue("error", "missing", "还没有处理结果，请先点「处理」")]
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    issues: list[Issue] = []
    tiling = [layer["name"] for layer in config.get("layers", [])] + [config["ground"]["name"]]
    for name in metrics:
        path = out_dir / f"{name}.png"
        if not path.exists():
            issues.append(Issue("error", "missing", f"{name}.png 不存在"))
            continue
        rgba = np.array(Image.open(path).convert("RGBA"))
        if not (rgba[..., 3] > 0).any():
            issues.append(Issue("error", "empty", f"{name}：图片是空的"))
        elif _key_residue(rgba) > RESIDUE_RATIO:
            issues.append(Issue("warning", "residue", f"{name}：残留洋红/绿幕像素"))
        if name in tiling:
            seam = _seam_issue(path)
            if seam:
                issues.append(seam)
    return issues


def to_report(issues: list[Issue]) -> dict:
    return {
        "ok": not any(i.level == "error" for i in issues),
        "errors": sum(i.level == "error" for i in issues),
        "warnings": sum(i.level == "warning" for i in issues),
        "issues": [asdict(i) for i in issues],
    }
