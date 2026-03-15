from __future__ import annotations

from abc import ABC, abstractmethod


ROUTER_REGISTRY: dict[str, type["RequestRouter"]] = {}


class RequestRouter(ABC):
    """请求路由基类：根据用户输入选择执行路径。"""

    ROUTER_NAME = "base_router"

    @abstractmethod
    def select_route(self, user_input: str) -> str:
        """返回路由键，如: command / quick_chat / agent_graph"""

    @classmethod
    def from_name(cls, router_name: str) -> "RequestRouter":
        router_cls = ROUTER_REGISTRY.get(router_name)
        if not router_cls:
            raise ValueError(f"Router not found: {router_name}")
        return router_cls()


class NoopRouter(RequestRouter):
    ROUTER_NAME = "noop_router"

    def select_route(self, user_input: str) -> str:
        return "agent_graph"


def register_router(router_cls: type[RequestRouter]) -> type[RequestRouter]:
    ROUTER_REGISTRY[router_cls.ROUTER_NAME] = router_cls
    return router_cls


register_router(NoopRouter)
