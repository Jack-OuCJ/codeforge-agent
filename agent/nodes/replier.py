from __future__ import annotations

from agent.state import AgentState


async def run(state: AgentState) -> dict:
    plan = state.get("task_plan") or {}
    tool_results = state.get("tool_results") or []
    last_error = state.get("last_error")

    lines = ["任务执行完成。"]
    if plan:
        lines.append(f"目标: {plan.get('goal', '')}")
        lines.append(f"步骤进度: {plan.get('current_step', 0)}/{len(plan.get('steps', []))}")

    if tool_results:
        lines.append("最近工具结果:")
        for item in tool_results[-5:]:
            lines.append(f"- {item.get('tool')}: {str(item.get('output', ''))[:120]}")

    if last_error:
        lines.append(f"注意: {last_error}")

    return {"final_response": "\n".join(lines)}
