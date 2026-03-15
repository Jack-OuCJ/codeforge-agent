# CodeForge Agent

一个基于 LangGraph + LangChain 的 CLI 编程智能体，支持：

- 多节点编排（Planner / Executor / Verifier / Replier）
- 路由层分发（command / quick_chat / agent_graph）
- 三种工作模式（PLAN / ASK / AGENT）
- 工具调用（Shell、读写编辑文件、搜索、Patch、测试）
- 阿里百炼 RAG 检索工具
- 交互式 CLI 与单次任务模式

## 安装

```bash
pip install -e .
```

## 配置

```bash
cp config/.env.example .env
```

填写 `.env`：

- `DASHSCOPE_API_KEY`（或使用 `OPENAI_API_KEY` 兜底）
- `BAILIAN_APP_ID`
- `BAILIAN_PIPELINE_ID`
- `ROUTER_NAME`（默认 `rule_based_router`）

## 运行

交互模式：

```bash
python main.py
```

指定工作目录：

```bash
python main.py --cwd /path/to/project
```

单次任务：

```bash
python main.py --prompt "给 src/utils.py 添加单元测试"
```

## 交互模式切换

- 在终端中按 `Shift+Tab` 循环切换：`PLAN -> ASK -> AGENT`
- 也可用命令：`/mode plan`、`/mode ask`、`/mode agent`

模式语义：

- `PLAN`：只生成执行计划，不调用工具、不改代码
- `ASK`：只回答问题，不执行工具
- `AGENT`：按智能体流程执行，可调用工具并修改代码

