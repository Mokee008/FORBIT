"""
sitecustomize.py - Automatic Environment Bootstrapper for FOREST HEARTBEAT
Automatically adds the local virtual environment (.venv) site-packages to sys.path
so that running `python3 <script>` works out-of-the-box even without `source .venv/bin/activate`.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# 1. Add workspace root and src/ to sys.path
for p in [str(ROOT), str(ROOT / "src")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# 2. Add .venv site-packages to sys.path if numpy is not already installed
try:
    import numpy
except ModuleNotFoundError:
    venv_lib = ROOT / ".venv" / "lib"
    if venv_lib.exists():
        for sp in venv_lib.glob("python*/site-packages"):
            if sp.exists() and str(sp) not in sys.path:
                sys.path.insert(0, str(sp))
