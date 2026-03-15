from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.live import Live
from rich.panel import Panel

from agent.graph import build_graph
from cli.display import render_event


console = Console()


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


async def main_loop(cwd: str = ".", prompt: str = "") -> None:
    graph = build_graph()

    if prompt:
        await _run_once(graph, prompt, cwd)
        return

    session = PromptSession(
        history=FileHistory(".agent_history"),
        auto_suggest=AutoSuggestFromHistory(),
    )

    console.print(Panel("[bold green]🤖 CodeForge Agent[/bold green] - 输入 /help 查看命令", border_style="green"))

    while True:
        try:
            user_input = await session.prompt_async(">>> ", multiline=False)
            if not user_input.strip():
                continue

            if user_input.startswith("/"):
                command = user_input.strip().split()[0]
                if command == "/help":
                    console.print("/help /clear /exit")
                    continue
                if command == "/clear":
                    console.clear()
                    continue
                if command in {"/exit", "/quit"}:
                    break

            await _run_once(graph, user_input, cwd)
        except KeyboardInterrupt:
            console.print("\n[yellow]已中断当前任务[/yellow]")
        except EOFError:
            console.print("\n[dim]Bye![/dim]")
            break
