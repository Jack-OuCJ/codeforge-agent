from __future__ import annotations

from agent.routing.base import RequestRouter, register_router


@register_router
class RuleBasedRouter(RequestRouter):
    """轻量规则路由器，借鉴 OpenHands 路由抽象模式。"""

    ROUTER_NAME = "rule_based_router"

    QUICK_CHAT_KEYWORDS = {
        "你好",
        "hello",
        "hi",
        "hey",
        "help",
        "谢谢",
        "thanks",
        "bye",
    }

    def select_route(self, user_input: str) -> str:
        stripped = user_input.strip()
        lowered = stripped.lower()

        if not stripped:
            return "empty"

        if stripped.startswith("/"):
            return "command"

        if lowered in self.QUICK_CHAT_KEYWORDS:
            return "quick_chat"

        return "agent_graph"
