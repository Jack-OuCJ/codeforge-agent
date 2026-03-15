from __future__ import annotations

import difflib
from pathlib import Path

from langchain_core.tools import tool


def _replace_nth(text: str, old: str, new: str, occurrence: int) -> str:
    start = -1
    index = 0
    for _ in range(occurrence):
        start = text.find(old, index)
        if start == -1:
            return text
        index = start + len(old)
    return text[:start] + new + text[start + len(old) :]


def _diff_summary(original: str, updated: str, file_path: str) -> str:
    diff = difflib.unified_diff(
        original.splitlines(),
        updated.splitlines(),
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )
    lines = list(diff)
    if not lines:
        return "✅ 文件无变化"
    preview = "\n".join(lines[:200])
    return f"✅ 已更新: {file_path}\n{preview}"


@tool
def file_edit(file_path: str, old_string: str, new_string: str, occurrence: int = 1) -> str:
    """精确替换文件中的指定文本。"""
    target = Path(file_path).expanduser().resolve()
    if not target.exists():
        return f"❌ 文件不存在: {file_path}"

    content = target.read_text(encoding="utf-8", errors="replace")
    count = content.count(old_string)
    if count == 0:
        return "❌ 未找到目标字符串，请检查是否包含完整上下文"
    if occurrence < 1 or occurrence > count:
        return f"❌ occurrence 超出范围: 1..{count}"

    new_content = _replace_nth(content, old_string, new_string, occurrence)
    target.write_text(new_content, encoding="utf-8")
    return _diff_summary(content, new_content, str(target))


@tool
def file_write(file_path: str, content: str) -> str:
    """创建新文件或完全覆写已有文件。"""
    target = Path(file_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    original = ""
    if target.exists():
        original = target.read_text(encoding="utf-8", errors="replace")
    target.write_text(content, encoding="utf-8")
    return _diff_summary(original, content, str(target))
