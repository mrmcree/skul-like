"""SiliconFlow (硅基流动) LLM helpers for the prompt workbench.

  - expand(): one-line idea -> detailed character look, or level theme + prop list
  - refine(): polish a generated Jimeng prompt, keeping its technical rules

The API key is read from the SILICONFLOW_API_KEY environment variable, or from
tools/studio/.env (git-ignored). Uses the OpenAI-compatible /chat/completions API.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from . import prompts

BASE_URL = "https://api.siliconflow.cn/v1"
DEFAULT_MODEL = "Qwen/Qwen3-32B"
ENV_FILE = Path(__file__).parent / ".env"
TIMEOUT_S = 90
KEYS = ("SILICONFLOW_API_KEY", "SILICONFLOW_MODEL", "SILICONFLOW_BASE_URL")


class LlmError(RuntimeError):
    """Problem talking to the LLM (shown to the user as-is)."""


def _settings() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    for key in KEYS:
        if os.environ.get(key):
            values[key] = os.environ[key]
    return values


def status() -> dict:
    s = _settings()
    return {"configured": bool(s.get("SILICONFLOW_API_KEY")), "model": s.get("SILICONFLOW_MODEL") or DEFAULT_MODEL}


def _request(method: str, path: str, body: dict | None = None) -> dict:
    s = _settings()
    key = s.get("SILICONFLOW_API_KEY")
    if not key:
        raise LlmError("还没有配置硅基流动 API Key（tools/studio/.env 里的 SILICONFLOW_API_KEY）")
    url = (s.get("SILICONFLOW_BASE_URL") or BASE_URL).rstrip("/") + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:400]
        try:
            detail = json.loads(detail).get("message") or detail
        except Exception:
            pass
        raise LlmError(f"硅基流动返回 {err.code}：{detail}") from err
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        raise LlmError(f"连不上硅基流动：{err}") from err


def list_models() -> list[str]:
    data = _request("GET", "/models?type=text&sub_type=chat")
    return sorted(m["id"] for m in data.get("data", []) if isinstance(m, dict) and m.get("id"))


def chat(system: str, user: str, model: str | None = None, temperature: float = 0.7) -> str:
    model = model or status()["model"]
    body: dict = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": temperature,
        "max_tokens": 1500,
    }
    if "qwen3" in model.lower():
        body["enable_thinking"] = False  # faster; we only need the final answer
    data = _request("POST", "/chat/completions", body)
    try:
        content = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as err:
        raise LlmError("硅基流动返回的格式看不懂") from err
    return re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()


def json_from(text: str) -> dict:
    """First {...} object in a model reply (models like to wrap JSON in prose or ```)."""
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise LlmError(f"AI 没有按格式返回：{text[:120]}")
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError as err:
        raise LlmError(f"AI 返回的 JSON 有误：{text[:120]}") from err
    if not isinstance(value, dict):
        raise LlmError("AI 返回的不是对象")
    return value


EXPAND_CHARACTER = (
    "你是像素风 2D 横版动作游戏的美术提示词专家。用户给出一个角色想法，把它扩写成用于即梦 AI 生成精灵图的"
    "角色外观描述：只写外观（性别年龄体型、发型、服装、配色、武器或道具、标志性细节），40 到 90 个汉字，"
    "用逗号分隔的短语。不要写动作、背景、画风、镜头和构图。"
    '只输出 JSON：{"subject": "..."}'
)
EXPAND_ENVIRONMENT = (
    "你是像素风 2D 横版动作游戏的场景美术提示词专家。用户给出一个关卡想法，扩写成："
    "关卡主题（地点、时间、天气氛围、两三种主色调，20 到 50 个汉字）；"
    "装饰物件（5 到 8 个适合做横版场景装饰、能单独抠出来的物件，用顿号分隔）。不要写角色。"
    '只输出 JSON：{"theme": "...", "items": "..."}'
)


def expand(kind: str, idea: str, model: str | None = None) -> dict:
    if kind == "character":
        out = json_from(chat(EXPAND_CHARACTER, idea, model))
        subject = str(out.get("subject", "")).strip()
        if not subject:
            raise LlmError("AI 没有给出角色描述")
        return {"subject": subject[:400]}
    out = json_from(chat(EXPAND_ENVIRONMENT, idea, model))
    theme = str(out.get("theme", "")).strip()
    if not theme:
        raise LlmError("AI 没有给出关卡主题")
    return {"theme": theme[:200], "items": str(out.get("items", "")).strip()[:400]}


REFINE = (
    "你在优化即梦 AI 的像素画提示词。保留原意，让外观描述更具体、更容易被 AI 理解，删掉重复和含糊的词。"
    "必须原样保留所有技术约束：背景色（如 #00FF00、#FF00FF）、行数和每行的动作与帧数、朝向、"
    "帧间空隙、无文字无阴影等要求，不能改动它们的含义和数字。保持中文，不要加解释。"
    '只输出 JSON：{"prompt": "..."}'
)
ROW_RE = re.compile(r"第\d+行[^，,]*?\d+帧")


def ensure_rules(original: str, refined: str) -> tuple[str, list[str]]:
    """Put back technical rules the model dropped; reject rewrites that lost row/frame specs."""
    warnings: list[str] = []
    if any(row not in refined for row in ROW_RE.findall(original)):
        return original, ["AI 改动了行数或帧数说明，已保留原提示词"]
    if "#00FF00" in original and "#00FF00" not in refined:
        refined = f"{refined}，{prompts.CHARACTER_RULES}"
        warnings.append("AI 去掉了绿幕要求，已自动补回")
    if "#FF00FF" in original and "#FF00FF" not in refined:
        refined = f"{refined}，{prompts.ENV_RULES}"
        warnings.append("AI 去掉了洋红背景要求，已自动补回")
    return refined, warnings


def refine(prompt: str, instruction: str = "", model: str | None = None) -> dict:
    user = f"原提示词：\n{prompt}\n\n额外要求：{instruction.strip() or '无'}"
    out = json_from(chat(REFINE, user, model, temperature=0.5))
    refined = str(out.get("prompt", "")).strip()[:3000]
    if not refined:
        raise LlmError("AI 没有返回提示词")
    refined, warnings = ensure_rules(prompt, refined)
    return {"prompt": refined, "warnings": warnings}
