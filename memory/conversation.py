from __future__ import annotations

from collections import deque


class ConversationMemory:
    def __init__(self, max_items: int = 100) -> None:
        self._messages: deque[dict] = deque(maxlen=max_items)

    def add(self, role: str, content: str) -> None:
        self._messages.append({"role": role, "content": content})

    def all(self) -> list[dict]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()
