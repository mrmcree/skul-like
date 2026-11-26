# CLAUDE.md

Godot 4.5 的和风像素横版动作 Roguelite 原型（参考《小骨：英雄杀手》）。玩法设计见 `docs/GDD.md`；本文件讲代码怎么组织、怎么验证、有哪些坑。

## 运行与验证

Godot 是免安装版：`C:\personal_work\roglike2\tools\godot\Godot_v4.5-stable_win64_console.exe`（下文记作 `$G`）。

```bash
"$G" --headless --path . --import            # 重新导入资源（改了图片后要跑）
"$G" --headless --path . --quit-after 180    # 跑 3 秒，输出里不能有 ERROR / WARNING / SCRIPT ERROR
python -m pytest tools/studio/tests -q        # 素材工作室的单元测试
```

- **`-s script.gd` 模式不会加载 autoload**（GameSettings / GameFeel / Sfx），一跑就报 "Identifier not found"。冒烟测试要写成 `extends Node` 的场景脚本，再用 `"$G" --headless --path . res://tmp_test.tscn` 运行，跑完删掉临时文件。
- **截图**用游戏自己的渲染缓冲：`await RenderingServer.frame_post_draw` 之后调用 `get_viewport().get_texture().get_image()`，得到 1920×1080 的图。不要截屏幕（窗口可能被别的程序挡住）。headless 模式不能渲染，截图时要去掉 `--headless`。
- 改完代码至少要跑通一次 headless 运行。改了手感或美术，要截图确认。

## 坐标与像素精度（最重要的约定）

- **逻辑分辨率 480×270**。所有玩法数值（速度、判定框、攻击范围）都用逻辑像素，**不要因为渲染分辨率改这些数值**。
- `stretch/mode = canvas_items`，按窗口分辨率渲染，默认窗口 1920×1080，即 4 倍。
- **2 倍精度贴图**：主角、骷髅、中景、装饰物的贴图像素量是逻辑尺寸的 2 倍，显示时缩放 0.5（`DENSITY = 2.0`，或 `metrics.json` 里的 `scale`）。远景和地面按原图的像素网格处理，缩放分别是 2.0 和 1.0。
- 精灵图的锚点 = **脚底**，水平居中在格子里，所以 `flip_h` / `scale.x = -1` 翻转是对称的。新角色的配置必须保持 `anchor.x == cell.x / 2`。

## 代码结构

```
scripts/
  autoload/   game_settings.gd（设置，存 user://settings.cfg）、game_feel.gd（顿帧、震屏）、sfx.gd（音效池）
  player/     player.gd（状态机 NORMAL/DASH/ATTACK/HURT/DEAD）、player_sprite.gd（动画）、
              player_feedback.gd（所有特效和音效）、player_health.gd
  enemies/    skeleton.gd（AI 状态机 PATROL/IDLE/CHASE/ATTACK/HURT/DEAD）、skeleton_sprite.gd
  combat/     attack_data.gd（Resource）、hitbox.gd、hurtbox.gd、hit_info.gd、hit_reaction.gd（闪白、颤抖、回弹，通用）
  vfx/        vfx.gd（Vfx.spawn(name, parent, pos, facing, z)）、vfx_catalog.gd（帧数据表）、impact_burst.gd
  ui/         hud.gd、settings_menu.gd、damage_number.gd
  common/     sheet_frames.gd（把精灵图切成 SpriteFrames）
data/attacks/ 连招和敌人攻击的数值（.tres）：伤害、前摇/判定/收招、判定框、击退、顿帧、震屏、heavy
scenes/       main.tscn（第一关）、player/、enemies/（skeleton + 继承它的 skeleton_elite）、ui/
shaders/flash.gdshader   受击闪白 + 换色（精英骷髅的蓝甲）
```

**约定**
- 玩法逻辑和表现分开：`player.gd` 只管移动和战斗，特效和音效都走 `player_feedback.gd`。
- 攻击数值写在 `AttackData` 资源里，不要硬编码在脚本中。换头系统（里程碑 3）会按头骨替换整套连招。
- 敌人变体优先用**继承场景 + 改 export**（参考 `skeleton_elite.tscn`），不复制脚本。
- 打击感统一走 autoload：`GameFeel.hit_stop()`、`GameFeel.shake()`、`Sfx.play()`。它们已经接入设置菜单（音量、震屏强度、顿帧开关），不要绕过它们直接改 `Engine.time_scale` 或直接播 AudioStreamPlayer。
- GDScript 一律写静态类型；文件控制在 400 行以内；脚本开头写 `##` 文档注释。
- 碰撞层：1 world、2 player、3 enemy、4 player_hurtbox、5 enemy_hurtbox、6 one_way_platform。

## 场景文件的坑

- **`main.tscn` 是在 Godot 编辑器里维护的**。以前用来生成它的脚本已经不用了，不要重新生成，也不要大段手改，小改动可以。
- 编辑器开着的时候按 F5 会保存所有打开的场景，**会用编辑器内存里的旧版本覆盖磁盘上的修改**。如果在外部改了 `.tscn`，要提醒用户在编辑器里重新加载这个场景。
- 手写 `.tscn` 时：`load_steps` = 外部资源数 + 子资源数 + 1；导出的节点引用写成 `node_paths=PackedStringArray("x")` 加 `x = NodePath(...)`。
- 可能有**多个 Claude 会话同时改这个项目**。动手前看一下 `git status` 和文件的修改时间，不要覆盖别人刚改过的东西。

## 美术素材流程

```
即梦/豆包出图 → assets/raw/<名字>/（原图 + sprite.json 或 env.json）
             → tools/ 处理 → assets/characters/<名字>/ 或 assets/environment/<关卡>/ → 自动质检
```

| 工具 | 用途 |
|---|---|
| `tools/process_sprites.py <名字>` | 角色/敌人的绿幕动作条或多行动作表 → 精灵图。配置 `sprite.json`：cell、anchor、target_height、strips（name/file/row/frames/scale_from）、watermark_box、anchor_band、feet_ignore_bright、enhance |
| `tools/process_env.py <关卡>` | 洋红背景的视差层、地面、物件图 → 关卡贴图 + `metrics.json`（游戏内尺寸、缩放、可站立表面所在行）。配置 `env.json`，支持 pixel / height / zoom / density |
| `tools/process_vfx.py` | 太刀刀光图集 → `slash_1/2/3.png` |
| `tools/tint_vfx.py` | 特效换配色、清除前几帧；原图备份在 `assets/raw/vfx_originals/` |
| `tools/gen_ui.py` / `tools/gen_sfx.py` | 生成 HUD 像素图 / 合成音效 |
| `tools/master_sfx.py` | 给武器和受击音效叠加金属刀鸣、低频重量、撞击声并统一响度；始终从 `assets/raw/sfx_originals/` 的原始录音开始处理，重复运行不会叠加两次 |
| `tools/pixel_tools.py` | 共用函数：抠图、去色边、按块取主色缩小、调色板、描边、无缝拼接 |
| **素材工作室** `python tools/asset_studio.py` → http://127.0.0.1:8765 | 网页版：提示词生成（可接入硅基流动 LLM 扩写/润色）、上传原图、编辑配置、一键处理、自动质检、序列帧播放。新版前端在 `tools/studio/web`（React + Vite，`npm install && npm run build` 后由后端提供），旧版静态页在 `tools/studio/static` |

**从 AI 出图积累下来的规则**（已写进 `tools/studio/prompts.py`）：
- 角色用纯绿 `#00FF00` 背景，环境用纯洋红 `#FF00FF` 背景（森林本身全是绿色）。
- 侧视、朝右、每帧大小一致、脚底在同一条线上、**帧和帧之间留大空隙**（不然武器会伸进相邻帧，切帧失败）、**不画刀光**（刀光由游戏特效负责）。
- 一张图最多 5 行动作；同一个角色的多张图都上传同一张参考图。
- AI 的"像素画"大多没有严格的网格。先用自相关检测原图的像素格大小：有规整网格的（比如地面是 6px）按 `1/格子` 精确缩小，没有网格的按"每块取出现最多的颜色"来缩小。
- 豆包和即梦的水印在右下角，用 `watermark_box` 精确抹掉，避免把贴近角落的帧也切掉。

## 项目技能（.claude/skills）

- `game-feel`：顿帧、震屏、缓动、闪白、击退的做法和数值分档。改打击感时用。
- `game-ui-ux`：HUD 和菜单的锚点、缩放、手柄焦点、界面栈、无障碍要求。改 UI 时用。
- 来源：gamedev-skills/awesome-gamedev-agent-skills（Apache-2.0，许可证见 `.claude/skills/LICENSE-gamedev-skills.txt`）。
- **和本项目约定冲突时，以本文件为准**：game-ui-ux 建议把 viewport 设成 1920×1080，但本项目的逻辑分辨率固定是 480×270（见上文"坐标与像素精度"），不要改。

## 密钥

`tools/studio/.env` 存放 `SILICONFLOW_API_KEY`，这个文件被 git 忽略。**不要读出、打印或提交里面的值。**

## 已知问题

- `tools/process_vfx.py` 里的 `PREVIEW_PATH` 写死了一个别的工具的临时目录（`C:\Users\123\.gemini\...`），换台机器就会出错，应该改成 `assets/raw/` 下的路径。
- `assets/characters/samurai/` 是 itch.io 的旧主角素材，代码已经不再引用；`vfx_catalog.gd` 里还留着旧刀光的条目（slash_light、slash_heavy），已经没人用了。`dash_streak` 冲刺时还在用，不要删。
- 玩家的攻击距离（约 20–27 px）比骷髅的枪（约 38 px）短，平衡性还没定（见 GDD 第 13 节）。
- 目前死亡后原地复活、敌人无限复活，都是原型阶段的临时规则。
