from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CodeForge CLI 编程智能体")
    parser.add_argument("--cwd", default=".", help="工作目录")
    parser.add_argument("--prompt", default="", help="单次任务模式输入")
    return parser
