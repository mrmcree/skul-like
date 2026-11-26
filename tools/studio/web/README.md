# Asset Studio (web)

React + Vite + Tailwind v4 + shadcn/ui frontend for the Asset Studio.
The backend (FastAPI, QC, processing) is unchanged: `tools/studio/*.py`.

## Setup (once)

Needs Node.js 20+ (`winget install OpenJS.NodeJS.LTS`).

```powershell
cd tools/studio/web
npm install
```

## Develop (hot reload)

```powershell
# terminal 1, project root
python tools/asset_studio.py
# terminal 2
cd tools/studio/web; npm run dev     # open http://127.0.0.1:5173
```

## Use without Node running

```powershell
cd tools/studio/web; npm run build
python tools/asset_studio.py         # open http://127.0.0.1:8765
```

The backend serves `web/dist` when it exists, and falls back to the old `static/` page otherwise.

## Shortcuts

| Key | Action |
| --- | --- |
| Ctrl + K | command palette |
| ? | shortcut list |
| Right click | context menu on assets, animations, frames, viewport |
| Space | play / pause |
| ← / → | previous / next frame |
| ↑ / ↓ | previous / next animation |
| Ctrl + wheel | zoom the viewport |
| Ctrl + Enter | process the current asset |
| Ctrl + S | save config (in the config editor) |

## SiliconFlow (硅基流动) AI prompts

The prompt workbench can expand a one-line idea and polish generated prompts with an LLM.
Put the key in `tools/studio/.env` (git-ignored; see `.env.example`):

```
SILICONFLOW_API_KEY=sk-...
SILICONFLOW_MODEL=Qwen/Qwen3-32B
```

Restart `python tools/asset_studio.py` after editing it. The key never reaches the browser.
