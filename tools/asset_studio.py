"""Start the Asset Studio web page.

Usage (from the project root):
    python tools/asset_studio.py            then open http://127.0.0.1:8765
"""

from __future__ import annotations

import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent))

HOST = "127.0.0.1"   # local only: the studio can write files in the project
PORT = 8765

if __name__ == "__main__":
    print(f"Asset Studio: http://{HOST}:{PORT}")
    uvicorn.run("studio.app:app", host=HOST, port=PORT, log_level="warning")
