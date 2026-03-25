from __future__ import annotations

from typing import Any

from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax


_active_stream_run_id: str = ""
_active_stream_text: str = ""


def _extract_chunk_text(chunk: Any) -> str:
    if chunk is None:
        return ""

    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
        return "".join(parts)

    return str(content) if content is not None else ""


def render_event(event: dict, live: Live) -> None:
    global _active_stream_run_id, _active_stream_text

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
        if not output.strip():
            return
        if "@@" in output or output.startswith("---"):
            live.update(Syntax(output[:3000], "diff", theme="monokai"))
        else:
            live.update(Panel(output[:1000], border_style="blue"))
    elif kind == "on_chat_model_stream":
        chunk = event.get("data", {}).get("chunk")
        run_id = str(event.get("run_id", ""))
        if run_id != _active_stream_run_id:
            _active_stream_run_id = run_id
            _active_stream_text = ""

        content = _extract_chunk_text(chunk)
        if not content:
            return

        _active_stream_text += content
        live.update(Panel(f"[green]{_active_stream_text}[/green]", border_style="green"))
    elif kind == "on_chain_end":
        output = event.get("data", {}).get("output", {})
        final_response = output.get("final_response") if isinstance(output, dict) else None
        if final_response:
            if _active_stream_text and final_response.strip() == _active_stream_text.strip():
                _active_stream_run_id = ""
                _active_stream_text = ""
                return
            live.update(Panel(final_response, border_style="green"))

        _active_stream_run_id = ""
        _active_stream_text = ""
