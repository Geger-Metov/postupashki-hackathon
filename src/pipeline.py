"""Единая точка запуска.

    python -m src.pipeline
    python -m src.pipeline --only synthetic romi
"""
from __future__ import annotations

import argparse
import importlib
import sys


STEPS: list[tuple[str, str, str]] = [
    ("synthetic",   "src.generate_synthetic", "main"),
    ("load_data",   "src.load_data",          "main"),   # Разраб №1
    ("posts",       "src.telegram_collector", "main"),   # опционально
    ("classify",    "src.post_classifier",    "main"),   # опционально
    ("attribution", "src.attribution",        "main"),   # Разраб №1
    ("romi",        "src.romi",               "main"),   # мы
]


def run_step(name: str, module: str, func: str) -> None:
    print(f"[pipeline] → {name}")
    # Сохраняем и обнуляем sys.argv, чтобы подмодули не парсили наши флаги
    saved_argv = sys.argv.copy()
    sys.argv = [sys.argv[0]]
    try:
        mod = importlib.import_module(module)
        getattr(mod, func)()
        print(f"[pipeline] ✓ {name}")
    except ModuleNotFoundError:
        print(f"[pipeline] ⚠ {name} — модуль {module} ещё не готов, пропуск")
    except FileNotFoundError as e:
        print(f"[pipeline] ⚠ {name} — нет данных: {e}")
    except SystemExit:
        print(f"[pipeline] ⚠ {name} — модуль завершился с ошибкой парсинга")
    except Exception as e:
        print(f"[pipeline] ✗ {name} — {e}")
        raise
    finally:
        sys.argv = saved_argv


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    args = ap.parse_args()

    steps = STEPS
    if args.only:
        wanted = set(args.only)
        steps = [s for s in STEPS if s[0] in wanted]

    for name, module, func in steps:
        run_step(name, module, func)


if __name__ == "__main__":
    main()