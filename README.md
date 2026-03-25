# CodeForge Agent

一个基于 LangGraph + LangChain 的 CLI 编程智能体，对标 Claude Code / OpenHands，支持：

- 多节点编排（Planner / Executor）
- 路由层分发（command / quick_chat / agent_graph）
- 三种工作模式（PLAN / ASK / AGENT）
- 工具调用（Shell、读写编辑文件、搜索、Patch、测试）
- 阿里百炼 RAG 检索工具
- 交互式 CLI 与单次任务模式

---

## 快速开始（推荐：uv）

### 1. 安装 uv

如果尚未安装 [uv](https://docs.astral.sh/uv/)：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 克隆仓库

```bash
git clone https://github.com/Jack-OuCJ/codeforge-agent.git
cd codeforge-agent
```

### 3. 安装为全局 CLI 命令（推荐）

```bash
uv tool install .
```

安装完成后，`codeforge-agent` 命令即可在系统任意位置使用：

```bash
codeforge-agent
```

> 如果提示命令未找到，执行 `uv tool update-shell` 并重启终端，或手动将 `~/.local/bin` 添加到 `PATH`。

---

## 配置环境变量

全局安装后，程序会按以下顺序查找配置：

1. **当前工作目录**下的 `.env` 文件
2. **Shell 环境变量**（适合全局命令使用）

### 方式一：项目目录 `.env`（推荐本地开发）

```bash
cp config/.env.example .env
# 用编辑器打开 .env，填入你的 API Key 等配置
```

### 方式二：Shell 环境变量（推荐全局命令使用）

在 `~/.zshrc` 或 `~/.bashrc` 中添加：

```bash
export DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
export LLM_PROVIDER=dashscope
export DASHSCOPE_MODEL=qwen-max
# 其他配置项按需添加（参见下表）
```

保存后执行：

```bash
source ~/.zshrc
```

### 关键配置项说明

| 配置项 | 必填 | 默认值 | 说明 |
|--------|:----:|--------|------|
| `DASHSCOPE_API_KEY` | ✅ | — | 阿里百炼 API Key，[前往控制台获取](https://bailian.console.aliyun.com/) |
| `LLM_PROVIDER` | | `dashscope` | 模型提供商：`dashscope` 或 `minimax` |
| `DASHSCOPE_MODEL` | | `qwen-max` | 主力模型名（须为百炼支持的有效名称） |
| `DASHSCOPE_FAST` | | `qwen-turbo` | 轻量/快速模型 |
| `BAILIAN_COMPATIBLE_BASE_URL` | | `https://dashscope.aliyuncs.com/compatible-mode/v1` | 百炼 OpenAI 兼容接口地址 |
| `MINIMAX_API_KEY` | | — | 使用 MiniMax 时填写 |
| `MINIMAX_MODEL` | | `MiniMax-M2.7` | MiniMax 主模型 |
| `TEMPERATURE` | | `0.0` | 模型温度（越低越确定性） |
| `MAX_TOKENS` | | `0` | 单次生成 token 上限，`0` 表示由服务端决定 |
| `MAX_ITERATIONS` | | `20` | 智能体最大执行迭代次数 |
| `SHOW_DEBUG_STREAM` | | `false` | 显示规划/执行节点的中间流式输出 |
| `SHOW_MODEL_THINK` | | `false` | 显示模型 `<think>` 思考过程 |
| `TOOL_OUTPUT_DISPLAY_MAX_CHARS` | | `0` | CLI 工具输出最大显示字符数，`0` 不截断 |
| `TOOL_OUTPUT_MODEL_MAX_CHARS` | | `0` | 工具结果回传模型的最大字符数，`0` 不截断 |

完整配置模板见 [config/.env.example](config/.env.example)。

## 使用

### 交互模式

```bash
codeforge-agent
```

### 指定工作目录

```bash
codeforge-agent --cwd /path/to/your/project
```

### 单次任务（非交互）

```bash
codeforge-agent --prompt "给 src/utils.py 添加单元测试"
```

---

## 交互命令

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助 |
| `/clear` | 清屏 |
| `/mode [plan\|ask\|agent]` | 切换工作模式 |
| `/model` | 交互式选择模型 |
| `/provider [dashscope\|minimax]` | 切换 LLM Provider |
| `/history` | 查看最近会话记录 |
| `/exit` | 退出 |

按 `Shift+Tab` 可在 `PLAN → ASK → AGENT` 三种模式间循环切换。

**模式说明：**

| 模式 | 行为 |
|------|------|
| `PLAN` | 只生成执行计划，不调用工具、不改代码 |
| `ASK` | 只回答问题，不执行工具 |
| `AGENT` | 完整智能体，可调用工具读写代码 |

---

## 本地开发

```bash
# 克隆后同步依赖（会自动创建 .venv）
uv sync

# 直接运行，无需全局安装
uv run python main.py

# 运行测试
uv run pytest
```

---

## 会话历史

- 每次启动生成新的 `thread_id`，会话记录以 JSON 形式保存至 `history/YYYY-MM-DD/` 目录。
- 文件名由首条用户输入生成，附加 thread 短 ID。
- 最多保留 10 个会话文件，超过后自动删除最旧记录。
- CLI 中输入 `/history` 可查看最近记录。

---

## 技术架构

```
CLI 入口 (cli/app.py)
  └─→ 路由层 (agent/routing/)
        └─→ LangGraph 编排 (agent/graph.py)
              ├─ Planner 节点：理解意图 + RAG 检索 + 生成 TaskPlan
              └─ Executor 节点：ReAct 模式 + 工具调用

工具层 (tools/)：bash、文件读写编辑、glob/grep 搜索、patch、测试执行
```

---

## License

MIT
