from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

from config.settings import settings


@tool
def file_read(file_path: str, start_line: int = 1, end_line: int = -1) -> str:
    """读取文件内容，支持行范围。"""
    target = Path(file_path).expanduser().resolve()
    if not target.exists():
        return f"❌ 文件不存在: {file_path}"
    if not target.is_file():
        return f"❌ 路径不是文件: {file_path}"

    size_kb = target.stat().st_size / 1024
    if size_kb > settings.MAX_FILE_READ_SIZE_KB:
        return f"❌ 文件过大: {size_kb:.1f}KB，超过限制 {settings.MAX_FILE_READ_SIZE_KB}KB"

    content = target.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    if end_line == -1:
        end_line = len(lines)

    start = max(start_line, 1)
    end = min(end_line, len(lines))
    if start > end:
        return ""

    selected = lines[start - 1 : end]
    return "\n".join(selected)
