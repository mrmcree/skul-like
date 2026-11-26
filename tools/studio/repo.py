"""Where the studio reads and writes things on disk, with path safety checks.

Raw art lives in assets/raw/<name>/ with either sprite.json (character / enemy) or
env.json (level environment). Processed output goes to assets/characters/<name>/ or the
env config's out_dir.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
RAW = ASSETS / "raw"
CHARACTERS = ASSETS / "characters"
NAME_RE = re.compile(r"^[\w-]{1,40}$")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_UPLOAD_BYTES = 40 * 1024 * 1024
CONFIG_FILES = {"sprite": "sprite.json", "env": "env.json"}


class RepoError(ValueError):
    """Bad input from the client (shown to the user as-is)."""


def check_name(name: str) -> str:
    if not NAME_RE.match(name):
        raise RepoError("名称只能包含字母、数字、中文、下划线和横线（最多 40 个字符）")
    return name


def asset_kind(name: str) -> str | None:
    folder = RAW / check_name(name)
    for kind, file in CONFIG_FILES.items():
        if (folder / file).exists():
            return kind
    return None


def list_assets() -> list[dict]:
    out = []
    for folder in sorted(p for p in RAW.iterdir() if p.is_dir()):
        if not NAME_RE.match(folder.name):
            continue
        kind = asset_kind(folder.name)
        images = sorted(p.name for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS)
        out.append({"name": folder.name, "kind": kind, "raw_images": images})
    return out


def read_config(name: str) -> tuple[str, dict] | None:
    kind = asset_kind(name)
    if kind is None:
        return None
    path = RAW / name / CONFIG_FILES[kind]
    return kind, json.loads(path.read_text(encoding="utf-8"))


def _validate(kind: str, config: dict) -> None:
    required = {"sprite": ("cell", "anchor", "target_height", "strips"),
                "env": ("out_dir", "layers", "ground", "sheets")}[kind]
    missing = [k for k in required if k not in config]
    if missing:
        raise RepoError(f"配置缺少字段：{', '.join(missing)}")
    if kind == "sprite":
        for s in config["strips"]:
            if not {"name", "file", "frames"} <= set(s):
                raise RepoError("每个 strip 都需要 name、file、frames")


def write_config(name: str, kind: str, config: dict) -> None:
    if kind not in CONFIG_FILES:
        raise RepoError(f"未知类型：{kind}")
    _validate(kind, config)
    folder = RAW / check_name(name)
    folder.mkdir(parents=True, exist_ok=True)
    other = folder / CONFIG_FILES["env" if kind == "sprite" else "sprite"]
    if other.exists():
        raise RepoError("这个素材已经有另一种类型的配置了")
    (folder / CONFIG_FILES[kind]).write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def save_upload(name: str, filename: str, data: bytes) -> Path:
    filename = Path(filename).name
    if Path(filename).suffix.lower() not in IMAGE_EXTS or not NAME_RE.match(Path(filename).stem):
        raise RepoError("只支持 png / jpg / webp，文件名只能包含字母、数字、中文、下划线和横线")
    if len(data) > MAX_UPLOAD_BYTES:
        raise RepoError("文件太大（上限 40 MB）")
    folder = RAW / check_name(name)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    path.write_bytes(data)
    return path


def sheet_path(name: str) -> Path:
    return CHARACTERS / check_name(name) / f"{name}.png"


def env_outputs(config: dict) -> list[dict]:
    out_dir = ROOT / config["out_dir"]
    metrics_path = out_dir / "metrics.json"
    if not metrics_path.exists():
        return []
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    rel = out_dir.relative_to(ASSETS).as_posix()
    return [{"name": k, "url": f"/files/{rel}/{k}.png", **v} for k, v in metrics.items()]
