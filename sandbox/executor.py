from __future__ import annotations

import subprocess
from pathlib import Path


def run(command: list[str], cwd: str = ".", timeout: int = 60) -> tuple[int, str, str]:
    base = Path(cwd).expanduser().resolve()
    proc = subprocess.run(
        command,
        cwd=str(base),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr
