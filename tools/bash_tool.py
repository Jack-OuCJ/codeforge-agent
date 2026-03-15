from __future__ import annotations

import asyncio
import os
from pathlib import Path

from langchain_core.tools import tool


DANGEROUS_PATTERNS = ["rm -rf /", "dd if=", ":(){:|:&};:", "mkfs", "shutdown", "reboot"]
APPROVAL_PATTERNS = [" rm ", " mv ", " chmod ", " chown ", "> /", "sudo "]


def _needs_approval(command: str) -> bool:
    padded = f" {command.strip()} "
    return any(pattern in padded for pattern in APPROVAL_PATTERNS)


@tool
async def bash(command: str, timeout: int = 30, require_approval: bool = False) -> str:
    """在当前工作目录执行 Shell 命令。"""
    lowered = command.lower()
    if any(pattern in lowered for pattern in DANGEROUS_PATTERNS):
        return f"❌ 危险命令已拦截: {command}"

    if _needs_approval(command) and not require_approval:
        return f"⚠️ 需要用户确认: {command}\n请使用 require_approval=true 重新调用"

    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(Path(os.getcwd()).resolve()),
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return f"❌ 命令超时（>{timeout}s）: {command}"

    output = stdout.decode("utf-8", errors="replace")
    error = stderr.decode("utf-8", errors="replace")

    result = f"Exit Code: {proc.returncode}\n"
    if output:
        result += f"STDOUT:\n{output}\n"
    if error:
        result += f"STDERR:\n{error}\n"
    return result
