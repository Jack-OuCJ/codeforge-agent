from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from agent.llm import get_llm
from agent.prompts.executor_prompt import EXECUTOR_SYSTEM_PROMPT
from agent.state import AgentState
from tools import get_all_tools


def _summarize_file_context(file_context: dict) -> str:
    if not file_context:
        return "\n当前无已加载文件上下文。"
    items = [f"- {path}" for path in list(file_context.keys())[:20]]
    return "\n已加载文件:\n" + "\n".join(items)


async def _execute_tool_calls(tool_calls: list[dict]) -> tuple[list[dict], list[ToolMessage]]:
    tools = get_all_tools()
    tool_map = {tool.name: tool for tool in tools}
    results: list[dict] = []
    tool_messages: list[ToolMessage] = []

    for call in tool_calls:
        tool_name = call.get("name", "")
        tool_id = call.get("id", "")
        args = call.get("args", {})

        if tool_name not in tool_map:
            output = f"❌ 未注册工具: {tool_name}"
        else:
            tool_obj = tool_map[tool_name]
            try:
                output = await tool_obj.ainvoke(args)
            except Exception as exc:
                output = f"❌ 工具执行失败: {exc}"

        result = {"tool": tool_name, "args": args, "output": str(output)}
        results.append(result)
        tool_messages.append(ToolMessage(content=str(output), tool_call_id=tool_id))

    return results, tool_messages


def _step_succeeded(results: list[dict]) -> bool:
    if not results:
        return True
    return all(not str(item.get("output", "")).startswith("❌") for item in results)


async def run(state: AgentState) -> dict:
    plan = state.get("task_plan")
    if not plan:
        return {"last_error": "缺少任务计划"}

    step_index = min(plan["current_step"], len(plan["steps"]) - 1)
    current_step = plan["steps"][step_index]

    llm = get_llm()
    llm_with_tools = llm.bind_tools(get_all_tools())

    messages = [
        SystemMessage(content=EXECUTOR_SYSTEM_PROMPT + _summarize_file_context(state.get("file_context", {}))),
        *state.get("messages", []),
        HumanMessage(content=f"当前执行步骤: {current_step}"),
    ]

    response = await llm_with_tools.ainvoke(messages)
    next_state: dict = {
        "messages": [response],
        "iteration_count": state.get("iteration_count", 0) + 1,
    }

    tool_calls = getattr(response, "tool_calls", []) or []
    if tool_calls:
        results, tool_messages = await _execute_tool_calls(tool_calls)
        next_state["tool_results"] = (state.get("tool_results") or []) + results
        next_state["messages"] += tool_messages

        if _step_succeeded(results):
            updated_plan = plan.copy()
            updated_plan["current_step"] += 1
            if updated_plan["current_step"] >= len(updated_plan["steps"]):
                updated_plan["completed"] = True
            next_state["task_plan"] = updated_plan
        else:
            next_state["last_error"] = "工具执行失败，请重新规划"
    else:
        updated_plan = plan.copy()
        updated_plan["current_step"] += 1
        if updated_plan["current_step"] >= len(updated_plan["steps"]):
            updated_plan["completed"] = True
        next_state["task_plan"] = updated_plan

    return next_state
