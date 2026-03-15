from __future__ import annotations

import asyncio
import os

from cli.app import main_loop
from cli.parser import build_parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    os.chdir(args.cwd)
    asyncio.run(main_loop(cwd=args.cwd, prompt=args.prompt))


if __name__ == "__main__":
    main()
