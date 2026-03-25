from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agent.nodes import executor, planner
from agent.state import AgentState
from config.settings import settings


def should_continue(state: AgentState) -> str:
    if state.get("iteration_count", 0) >= settings.MAX_ITERATIONS:
        return "end"
    if state.get("last_error"):
        return "planner"
    plan = state.get("task_plan")
    if plan and plan.get("completed"):
        return "end"
    return "executor"


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner.run)
    workflow.add_node("executor", executor.run)

    workflow.set_entry_point("planner")

    workflow.add_conditional_edges("planner", lambda s: "executor", {"executor": "executor"})
    workflow.add_conditional_edges(
        "executor",
        should_continue,
        {
            "executor": "executor",
            "planner": "planner",
            "end": END,
        },
    )

    return workflow.compile(checkpointer=MemorySaver())
