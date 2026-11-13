"""Load project-local dependencies and keep model caches inside the project."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")
(ROOT / "runtime" / "tmp").mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(ROOT / "runtime" / "tmp")
if sys.prefix == sys.base_prefix:
    sys.path.insert(0, str(ROOT.parent / "lensguard" / ".packages"))
sys.path.insert(0, str(ROOT / ".packages"))
os.environ.setdefault("HF_HOME", str(ROOT / "runtime" / "cache"))
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "120")
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_FLAX", "0")

# Agent dependencies are isolated and appended: existing detector libraries retain priority.
sys.path.append(str(ROOT / ".agent-packages"))
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
