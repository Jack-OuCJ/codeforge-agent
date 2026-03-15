from __future__ import annotations

from agent.state import AgentState


async def run(state: AgentState) -> dict:
    plan = state.get("task_plan")
    if not plan:
        return {"last_error": "缺少任务计划"}
    if plan.get("completed"):
        return {"last_error": None}
    return {
        "last_error": "任务尚未完成，需继续执行",
        "task_plan": {**plan, "completed": False},
    }
