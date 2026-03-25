from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.llm import get_llm, parse_json_from_text
from agent.prompts.planner_prompt import PLANNER_SYSTEM_PROMPT
from agent.state import AgentState
from config.settings import settings
from rag.rag_tool import rag_retrieve


def _format_recent_conversation(messages: list, max_items: int = 8) -> str:
    if not messages:
        return "无"

    collected: list[str] = []
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            text = str(getattr(message, "content", "")).strip()
            if text:
                collected.append(f"用户: {text[:400]}")
        elif isinstance(message, AIMessage):
            if getattr(message, "tool_calls", None):
                continue
            text = str(getattr(message, "content", "")).strip()
            if text:
                collected.append(f"助手: {text[:400]}")

        if len(collected) >= max_items:
            break

    if not collected:
        return "无"

    collected.reverse()
    return "\n".join(collected)


async def _should_use_rag(query: str) -> bool:
    if not query.strip():
        return False
    if not settings.RAG_USE_MODEL_GATE:
        return True

    llm = get_llm(temperature=0)
    response = await llm.ainvoke(
        [
            SystemMessage(
                content=(
                    "你是一个检索开关判断器。"
                    "判断当前问题是否需要依赖外部知识库信息（文档/API规范/业务知识）才能更准确回答。"
                    "如果只是通用编程、闲聊、改写文案、项目内可直接完成的任务，则不需要检索。"
                    "只输出 JSON：{\"use_rag\": true/false, \"reason\": \"一句话\"}"
                )
            ),
            HumanMessage(content=f"用户请求: {query}"),
        ]
    )

    try:
        parsed = parse_json_from_text(response.content)
        return bool(parsed.get("use_rag", False))
    except Exception:
        return False


async def _retrieve_relevant_context(query: str) -> str:
    if not settings.ENABLE_RAG:
        return ""
    if not settings.bailian_knowledge_base_ids:
        return ""

    try:
        if not await _should_use_rag(query):
            return ""
        return await rag_retrieve.ainvoke({"query": query})
    except Exception:
        return ""


async def run(state: AgentState) -> dict:
    last_message = state["messages"][-1].content if state.get("messages") else ""
    recent_conversation = _format_recent_conversation(list(state.get("messages") or []))
    rag_context = await _retrieve_relevant_context(last_message)

    llm = get_llm(temperature=0)
    prompt = f"""
工作目录: {state.get('cwd', '')}
最近会话上下文:
{recent_conversation}

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

    if not steps:
        steps = ["直接回答用户"]

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
