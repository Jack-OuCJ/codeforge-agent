# CodeForge Agent

一个基于 LangGraph + LangChain 的 CLI 编程智能体，支持：

- 多节点编排（Planner / Executor / Verifier / Replier）
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

