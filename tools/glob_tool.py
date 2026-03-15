from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool


@tool
def glob_search(pattern: str, cwd: str = ".") -> str:
    """使用 glob 模式搜索文件。"""
    base = Path(cwd).expanduser().resolve()
    matches = sorted(base.glob(pattern))
    if not matches:
        return "未找到匹配文件"
    return "\n".join(str(path) for path in matches[:500])
