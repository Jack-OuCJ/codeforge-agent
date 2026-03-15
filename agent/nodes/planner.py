from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm import get_llm, parse_json_from_text
from agent.prompts.planner_prompt import PLANNER_SYSTEM_PROMPT
from agent.state import AgentState
from rag.rag_tool import rag_retrieve


async def _retrieve_relevant_context(query: str) -> str:
    try:
        return await rag_retrieve.ainvoke({"query": query})
    except Exception:
        return "知识库检索暂不可用"


async def run(state: AgentState) -> dict:
    last_message = state["messages"][-1].content if state.get("messages") else ""
    rag_context = await _retrieve_relevant_context(last_message)

    llm = get_llm(temperature=0)
    prompt = f"""
工作目录: {state.get('cwd', '')}
RAG上下文: {rag_context}
用户请求: {last_message}
上次错误: {state.get('last_error', '无')}

请输出 JSON 执行计划。
"""
    response = await llm.ainvoke([
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    try:
        parsed = parse_json_from_text(response.content)
        goal = parsed.get("goal") or "完成用户请求"
        steps = parsed.get("steps") or ["分析请求", "执行修改", "验证结果"]
    except Exception:
        goal = "完成用户请求"
        steps = ["分析请求", "执行修改", "验证结果"]

    return {
        "task_plan": {
            "goal": goal,
            "steps": steps,
            "current_step": 0,
            "completed": False,
        },
        "rag_context": rag_context,
        "last_error": None,
        "iteration_count": state.get("iteration_count", 0),
    }
