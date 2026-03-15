from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agent.nodes import executor, planner, replier, verifier
from agent.state import AgentState
from config.settings import settings


def should_continue(state: AgentState) -> str:
    if state.get("iteration_count", 0) >= settings.MAX_ITERATIONS:
        return "replier"
    if state.get("final_response"):
        return "replier"
    if state.get("pending_approval"):
        return "replier"
    if state.get("last_error"):
        return "planner"
    plan = state.get("task_plan")
    if plan and plan.get("completed"):
        return "verifier"
    return "executor"


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner.run)
    workflow.add_node("executor", executor.run)
    workflow.add_node("verifier", verifier.run)
    workflow.add_node("replier", replier.run)

    workflow.set_entry_point("planner")

    workflow.add_conditional_edges("planner", lambda s: "executor", {"executor": "executor"})
    workflow.add_conditional_edges(
        "executor",
        should_continue,
        {
            "executor": "executor",
            "planner": "planner",
            "verifier": "verifier",
            "replier": "replier",
        },
    )
    workflow.add_conditional_edges(
        "verifier",
        lambda s: "replier" if not s.get("last_error") else "executor",
        {
            "replier": "replier",
            "executor": "executor",
        },
    )
    workflow.add_edge("replier", END)

    return workflow.compile(checkpointer=MemorySaver())
