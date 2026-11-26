"""Export the samurai skill effects from pixelfx into assets/vfx/ (skill_*.png + .json).

Usage (from the project root, needs Node 18+):
    python tools/export_skill_vfx.py                 # pixelfx at the default path below
    python tools/export_skill_vfx.py D:/path/pixelfx

Each effect is rendered with `node tools/render.mjs <id> --sheet`, recoloured with the same
crimson ramp as the katana trails (slash_1..3). VfxCatalog reads the JSON's meta.pixelfx, so no
catalog entry is needed. Contact sheets for a quick look go to tmp/pixelfx/<id>/contact.png.
pixelfx is MIT (see assets/vfx/LICENSE-pixelfx.txt).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PIXELFX = Path(r"C:\personal_work\pixel-game\vendor\pixelfx")
OUT_DIR = ROOT / "assets" / "vfx"
TMP_DIR = ROOT / "tmp" / "pixelfx"

KATANA = ["#3a1020", "#6b243e", "#ae2b34", "#e47f5f", "#f8ae77", "#fedfbb", "#ffffff"]
SPARKS = ["#fff3a6", "#ffe26b", "#ff8a2a", "#f2561d"]

# game name -> (pixelfx id, options)
EFFECTS = {
    "skill_issen": ("melee/thrust", {"palette": KATANA, "sparks": SPARKS, "reach": 90}),
    # skill_spin / skill_spin_back are the front and back layers of melee/spin-slash
    # (radius 44, density 2). render.mjs --sheet merges both layers, so they are not exported here.
    "skill_rising": ("melee/uppercut", {"palette": KATANA, "sparks": SPARKS, "outline": "#1a0610"}),
    "parry_clash": ("impacts/parry", {}),
}


def main() -> int:
    pixelfx = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PIXELFX
    if not (pixelfx / "tools" / "render.mjs").exists():
        print(f"找不到 pixelfx：{pixelfx}（应包含 tools/render.mjs）")
        return 1
    node = shutil.which("node")
    if not node:
        print("找不到 node，请先安装 Node.js 18+（winget install OpenJS.NodeJS.LTS）")
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failed = 0
    for name, (fx_id, options) in EFFECTS.items():
        cmd = [node, "tools/render.mjs", fx_id, "--sheet", "--out", str(TMP_DIR), "--opts", json.dumps(options)]
        result = subprocess.run(cmd, cwd=pixelfx, capture_output=True, text=True, encoding="utf-8", errors="replace")
        src = TMP_DIR / fx_id
        base = fx_id.split("/")[1]
        if result.returncode != 0 or not (src / f"{base}.png").exists():
            failed += 1
            print(f"✗ {name} ({fx_id})\n{result.stdout}{result.stderr}")
            continue
        shutil.copyfile(src / f"{base}.png", OUT_DIR / f"{name}.png")
        meta = json.loads((src / f"{base}.json").read_text(encoding="utf-8"))
        meta["meta"]["image"] = f"{name}.png"
        meta["meta"]["pixelfx"]["density"] = 2.0 if name == "parry_clash" else 1.0
        (OUT_DIR / f"{name}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        info = meta["meta"]["pixelfx"]
        print(f"✓ {name:13s} <- {fx_id:18s} {info['frames']} 帧 {info['frameSize'][0]}x{info['frameSize'][1]}  预览 {src / 'contact.png'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
