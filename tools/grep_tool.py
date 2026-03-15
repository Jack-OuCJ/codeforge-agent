from __future__ import annotations

import re
from pathlib import Path

from langchain_core.tools import tool


@tool
def grep_search(pattern: str, path: str = ".", recursive: bool = True) -> str:
    """在文件中搜索文本内容（支持正则）。"""
    root = Path(path).expanduser().resolve()
    flags = re.IGNORECASE
    regex = re.compile(pattern, flags)
    result: list[str] = []

    iterator = root.rglob("*") if recursive else root.glob("*")
    for file in iterator:
        if not file.is_file():
            continue
        try:
            content = file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_no, line in enumerate(content.splitlines(), 1):
            if regex.search(line):
                result.append(f"{file}:{line_no}:{line.strip()}")
        if len(result) >= 500:
            break

    if not result:
        return "未找到匹配内容"
    return "\n".join(result)
