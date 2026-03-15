from __future__ import annotations

import subprocess
from pathlib import Path

from langchain_core.tools import tool


@tool
def run_tests(target: str = "", cwd: str = ".", timeout: int = 120) -> str:
    """执行 pytest 测试。"""
    base = Path(cwd).expanduser().resolve()
    cmd = ["pytest", "-q"]
    if target:
        cmd.append(target)

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(base),
        timeout=timeout,
    )
    return (
        f"Exit Code: {proc.returncode}\n"
        f"STDOUT:\n{proc.stdout}\n"
        f"STDERR:\n{proc.stderr}\n"
    )
