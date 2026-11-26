"""Asset Studio: a local web page for the AI-art pipeline.

  - browse assets, play sprite-sheet animations
  - generate Jimeng prompts (+ a matching config)
  - upload raw images, edit config, run processing
  - automatic QC with issues marked on the frames

Start it with `python tools/asset_studio.py` (listens on 127.0.0.1 only).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import prompts, repo, runner

STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Asset Studio")
app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.mount("/files", StaticFiles(directory=repo.ASSETS), name="files")


def _bad_request(err: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(err))


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/assets")
def list_assets() -> list[dict]:
    return repo.list_assets()


@app.get("/api/assets/{name}")
def get_asset(name: str) -> dict:
    try:
        loaded = repo.read_config(name)
    except repo.RepoError as err:
        raise _bad_request(err) from err
    if loaded is None:
        return {"name": name, "kind": None, "config": None}
    kind, config = loaded
    info: dict = {"name": name, "kind": kind, "config": config}
    if kind == "sprite":
        sheet = repo.sheet_path(name)
        info["sheet_url"] = f"/files/characters/{name}/{name}.png" if sheet.exists() else None
        info["sheet_mtime"] = sheet.stat().st_mtime if sheet.exists() else 0
    else:
        info["outputs"] = repo.env_outputs(config)
    return info


class ConfigBody(BaseModel):
    kind: Literal["sprite", "env"]
    config: dict


@app.put("/api/assets/{name}/config")
def put_config(name: str, body: ConfigBody) -> dict:
    try:
        repo.write_config(name, body.kind, body.config)
    except repo.RepoError as err:
        raise _bad_request(err) from err
    return {"ok": True}


@app.post("/api/assets/{name}/upload")
async def upload(name: str, filename: str, request: Request) -> dict:
    data = await request.body()
    try:
        path = repo.save_upload(name, filename, data)
    except repo.RepoError as err:
        raise _bad_request(err) from err
    return {"ok": True, "file": path.name}


@app.post("/api/assets/{name}/process")
def process(name: str) -> dict:
    try:
        return runner.process(name)
    except repo.RepoError as err:
        raise _bad_request(err) from err


@app.get("/api/assets/{name}/qc")
def get_qc(name: str) -> dict:
    try:
        return runner.run_qc(name)
    except repo.RepoError as err:
        raise _bad_request(err) from err


class ActionBody(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9_]{1,30}$")
    frames: int = Field(ge=1, le=16)
    description: str = Field(min_length=1, max_length=120)


class PromptBody(BaseModel):
    kind: Literal["character", "environment"]
    subject: str = Field(default="", max_length=400)
    style: str = Field(default=prompts.DEFAULT_STYLE, max_length=200)
    actions: list[ActionBody] = Field(default_factory=list, max_length=20)
    target_height: int = Field(default=60, ge=16, le=256)
    theme: str = Field(default="", max_length=200)
    items: str = Field(default="", max_length=400)


@app.get("/api/presets")
def presets() -> dict:
    return {name: [a.__dict__ for a in actions] for name, actions in prompts.PRESETS.items()}


@app.post("/api/prompts")
def make_prompts(body: PromptBody) -> dict:
    if body.kind == "environment":
        if not body.theme:
            raise HTTPException(status_code=400, detail="请填写关卡主题")
        return {"prompts": prompts.environment_prompts(body.theme, body.items, body.style)}
    if not body.subject or not body.actions:
        raise HTTPException(status_code=400, detail="请填写角色描述并至少添加一个动作")
    actions = [prompts.Action(a.name, a.frames, a.description) for a in body.actions]
    sheets = prompts.character_sheets(body.subject, actions, body.style)
    return {"prompts": sheets, "config": prompts.character_config(sheets, actions, body.target_height)}
