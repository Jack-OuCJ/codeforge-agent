from __future__ import annotations

import json
import re
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Input, Label, RichLog, Rule, Static
from rich.text import Text

from agent.graph import build_graph
from agent.llm import get_llm, parse_json_from_text
from agent.prompts.planner_prompt import PLANNER_SYSTEM_PROMPT
from agent.routing import RequestRouter
from config.settings import settings

Mode = Literal["plan", "ask", "agent"]
MODE_ORDER: list[Mode] = ["plan", "ask", "agent"]


class MessageType(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    ERROR = "error"


# ── Helper functions (business logic — unchanged) ────────────────────────────

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


def _remove_think_blocks(text: str) -> str:
    if settings.SHOW_MODEL_THINK:
        return text.strip()
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _split_visible_and_thinking(text: str) -> tuple[str, bool]:
    if settings.SHOW_MODEL_THINK:
        return text, False
    visible: list[str] = []
    pos = 0
    in_thinking = False
    while pos < len(text):
        if not in_thinking:
            start = text.find("<think>", pos)
            if start == -1:
                visible.append(text[pos:])
                break
            visible.append(text[pos:start])
            pos = start + len("<think>")
            in_thinking = True
        else:
            end = text.find("</think>", pos)
            if end == -1:
                pos = len(text)
                break
            pos = end + len("</think>")
            in_thinking = False
    return "".join(visible), in_thinking


def _thinking_placeholder(frame: int) -> str:
    dots = ["", ".", "..", "..."]
    return f"\U0001f914 思考中{dots[frame % len(dots)]}"


def _truncate_tool_output_for_display(output: str) -> str:
    limit = max(settings.TOOL_OUTPUT_DISPLAY_MAX_CHARS, 0)
    if limit and len(output) > limit:
        return output[:limit] + f"\n\n...(输出过长，已截断显示 {len(output) - limit} 字符)"
    return output


def _is_user_visible_stream_event(event: dict[str, Any]) -> bool:
    if settings.SHOW_DEBUG_STREAM:
        return True
    metadata = event.get("metadata", {}) or {}
    node_name = str(
        metadata.get("langgraph_node")
        or metadata.get("graph_node")
        or metadata.get("node_name")
        or ""
    ).lower()
    if node_name:
        return "executor" in node_name
    event_name = str(event.get("name", "")).lower()
    return "executor" in event_name or "chat_model" in event_name


def _extract_final_response_from_state_output(output: dict[str, Any]) -> str:
    messages = output.get("messages") or []
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            continue
        msg_type = str(getattr(message, "type", "")).lower()
        if msg_type and msg_type not in {"ai", "assistant"}:
            continue
        content = getattr(message, "content", "")
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text_piece = item.get("text") or item.get("content")
                    if text_piece:
                        parts.append(str(text_piece))
            text = "\n".join(parts).strip()
        else:
            text = str(content).strip()
        if text:
            return text
    return ""


def _next_mode(current_mode: Mode) -> Mode:
    index = MODE_ORDER.index(current_mode)
    return MODE_ORDER[(index + 1) % len(MODE_ORDER)]


def _build_initial_state(user_input: str, cwd: str) -> dict:
    return {
        "messages": [HumanMessage(content=user_input)],
        "cwd": str(Path(cwd).resolve()),
    }


# ── Session history ───────────────────────────────────────────────────────────

class SessionHistoryStore:
    def __init__(self, base_dir: Path, max_sessions: int = 10) -> None:
        self.base_dir = base_dir
        self.max_sessions = max_sessions
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.thread_id: str = ""
        self.created_at: str = ""
        self.first_question: str = ""
        self.title: str = ""
        self.session_file: Path | None = None

    def start_new_thread(self, thread_id: str) -> None:
        self.thread_id = thread_id
        self.created_at = self._now_iso()
        self.first_question = ""
        self.title = ""
        self.session_file = None

    def capture_first_question(self, question: str) -> None:
        if self.first_question:
            return
        cleaned = question.strip()
        if not cleaned:
            return
        self.first_question = cleaned
        self.title = self._sanitize_title(cleaned)
        self._ensure_session_file()

    def save_messages(self, messages: list[dict]) -> None:
        if not self.thread_id or not self.first_question:
            return
        self._ensure_session_file()
        if self.session_file is None:
            return
        payload = {
            "thread_id": self.thread_id,
            "title": self.title,
            "first_question": self.first_question,
            "created_at": self.created_at,
            "updated_at": self._now_iso(),
            "messages": messages,
        }
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        self.session_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._prune_old_sessions()

    def list_sessions(self, limit: int = 10) -> list[dict[str, str]]:
        sessions: list[dict[str, str]] = []
        for path in self.base_dir.glob("**/*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            updated_at = str(data.get("updated_at") or "")
            sessions.append(
                {
                    "thread_id": str(data.get("thread_id") or ""),
                    "title": str(data.get("title") or path.stem),
                    "first_question": str(data.get("first_question") or ""),
                    "created_at": str(data.get("created_at") or ""),
                    "updated_at": updated_at,
                    "date": path.parent.name,
                    "path": str(path.relative_to(self.base_dir.parent)),
                    "_sort": str(self._sort_key(updated_at, path)),
                }
            )
        sessions.sort(key=lambda item: item.get("_sort", ""), reverse=True)
        return sessions[:limit]

    def _ensure_session_file(self) -> None:
        if self.session_file is not None:
            return
        if not self.thread_id:
            self.start_new_thread(uuid4().hex)
        if not self.created_at:
            self.created_at = self._now_iso()
        date_key = self.created_at[:10]
        date_dir = self.base_dir / date_key
        date_dir.mkdir(parents=True, exist_ok=True)
        title = self.title or "session"
        file_name = f"{title}__{self.thread_id[:8]}.json"
        self.session_file = date_dir / file_name

    def _prune_old_sessions(self) -> None:
        all_sessions: list[tuple[float, Path]] = []
        for path in self.base_dir.glob("**/*.json"):
            timestamp = self._sort_key(None, path)
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                timestamp = self._sort_key(str(data.get("updated_at") or ""), path)
            except Exception:
                pass
            all_sessions.append((timestamp, path))
        if len(all_sessions) <= self.max_sessions:
            return
        all_sessions.sort(key=lambda item: item[0])
        for _, path in all_sessions[: len(all_sessions) - self.max_sessions]:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                continue

    @staticmethod
    def _sanitize_title(text: str, max_len: int = 40) -> str:
        value = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", text)
        value = re.sub(r"\s+", "_", value).strip(" ._")
        if not value:
            value = "session"
        return value[:max_len]

    @staticmethod
    def _sort_key(iso_time: str | None, path: Path) -> float:
        if iso_time:
            try:
                return datetime.fromisoformat(iso_time).timestamp()
            except ValueError:
                pass
        return path.stat().st_mtime

    @staticmethod
    def _now_iso() -> str:
        return datetime.now().isoformat(timespec="seconds")


# ── Textual CSS ───────────────────────────────────────────────────────────────

APP_CSS = """
Screen {
    background: #1e1e2e;
}

#status_bar {
    height: 1;
    background: #181825;
    color: #cdd6f4;
    content-align: left middle;
    padding: 0 2;
    dock: top;
}

#chat_log {
    height: 1fr;
    background: #1e1e2e;
    scrollbar-color: #585b70;
    scrollbar-background: #313244;
    padding: 0 1;
}

#stream_widget {
    height: auto;
    background: #1e1e2e;
    color: #cdd6f4;
    padding: 0 1;
}

#separator {
    background: #313244;
    color: #585b70;
    margin: 0;
}

#input_bar {
    height: 3;
    background: #313244;
    border: tall #585b70;
    padding: 0 1;
}

#mode_label {
    width: auto;
    content-align: left middle;
    color: #00ccff;
    padding: 0 1 0 0;
}

Input {
    background: #313244;
    color: #cdd6f4;
    border: none;
    height: 1;
}

Input:focus {
    border: none;
}

#help_bar {
    height: 1;
    background: #181825;
    color: #585b70;
    content-align: left middle;
    padding: 0 2;
    dock: bottom;
}
"""


# ── Textual Application ───────────────────────────────────────────────────────

class CodeForgeApp(App[None]):
    """CodeForge Agent — TUI powered by Textual.

    Rendering highlights:
    * ENABLE_SYNCHRONIZED_OUTPUT = True  — DEC mode 2026 synchronized output.
      Wraps each frame in BSU/ESU sequences so the terminal composites the
      entire frame atomically, eliminating tearing and flickering.
    * Textual renders to an off-screen back-buffer and diffs against the
      front-buffer before emitting ANSI sequences (double-buffering + blit).
    * Streaming uses a dedicated Static widget updated from an
      @work(exclusive=True) async coroutine.  Textual's event loop yields
      between awaits so keyboard/mouse events remain responsive during
      long model generations.
    * Memoization: reactive `mode` variable drives label re-renders only when
      the value changes; RichLog only repaints rows that actually changed.
    """

    ENABLE_SYNCHRONIZED_OUTPUT = True   # DEC mode 2026

    CSS = APP_CSS
    TITLE = "CodeForge Agent"

    BINDINGS = [
        Binding("shift+tab", "switch_mode", "切换模式", show=False),
        Binding("escape,tab", "switch_mode", "切换模式", show=False),
        Binding("ctrl+c", "quit_or_cancel", "退出", show=False, priority=True),
    ]

    mode: reactive[Mode] = reactive("agent")

    def __init__(self, cwd: str = ".", prompt_text: str = "") -> None:
        super().__init__()
        self.cwd = cwd
        self.prompt_text = prompt_text
        self.graph = None
        self.router: RequestRouter | None = None
        self.history_store: SessionHistoryStore | None = None
        self.conversation_thread_id: str = ""
        self._session_messages: list[dict] = []
        self._streaming_raw_buffer: str = ""
        self._thinking_frame: int = 0
        self._ctrl_c_count: int = 0
        self._last_ctrl_c_time: float = 0.0

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Static(self._status_text(), id="status_bar")
        yield RichLog(
            id="chat_log",
            markup=False,
            highlight=False,
            wrap=True,
            auto_scroll=True,
        )
        # Back-buffer for the in-flight streaming response.
        # Committed to chat_log (front-buffer blit) when generation ends.
        yield Static("", id="stream_widget")
        yield Rule(id="separator")
        with Horizontal(id="input_bar"):
            yield Label("[AGENT] >> ", id="mode_label")
            yield Input(placeholder="输入任务或命令 (/help)", id="user_input")
        yield Static(
            "  /help /history /clear /mode /model /provider /exit"
            "   Shift+Tab:切换模式  PgUp/PgDn:滚动  Ctrl+C\xd7 2:退出",
            id="help_bar",
        )

    def _status_text(self) -> str:
        provider = settings.LLM_PROVIDER.upper()
        model = (
            settings.MINIMAX_MODEL
            if settings.LLM_PROVIDER == "minimax"
            else settings.DASHSCOPE_MODEL
        )
        return (
            f"  CodeForge Agent  \u2502  Provider: {provider}"
            f"  \u2502  Model: {model}  \u2502  Shift+Tab: 切换模式"
        )

    async def on_mount(self) -> None:
        self.graph = build_graph()
        self.router = RequestRouter.from_name(settings.ROUTER_NAME)
        cwd_path = Path(self.cwd).resolve()
        self.history_store = SessionHistoryStore(
            base_dir=cwd_path / "history", max_sessions=10
        )
        self.conversation_thread_id = uuid4().hex
        self.history_store.start_new_thread(self.conversation_thread_id)
        self._log_system("欢迎使用 CodeForge Agent！输入 /help 查看帮助。")
        self.query_one("#user_input", Input).focus()
        if self.prompt_text:
            await self.process_input(self.prompt_text)
            self.exit()

    # ── Reactive watchers ─────────────────────────────────────────────────────

    def watch_mode(self, new_mode: Mode) -> None:
        try:
            self.query_one("#mode_label", Label).update(f"[{new_mode.upper()}] >> ")
        except Exception:
            pass

    # ── Logging helpers ───────────────────────────────────────────────────────

    def _make_rich_text(self, msg_type: MessageType, content: str) -> Text:
        text = Text(no_wrap=False)
        text.append("\n")
        if msg_type == MessageType.USER:
            for line in content.split("\n"):
                text.append(f">> {line}\n", style="#00ccff")
        elif msg_type == MessageType.ASSISTANT:
            for line in content.split("\n"):
                text.append(f":: {line}\n", style="#cdd6f4")
        elif msg_type == MessageType.SYSTEM:
            for line in content.split("\n"):
                text.append(f"*  {line}\n", style="italic #a6adc8")
        elif msg_type == MessageType.TOOL:
            for line in content.split("\n"):
                text.append(f"+  {line}\n", style="#89b4fa")
        elif msg_type == MessageType.ERROR:
            for line in content.split("\n"):
                text.append(f"!  {line}\n", style="bold #f38ba8")
        return text

    def _log(self, msg_type: MessageType, content: str) -> None:
        self._session_messages.append({"type": msg_type.value, "content": content})
        try:
            self.query_one("#chat_log", RichLog).write(
                self._make_rich_text(msg_type, content)
            )
        except Exception:
            pass

    def _log_user(self, c: str) -> None:
        self._log(MessageType.USER, c)

    def _log_assistant(self, c: str) -> None:
        self._log(MessageType.ASSISTANT, c)

    def _log_system(self, c: str) -> None:
        self._log(MessageType.SYSTEM, c)

    def _log_tool(self, c: str) -> None:
        self._log(MessageType.TOOL, c)

    def _log_error(self, c: str) -> None:
        self._log(MessageType.ERROR, c)

    # ── Streaming double-buffer helpers ───────────────────────────────────────

    def _update_stream(self, content: str) -> None:
        """Update the live streaming back-buffer widget."""
        try:
            widget = self.query_one("#stream_widget", Static)
            if content:
                text = Text(no_wrap=False)
                for line in content.split("\n"):
                    text.append(f":: {line}\n", style="#cdd6f4")
                widget.update(text)
            else:
                widget.update("")
        except Exception:
            pass

    def _commit_stream(self, content: str) -> None:
        """Blit the streaming back-buffer to the permanent front-buffer log."""
        if content.strip():
            self._log_assistant(content)
        self._update_stream("")

    def _persist_session(self) -> None:
        if self.history_store:
            self.history_store.save_messages(self._session_messages)

    # ── Key actions ───────────────────────────────────────────────────────────

    def action_switch_mode(self) -> None:
        self.mode = _next_mode(self.mode)

    def action_quit_or_cancel(self) -> None:
        now = time.monotonic()
        if now - self._last_ctrl_c_time < 1.0:
            self._ctrl_c_count += 1
        else:
            self._ctrl_c_count = 1
        self._last_ctrl_c_time = now
        if self._ctrl_c_count >= 2:
            self.exit()
        else:
            try:
                self._log_system("再按一次 Ctrl+C 退出")
            except Exception:
                pass

    # ── Input handler ─────────────────────────────────────────────────────────

    @on(Input.Submitted, "#user_input")
    async def _on_user_input(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.clear()
        if text:
            await self.process_input(text)

    # ── Core: process input ───────────────────────────────────────────────────

    async def process_input(self, user_input: str) -> None:
        if not user_input.strip():
            return
        self._log_user(user_input)
        if self.router is None:
            return
        route = self.router.select_route(user_input)
        if route == "empty":
            return
        if route != "command" and self.history_store:
            self.history_store.capture_first_question(user_input)
        if route == "command":
            await self._handle_command(user_input)
            return
        if route == "quick_chat" and self.mode == "agent":
            self._log_assistant("你好！我已就绪，可以直接描述你的编码任务。")
            self._persist_session()
            return
        if self.mode == "plan":
            await self._run_plan_only(user_input)
            self._persist_session()
            return
        if self.mode == "ask":
            await self._run_ask_only(user_input)
            self._persist_session()
            return
        self._do_stream(user_input)

    # ── Streaming worker ──────────────────────────────────────────────────────

    @work(exclusive=True)
    async def _do_stream(self, user_input: str) -> None:
        await self._stream_response(user_input)
        self._log_system("\u2705 任务完成")
        self._persist_session()

    async def _stream_response(self, user_input: str) -> None:
        if self.graph is None:
            return
        thread_config = {"configurable": {"thread_id": self.conversation_thread_id}}
        self._streaming_raw_buffer = ""
        self._thinking_frame = 0
        self._update_stream(_thinking_placeholder(self._thinking_frame))

        try:
            async for event in self.graph.astream_events(
                _build_initial_state(user_input, self.cwd),
                config=thread_config,
                version="v2",
            ):
                kind = event.get("event", "")

                if kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    tool_input = event.get("data", {}).get("input", {})
                    self._log_tool(
                        f"\u2699 调用工具: {tool_name}\n{str(tool_input)[:300]}"
                    )

                elif kind == "on_tool_end":
                    output = str(event.get("data", {}).get("output", ""))
                    if output.strip():
                        self._log_tool(
                            f"\u2713 结果:\n{_truncate_tool_output_for_display(output)}"
                        )

                elif kind == "on_chat_model_stream":
                    if not _is_user_visible_stream_event(event):
                        continue
                    chunk = event.get("data", {}).get("chunk")
                    content = _extract_chunk_text(chunk)
                    if content:
                        self._streaming_raw_buffer += content
                        visible, is_thinking = _split_visible_and_thinking(
                            self._streaming_raw_buffer
                        )
                        display = visible
                        if is_thinking:
                            self._thinking_frame += 1
                            if display and not display.endswith("\n"):
                                display += "\n"
                            display += _thinking_placeholder(self._thinking_frame)
                        self._update_stream(display)

                elif kind == "on_chain_end":
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict):
                        fr = output.get("final_response")
                        if fr:
                            cleaned = _remove_think_blocks(str(fr))
                        else:
                            cleaned = _remove_think_blocks(
                                _extract_final_response_from_state_output(output)
                            )
                        if cleaned:
                            self._commit_stream(cleaned)

        except Exception as exc:
            msg = str(exc)
            if "Arrearage" in msg:
                friendly = "模型服务不可用（账户欠费/权限问题），请检查百炼账户后重试。"
            elif msg.strip() in {"'request'", '"request"'}:
                friendly = "模型调用失败：请求参数或配置异常，请检查模型名与账号权限。"
            else:
                friendly = f"模型调用失败：{msg[:200]}"
            self._update_stream("")
            self._log_error(friendly)
            return

        if self._streaming_raw_buffer:
            visible, _ = _split_visible_and_thinking(self._streaming_raw_buffer)
            cleaned = _remove_think_blocks(visible)
            if cleaned:
                self._commit_stream(cleaned)
            else:
                self._update_stream("")
        else:
            self._update_stream("")

        self._streaming_raw_buffer = ""
        self._thinking_frame = 0

    # ── Command handler ───────────────────────────────────────────────────────

    async def _handle_command(self, raw: str) -> None:
        parts = raw.strip().split()
        command = parts[0]

        if command == "/help":
            self._log_system(
                "可用命令:\n"
                "  /help                          显示帮助\n"
                "  /history                       查看会话历史（最近10条）\n"
                "  /clear                         清空聊天历史\n"
                "  /mode [plan|ask|agent]         切换模式\n"
                "  /model                         显示当前模型\n"
                "  /provider [dashscope|minimax]  切换 provider\n"
                "  /exit                          退出\n"
                "\n"
                "快捷键:\n"
                "  Shift+Tab    循环切换模式\n"
                "  PgUp/PgDn    翻页滚动\n"
                "  Ctrl+C\xd72  强制退出\n"
            )
            self._persist_session()
            return

        if command == "/history":
            if self.history_store:
                sessions = self.history_store.list_sessions(limit=10)
                if not sessions:
                    self._log_system("暂无历史会话记录")
                    return
                lines = ["最近会话记录（按最近更新时间倒序）:"]
                for i, item in enumerate(sessions, 1):
                    lines.append(
                        f"  {i}. [{item['date']}] {item['title']}"
                        f" | thread={item['thread_id'][:8]}"
                        f" | updated={item['updated_at']}"
                    )
                self._log_system("\n".join(lines))
            return

        if command == "/clear":
            self._session_messages.clear()
            self.conversation_thread_id = uuid4().hex
            if self.history_store:
                self.history_store.start_new_thread(self.conversation_thread_id)
            self.query_one("#chat_log", RichLog).clear()
            self._log_system("聊天历史已清空")
            return

        if command == "/model":
            current = (
                settings.MINIMAX_MODEL
                if settings.LLM_PROVIDER == "minimax"
                else settings.DASHSCOPE_MODEL
            )
            self._log_system(f"当前模型: {current}\n请修改 .env 配置切换模型")
            self._persist_session()
            return

        if command == "/provider":
            if len(parts) == 1:
                self._log_system(
                    f"当前 Provider: {settings.LLM_PROVIDER}\n可用: dashscope / minimax"
                )
                self._persist_session()
                return
            target = parts[1].lower()
            if target not in {"dashscope", "minimax"}:
                self._log_error("可用 Provider: dashscope / minimax")
                return
            settings.LLM_PROVIDER = target
            model_name = (
                settings.MINIMAX_MODEL if target == "minimax" else settings.DASHSCOPE_MODEL
            )
            self._log_system(f"Provider 已切换 -> {target}\n当前模型: {model_name}")
            self.query_one("#status_bar", Static).update(self._status_text())
            self._persist_session()
            return

        if command == "/mode":
            if len(parts) == 1:
                self._log_system(f"当前模式: {self.mode.upper()}")
                self._persist_session()
                return
            target = parts[1].lower()
            if target not in {"plan", "ask", "agent"}:
                self._log_error("可用模式: plan / ask / agent")
                return
            self.mode = target  # type: ignore[assignment]
            self._log_system(f"模式切换 -> {self.mode.upper()}")
            self._persist_session()
            return

        if command in {"/exit", "/quit"}:
            self._log_system("再见!")
            self._persist_session()
            self.exit()
            return

        self._log_error(f"未知命令: {command}")
        self._persist_session()

    # ── Plan / Ask modes ──────────────────────────────────────────────────────

    async def _run_plan_only(self, user_input: str) -> None:
        self._log_system(f"PLAN 模式 - 工作目录: {Path(self.cwd).resolve()}")
        llm = get_llm(temperature=0)
        prompt = (
            "你现在处于 PLAN 模式。仅生成可执行计划，不要调用工具，不要假装执行。\n\n"
            f"工作目录: {Path(self.cwd).resolve()}\n"
            f"用户请求: {user_input}\n\n"
            '请输出 JSON：\n{{\n  "goal": "目标描述",\n  "steps": ["步骤1", "步骤2"]\n}}'
        )
        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(content=PLANNER_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
            )
            parsed = parse_json_from_text(response.content)
            goal = parsed.get("goal", "")
            steps = parsed.get("steps", [])
            body = f"目标: {goal}\n\n步骤:\n" + "".join(
                f"  {i}. {s}\n" for i, s in enumerate(steps, 1)
            )
            self._log_assistant(body)
        except Exception as exc:
            self._log_error(f"计划生成失败: {exc}")

    async def _run_ask_only(self, user_input: str) -> None:
        self._log_system("ASK 模式 - 仅回答问题")
        llm = get_llm()
        try:
            response = await llm.ainvoke(
                [
                    SystemMessage(
                        content="你处于 ASK 模式。只回答问题，不调用工具，不给出虚假执行结果。"
                    ),
                    HumanMessage(content=user_input),
                ]
            )
            self._log_assistant(_remove_think_blocks(str(response.content)))
        except Exception as exc:
            self._log_error(f"回答失败: {exc}")


# ── Entry point ───────────────────────────────────────────────────────────────

async def main_loop(cwd: str = ".", prompt: str = "") -> None:
    app = CodeForgeApp(cwd=cwd, prompt_text=prompt)
    await app.run_async()
