"""Единая точка запуска.

    python -m src.pipeline
    python -m src.pipeline --only synthetic romi
"""
from __future__ import annotations

import argparse
import importlib
import sys


STEPS: list[tuple[str, str, str]] = [
    ("normalize", "src.normalize_sales", "main"),
    ("synthetic", "src.generate_synthetic", "main"),
    ("eda", "src.quick_eda", "main"),
]


def run_step(name: str, module: str, func: str) -> None:
    print(f"[pipeline] → {name}")
    saved_argv = sys.argv.copy()
    sys.argv = [sys.argv[0]]
    try:
        mod = importlib.import_module(module)
        getattr(mod, func)()
        print(f"[pipeline] ✓ {name}")
    finally:
        sys.argv = saved_argv


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    args = ap.parse_args()

    steps = STEPS
    if args.only:
        wanted = set(args.only)
        unknown = wanted - {name for name, _, _ in STEPS}
        if unknown:
            raise SystemExit(
                f"Неизвестные шаги: {', '.join(sorted(unknown))}. "
                f"Доступны: {', '.join(name for name, _, _ in STEPS)}"
            )
        steps = [step for step in STEPS if step[0] in wanted]

    for name, module, func in steps:
        run_step(name, module, func)


if __name__ == "__main__":
    main()
