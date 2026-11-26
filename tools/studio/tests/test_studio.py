"""Tests for the Asset Studio's QC checks, prompt builder, repo safety and API.

Run from the project root:  python -m pytest tools/studio/tests -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from studio import prompts, qc, repo  # noqa: E402

CELL = (32, 32)
ANCHOR = (16, 30)


def _config(rows: list[tuple[str, int]]) -> dict:
    return {"cell": list(CELL), "anchor": list(ANCHOR), "target_height": 20,
            "strips": [{"name": n, "file": "x.png", "frames": f} for n, f in rows]}


def _figure(cell: np.ndarray, x: int, height: int, color=(150, 40, 40)) -> None:
    """Draw a 6px-wide figure standing on the anchor line."""
    cell[ANCHOR[1] - height + 1:ANCHOR[1] + 1, x - 3:x + 3] = (*color, 255)


def _sheet(tmp_path: Path, rows: list[list[dict]]) -> Path:
    w = CELL[0] * max(len(r) for r in rows)
    arr = np.zeros((CELL[1] * len(rows), w, 4), dtype=np.uint8)
    for r, frames in enumerate(rows):
        for f, spec in enumerate(frames):
            cell = arr[r * CELL[1]:(r + 1) * CELL[1], f * CELL[0]:(f + 1) * CELL[0]]
            if spec is not None:
                _figure(cell, spec.get("x", 16), spec.get("h", 20), spec.get("color", (150, 40, 40)))
    path = tmp_path / "sheet.png"
    Image.fromarray(arr, "RGBA").save(path)
    return path


def _codes(issues):
    return sorted((i.code, i.row, i.frame) for i in issues)


# --- QC ------------------------------------------------------------------------

def test_clean_sheet_passes(tmp_path):
    sheet = _sheet(tmp_path, [[{}, {}, {}]])
    assert qc.check_sprite_sheet(_config([("idle", 3)]), sheet) == []


def test_missing_sheet_is_an_error(tmp_path):
    issues = qc.check_sprite_sheet(_config([("idle", 3)]), tmp_path / "nope.png")
    assert [i.code for i in issues] == ["missing"]


def test_stale_sheet_size_is_an_error(tmp_path):
    sheet = _sheet(tmp_path, [[{}, {}]])
    issues = qc.check_sprite_sheet(_config([("idle", 3)]), sheet)
    assert [i.code for i in issues] == ["stale"]


def test_empty_frame_is_an_error(tmp_path):
    sheet = _sheet(tmp_path, [[{}, None, {}]])
    issues = qc.check_sprite_sheet(_config([("idle", 3)]), sheet)
    assert ("empty", 0, 1) in _codes(issues)
    assert qc.to_report(issues)["ok"] is False


def test_size_mismatch_in_standing_row_is_flagged(tmp_path):
    sheet = _sheet(tmp_path, [[{}, {}, {"h": 10}]])
    issues = qc.check_sprite_sheet(_config([("idle", 3)]), sheet)
    assert ("size", 0, 2) in _codes(issues)


def test_size_mismatch_ignored_for_death_row(tmp_path):
    sheet = _sheet(tmp_path, [[{}, {}, {"h": 10}]])
    assert qc.check_sprite_sheet(_config([("death", 3)]), sheet) == []


def test_jitter_in_looping_row_is_flagged(tmp_path):
    sheet = _sheet(tmp_path, [[{"x": 8}, {"x": 24}, {"x": 8}, {"x": 24}]])
    issues = qc.check_sprite_sheet(_config([("run", 4)]), sheet)
    assert ("jitter", 0, None) in _codes(issues)


def test_clipped_frame_is_flagged(tmp_path):
    sheet = _sheet(tmp_path, [[{}, {"x": 3}]])
    issues = qc.check_sprite_sheet(_config([("attack", 2)]), sheet)
    assert ("clipped", 0, 1) in _codes(issues)


def test_green_residue_is_flagged(tmp_path):
    sheet = _sheet(tmp_path, [[{}, {"color": (40, 220, 40)}]])
    issues = qc.check_sprite_sheet(_config([("attack", 2)]), sheet)
    assert ("residue", 0, 1) in _codes(issues)


def test_report_counts():
    report = qc.to_report([qc.Issue("warning", "x", "m"), qc.Issue("error", "y", "m")])
    assert (report["ok"], report["errors"], report["warnings"]) == (False, 1, 1)


# --- prompts -------------------------------------------------------------------

def test_character_prompts_split_into_sheets_of_at_most_five_rows():
    actions = prompts.PRESETS["主角（移动+战斗）"]
    sheets = prompts.character_sheets("女武士", actions)
    assert [len(s["rows"]) for s in sheets] == [5, 4]
    assert all("#00FF00" in s["prompt"] and "女武士" in s["prompt"] for s in sheets)


def test_character_config_matches_sheets():
    actions = prompts.PRESETS["近战小怪"]
    sheets = prompts.character_sheets("骷髅", actions)
    config = prompts.character_config(sheets, actions, target_height=60)
    assert [s["name"] for s in config["strips"]] == [a.name for a in actions]
    assert all(s["file"] == "Sheet1.png" for s in config["strips"])
    assert "scale_from" not in config["strips"][0]
    assert all(s["scale_from"] == "idle" for s in config["strips"][1:])
    assert config["anchor"][0] * 2 == config["cell"][0]


def test_environment_prompts_use_magenta_except_far_layer():
    out = prompts.environment_prompts("森林", "鸟居")
    assert [p["file"] for p in out] == ["1_far.png", "2_mid.png", "3_ground.png", "5_props.png"]
    assert all("#FF00FF" in p["prompt"] for p in out[1:])
    assert "鸟居" in out[-1]["prompt"]


# --- repo safety ---------------------------------------------------------------

@pytest.mark.parametrize("bad", ["../x", "a/b", "", "x" * 41, "a b"])
def test_bad_names_rejected(bad):
    with pytest.raises(repo.RepoError):
        repo.check_name(bad)


def test_upload_rejects_non_images(tmp_path, monkeypatch):
    monkeypatch.setattr(repo, "RAW", tmp_path)
    with pytest.raises(repo.RepoError):
        repo.save_upload("hero", "evil.py", b"print(1)")
    with pytest.raises(repo.RepoError):
        repo.save_upload("..", "x.png", b"x")
    assert repo.save_upload("hero", "Move.png", b"png").name == "Move.png"


def test_write_config_validates(tmp_path, monkeypatch):
    monkeypatch.setattr(repo, "RAW", tmp_path)
    with pytest.raises(repo.RepoError):
        repo.write_config("hero", "sprite", {"cell": [1, 1]})
    good = _config([("idle", 2)])
    repo.write_config("hero", "sprite", good)
    assert repo.read_config("hero") == ("sprite", good)


# --- API -----------------------------------------------------------------------

def test_api_prompts_and_presets():
    from fastapi.testclient import TestClient

    from studio.app import app

    client = TestClient(app)
    assert "近战小怪" in client.get("/api/presets").json()
    res = client.post("/api/prompts", json={
        "kind": "character", "subject": "骷髅",
        "actions": [{"name": "idle", "frames": 6, "description": "待机"}],
    })
    assert res.status_code == 200 and res.json()["config"]["strips"][0]["name"] == "idle"
    bad = client.post("/api/prompts", json={"kind": "character", "subject": "", "actions": []})
    assert bad.status_code == 400
    assert client.get("/api/assets/..%2Fetc").status_code in (400, 404)
