from __future__ import annotations

from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax


def render_event(event: dict, live: Live) -> None:
    kind = event.get("event", "")

    if kind == "on_tool_start":
        tool_name = event.get("name", "")
        tool_input = event.get("data", {}).get("input", {})
        live.update(
            Panel(
                f"[cyan]⚙ 调用工具: {tool_name}[/cyan]\n{str(tool_input)[:300]}",
                border_style="cyan",
            )
        )
    elif kind == "on_tool_end":
        output = str(event.get("data", {}).get("output", ""))
        if "@@" in output or output.startswith("---"):
            live.update(Syntax(output[:3000], "diff", theme="monokai"))
        else:
            live.update(Panel(output[:1000], border_style="blue"))
    elif kind == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk")
        content = getattr(chunk, "content", "") if chunk else ""
        live.update(Panel(f"[green]{content}[/green]", border_style="green"))
    elif kind == "on_chain_end":
        output = event.get("data", {}).get("output", {})
        final_response = output.get("final_response") if isinstance(output, dict) else None
        if final_response:
            live.update(Panel(final_response, border_style="green"))
