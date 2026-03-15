from __future__ import annotations

import subprocess
from pathlib import Path

from langchain_core.tools import tool


@tool
def apply_patch_tool(patch_content: str, cwd: str = ".") -> str:
    """应用 unified diff 补丁内容。"""
    base = Path(cwd).expanduser().resolve()
    proc = subprocess.run(
        ["patch", "-p0"],
        input=patch_content,
        text=True,
        capture_output=True,
        cwd=str(base),
    )
    return (
        f"Exit Code: {proc.returncode}\n"
        f"STDOUT:\n{proc.stdout}\n"
        f"STDERR:\n{proc.stderr}\n"
    )
