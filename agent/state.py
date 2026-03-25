from __future__ import annotations

from typing import Annotated, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class FileContext(TypedDict):
    path: str
    content: str
    last_modified: float


class TaskPlan(TypedDict):
    goal: str
    steps: list[str]
    current_step: int
    completed: bool


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    task_plan: Optional[TaskPlan]
    cwd: str
    file_context: dict[str, FileContext]
    rag_context: Optional[str]
    tool_results: list[dict]
    last_error: Optional[str]
    iteration_count: int
