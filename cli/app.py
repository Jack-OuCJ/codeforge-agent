from __future__ import annotations

from pathlib import Path
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.live import Live
from rich.panel import Panel

from agent.graph import build_graph
from agent.llm import get_llm, parse_json_from_text
from agent.prompts.planner_prompt import PLANNER_SYSTEM_PROMPT
from agent.routing import RequestRouter
from cli.display import render_event
from config.settings import settings


console = Console()
Mode = Literal["plan", "ask", "agent"]
MODE_ORDER: list[Mode] = ["plan", "ask", "agent"]


def _next_mode(current_mode: Mode) -> Mode:
    index = MODE_ORDER.index(current_mode)
    return MODE_ORDER[(index + 1) % len(MODE_ORDER)]


def _build_initial_state(user_input: str, cwd: str) -> dict:
    return {
        "messages": [HumanMessage(content=user_input)],
        "cwd": str(Path(cwd).resolve()),
        "task_plan": None,
        "file_context": {},
        "rag_context": None,
        "tool_results": [],
        "last_error": None,
        "iteration_count": 0,
        "final_response": None,
        "pending_approval": None,
    }


async def _run_once(graph, user_input: str, cwd: str) -> dict:
    thread_config = {"configurable": {"thread_id": "main"}}
    final_output: dict = {}
    with Live(console=console, refresh_per_second=8) as live:
        async for event in graph.astream_events(
            _build_initial_state(user_input, cwd),
            config=thread_config,
            version="v2",
        ):
            render_event(event, live)
            if event.get("event") == "on_chain_end":
                output = event.get("data", {}).get("output")
                if isinstance(output, dict):
                    final_output = output
    return final_output


async def _run_plan_only(user_input: str, cwd: str) -> None:
    llm = get_llm(temperature=0)
    prompt = f"""
你现在处于 PLAN 模式。
仅生成可执行计划，不要调用工具，不要假装执行。

工作目录: {Path(cwd).resolve()}
用户请求: {user_input}

请输出 JSON：
{{
  "goal": "目标描述",
  "steps": ["步骤1", "步骤2", "步骤3"]
}}
"""
    response = await llm.ainvoke(
        [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
    )

    try:
        parsed = parse_json_from_text(response.content)
        goal = parsed.get("goal", "")
        steps = parsed.get("steps", [])
        lines = [f"[bold cyan]PLAN[/bold cyan] 目标: {goal}"]
        if steps:
            lines.append("步骤:")
            lines.extend([f"{idx}. {step}" for idx, step in enumerate(steps, 1)])
        console.print(Panel("\n".join(lines), border_style="cyan"))
    except Exception:
        console.print(Panel(response.content, border_style="cyan"))


async def _run_ask_only(user_input: str) -> None:
    llm = get_llm()
    response = await llm.ainvoke(
        [
            SystemMessage(content="你处于 ASK 模式。只回答问题，不调用工具，不给出虚假执行结果。"),
            HumanMessage(content=user_input),
        ]
    )
    console.print(Panel(response.content, border_style="green"))


async def main_loop(cwd: str = ".", prompt: str = "") -> None:
    graph = build_graph()
    router = RequestRouter.from_name(settings.ROUTER_NAME)
    mode: Mode = "agent"

    bindings = KeyBindings()

    @bindings.add("s-tab")
    def _switch_mode(event):
        nonlocal mode
        mode = _next_mode(mode)
        event.app.invalidate()
        console.print(f"[bold yellow]模式切换 -> {mode.upper()}[/bold yellow]")

    async def dispatch_request(user_input: str) -> bool:
        route = router.select_route(user_input)
        if route == "empty":
            return True

        if route == "command":
            parts = user_input.strip().split()
            command = parts[0]
            if command == "/help":
                console.print("/help /clear /mode [plan|ask|agent] /exit")
                return True
            if command == "/clear":
                console.clear()
                return True
            if command == "/mode":
                nonlocal mode
                if len(parts) == 1:
                    console.print(f"当前模式: [bold]{mode.upper()}[/bold]")
                    return True
                target = parts[1].lower()
                if target not in {"plan", "ask", "agent"}:
                    console.print("[yellow]可用模式: plan / ask / agent[/yellow]")
                    return True
                mode = target
                console.print(f"[bold yellow]模式切换 -> {mode.upper()}[/bold yellow]")
                return True
            if command in {"/exit", "/quit"}:
                return False
            console.print(f"[yellow]未知命令: {command}[/yellow]")
            return True

        if route == "quick_chat" and mode == "agent":
            console.print("[green]你好！我已就绪，可以直接描述你的编码任务。[/green]")
            return True

        if mode == "plan":
            await _run_plan_only(user_input, cwd)
            return True

        if mode == "ask":
            await _run_ask_only(user_input)
            return True

        await _run_once(graph, user_input, cwd)
        return True

    if prompt:
        should_continue = await dispatch_request(prompt)
        if not should_continue:
            return
        return

    session = PromptSession(
        history=FileHistory(".agent_history"),
        auto_suggest=AutoSuggestFromHistory(),
        key_bindings=bindings,
    )

    console.print(
        Panel(
            "[bold green]🤖 CodeForge Agent[/bold green]\n"
            "模式: PLAN / ASK / AGENT（按 Shift+Tab 切换）\n"
            "输入 /help 查看命令",
            border_style="green",
        )
    )

    while True:
        try:
            user_input = await session.prompt_async(
                lambda: f"[{mode.upper()}] >>> ",
                multiline=False,
            )
            should_continue = await dispatch_request(user_input)
            if not should_continue:
                break
        except KeyboardInterrupt:
            console.print("\n[yellow]已中断当前任务[/yellow]")
        except EOFError:
            console.print("\n[dim]Bye![/dim]")
            break
