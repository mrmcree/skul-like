"""Run the existing processing scripts and QC them, for the studio."""

from __future__ import annotations

import subprocess
import sys
import threading

from . import qc, repo

SCRIPTS = {"sprite": "tools/process_sprites.py", "env": "tools/process_env.py"}
TIMEOUT_S = 1200
# One processing job at a time: the scripts are CPU-heavy and write shared files.
_lock = threading.Lock()


def run_qc(name: str) -> dict:
    loaded = repo.read_config(name)
    if loaded is None:
        return qc.to_report([qc.Issue("error", "no_config", "还没有配置文件（sprite.json / env.json）")])
    kind, config = loaded
    if kind == "sprite":
        issues = qc.check_sprite_sheet(config, repo.sheet_path(name))
    else:
        issues = qc.check_environment(config, repo.ROOT)
    return qc.to_report(issues)


def process(name: str) -> dict:
    """Run the matching processor as a subprocess; returns its log, exit status and QC."""
    kind = repo.asset_kind(name)
    if kind is None:
        raise repo.RepoError("还没有配置文件，先在「配置」里保存一份")
    if not _lock.acquire(blocking=False):
        raise repo.RepoError("已经有一个处理任务在运行，请稍等")
    try:
        result = subprocess.run(
            [sys.executable, SCRIPTS[kind], name],
            cwd=repo.ROOT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "log": "处理超时", "qc": run_qc(name)}
    finally:
        _lock.release()
    log = (result.stdout + result.stderr).strip()
    return {"ok": result.returncode == 0, "log": log, "qc": run_qc(name)}
