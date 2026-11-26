"""Prompt templates for generating art with Jimeng / Doubao, plus matching configs.

Encodes the lessons learned in this project:
  - characters on pure green (#00FF00), environments on pure magenta (#FF00FF)
  - side view, facing right, same size per frame, feet on one line
  - big gaps between frames so weapons don't cross into neighbours
  - no slash/trail effects drawn by the AI (the game adds its own)
  - at most MAX_ROWS animation rows per image (more rows -> the AI gets them wrong)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

DEFAULT_STYLE = "16位复古游戏风格，清晰像素颗粒，黑色描边"
MAX_ROWS = 5
CHARACTER_RULES = (
    "所有帧都是侧视图且身体朝向右侧，同一个角色，每帧角色大小完全一致，同一行的脚底在同一水平线上，"
    "帧与帧、行与行之间留出很大的空隙，武器和飘带不能伸进相邻的帧，不要画刀光特效，"
    "纯绿色背景#00FF00，无阴影，无文字，无网格线"
)
ENV_RULES = "没有任何角色，没有文字，纯洋红色背景#FF00FF"


@dataclass(frozen=True)
class Action:
    name: str           # animation name used in the game, e.g. "idle"
    frames: int
    description: str    # what happens, in words, e.g. "待机呼吸动画"


PRESETS: dict[str, list[Action]] = {
    "主角（移动+战斗）": [
        Action("idle", 6, "待机呼吸"), Action("run", 8, "奔跑循环，身体前倾"),
        Action("jump", 5, "跳跃：起跳、上升、最高点、下落、落地"), Action("dash", 4, "向前冲刺，身体压低"),
        Action("attack_1", 6, "武器横斩"), Action("attack_2", 6, "武器从下往上挑斩"),
        Action("attack_3", 6, "后撤蓄力后全力突刺"), Action("hurt", 3, "受击后仰"),
        Action("death", 6, "单膝跪地后倒下"),
    ],
    "近战小怪": [
        Action("idle", 6, "待机呼吸"), Action("walk", 6, "行走循环"),
        Action("attack", 6, "攻击：蓄力、出招、收招"), Action("hit", 3, "受击后仰"),
        Action("death", 6, "倒地死亡"),
    ],
    "远程小怪": [
        Action("idle", 6, "待机呼吸"), Action("walk", 6, "行走循环"),
        Action("attack", 6, "远程攻击：瞄准、发射、收势"), Action("hit", 3, "受击后仰"),
        Action("death", 6, "倒地死亡"),
    ],
}


def _chunks(actions: list[Action]) -> list[list[Action]]:
    """Split actions into sheets of at most MAX_ROWS rows, as evenly as possible."""
    sheets = math.ceil(len(actions) / MAX_ROWS) or 1
    size = math.ceil(len(actions) / sheets)
    return [actions[i:i + size] for i in range(0, len(actions), size)]


def character_sheets(subject: str, actions: list[Action], style: str = DEFAULT_STYLE) -> list[dict]:
    """One prompt per sheet image; each sheet holds up to MAX_ROWS animation rows."""
    out = []
    for i, group in enumerate(_chunks(actions)):
        rows = "，".join(f"第{n + 1}行{a.description}{a.frames}帧" for n, a in enumerate(group))
        prompt = (
            f"像素艺术精灵图集，2D横版动作游戏角色动作表，{subject}，{style}，"
            f"共{len(group)}行，每行一个动作：{rows}，{CHARACTER_RULES}"
        )
        out.append({
            "file": f"Sheet{i + 1}.png",
            "aspect": "1:1",
            "rows": [a.name for a in group],
            "prompt": prompt,
        })
    return out


def character_config(sheets: list[dict], actions: list[Action], target_height: int = 60) -> dict:
    """sprite.json matching character_sheets(): one strip per action, 2x-detail defaults."""
    by_name = {a.name: a for a in actions}
    strips = []
    first = None
    for sheet in sheets:
        for row, name in enumerate(sheet["rows"]):
            strip = {"name": name, "file": sheet["file"], "row": row,
                     "frames": by_name[name].frames, "watermark": True}
            if first is None:
                first = name
            else:
                strip["scale_from"] = first
            strips.append(strip)
    cell_h = math.ceil(target_height * 1.6 / 16) * 16
    cell_w = cell_h * 4 // 3
    return {
        "cell": [cell_w, cell_h],
        "anchor": [cell_w // 2, cell_h - 6],
        "target_height": target_height,
        "palette_colors": 32,
        "feet_ignore_bright": True,
        "watermark_box": [0.8, 0.945, 1.0, 1.0],
        "strips": strips,
    }


ENV_LAYERS = {
    "far": ("21:9", "像素艺术游戏视差背景远景层，{theme}，远处的山峦/天空/剪影，细节少，粗像素块，"
                    "有限调色板，左右边缘可以无缝衔接，横向构图，没有任何角色，没有文字"),
    "mid": ("21:9", "像素艺术游戏视差背景中景层，{theme}，一排树木或建筑的剪影，只占画面下半部分，"
                    "有限调色板，左右边缘可以无缝衔接，上方空隙是纯洋红色背景#FF00FF，没有角色，没有文字"),
    "ground": ("21:9", "像素艺术横版游戏地面截面，{theme}，顶部是地表边缘，下方是土层和石块，侧视剖面图，"
                       "{style}，地面上方是纯洋红色背景#FF00FF，左右边缘可以无缝衔接，没有角色，没有文字"),
    "props": ("16:9", "像素艺术游戏场景装饰物件集合，{theme}：{items}，侧视图，{style}，"
                      "每个物件独立摆放，物件之间留足空隙，" + ENV_RULES),
}


def environment_prompts(theme: str, items: str, style: str = DEFAULT_STYLE) -> list[dict]:
    """Prompts for a level's parallax layers, ground strip and prop sheet."""
    names = {"far": "1_far.png", "mid": "2_mid.png", "ground": "3_ground.png", "props": "5_props.png"}
    return [
        {"file": names[key], "aspect": aspect,
         "prompt": template.format(theme=theme, items=items or "岩石、灌木、草丛", style=style)}
        for key, (aspect, template) in ENV_LAYERS.items()
    ]
