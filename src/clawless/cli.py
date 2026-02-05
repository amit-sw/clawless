from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_ui() -> None:
    app_path = Path(__file__).resolve().parent / "streamlit_app.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    raise SystemExit(subprocess.call(cmd))
