"""
End-to-end MVP pipeline.

Запуск:
    python -m src.pipeline

Отдельные шаги:
    python -m src.pipeline --only normalize synthetic
"""

from __future__ import annotations

import argparse
import subprocess
import sys


STEPS = [
    ("normalize", ["-m", "src.normalize_sales"]),
    ("identity_map", ["-m", "src.build_identity_map"]),
    ("synthetic", ["-m", "src.generate_synthetic"]),
    ("eda", ["-m", "src.quick_eda"]),
    ("attribution", ["-m", "src.attribution"]),
    ("romi", ["-m", "src.romi"]),
    ("budget", ["-m", "src.budget_recommendation"]),
    ("forecast", ["-m", "src.forecast"]),
]


def run_step(name: str, command: list[str]) -> None:
    print(f"\n[pipeline] → {name}")

    result = subprocess.run(
        [sys.executable, *command],
        check=False,
    )

    if result.returncode != 0:
        raise SystemExit(
            f"[pipeline] ✗ {name} failed "
            f"(exit code {result.returncode})"
        )

    print(f"[pipeline] ✓ {name}")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Например: --only normalize attribution romi",
    )

    args = parser.parse_args()

    if args.only:
        available = {name for name, _ in STEPS}
        unknown = set(args.only) - available

        if unknown:
            raise SystemExit(
                f"Неизвестные шаги: {', '.join(sorted(unknown))}\n"
                f"Доступны: {', '.join(available)}"
            )

        selected = [
            step for step in STEPS
            if step[0] in set(args.only)
        ]
    else:
        selected = STEPS

    for name, command in selected:
        run_step(name, command)

    print("\n[pipeline] ✓ ALL STEPS COMPLETED")


if __name__ == "__main__":
    main()
