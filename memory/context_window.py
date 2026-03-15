from __future__ import annotations


class ContextWindowManager:
    def __init__(self, max_chars: int = 12000) -> None:
        self.max_chars = max_chars

    def compact(self, chunks: list[str]) -> str:
        merged = "\n".join(chunks)
        if len(merged) <= self.max_chars:
            return merged
        return merged[-self.max_chars :]
