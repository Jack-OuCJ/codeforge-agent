from __future__ import annotations

import time
from pathlib import Path


class FileMemory:
    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}

    def put(self, path: str, content: str) -> None:
        target = str(Path(path).expanduser().resolve())
        self._cache[target] = {
            "path": target,
            "content": content,
            "last_modified": time.time(),
        }

    def get(self, path: str) -> dict | None:
        target = str(Path(path).expanduser().resolve())
        return self._cache.get(target)

    def all(self) -> dict[str, dict]:
        return self._cache
