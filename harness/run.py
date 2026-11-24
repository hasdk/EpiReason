"""Run the EpiReason tasks for one or more models and print a summary with token use.

    uv run python -m harness.run --items items/dev --models anthropic/claude-haiku-5-5 deepseek/deepseek-flash \
        --grader deepseek/deepseek-v4-pro --epochs 3

Families with no items in the folder are skipped. Logs go to logs/ (git-ignored).
"""
from __future__ import annotations

import argparse

from dotenv import load_dotenv
from inspect_ai import eval

from harness.schema import load_items
from harness.task import family_a, family_b, family_c

TASKS = {"A": family_a, "B": family_b, "C": family_c}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--items", default="items/dev")
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--grader", required=True, help="judge model for family A")
    parser.add_argument("--epochs", type=int, default=1, help="samples per prompt")
    parser.add_argument("--families", default="ABC")
    parser.add_argument("--log-dir", default="logs")
    parser.add_argument("--levels", default="neutral,direct", help="family A hint levels, comma-separated")
    args = parser.parse_args()
    load_dotenv()

    present = {item.get("family") for item in load_items(args.items)}
    tasks = [TASKS[f](items_dir=args.items, **({"levels": args.levels} if f == "A" else {}))
             for f in args.families if f in present]
    if not tasks:
        raise SystemExit(f"no items for families {args.families} in {args.items}")

    logs = eval(tasks, model=args.models, model_roles={"grader": args.grader},
                epochs=args.epochs, log_dir=args.log_dir, display="none")

    for log in logs:
        scores = [s.scores[next(iter(s.scores))].value for s in (log.samples or []) if s.scores]
        graded = [v for v in scores if isinstance(v, (int, float)) and v == v]
        mean = sum(graded) / len(graded) if graded else float("nan")
        print(f"{log.eval.task:<10} {log.eval.model:<34} {log.status:<8} "
              f"responses={len(scores)} graded={len(graded)} mean={mean:.2f}")
        for model, usage in (log.stats.model_usage or {}).items():
            print(f"{'':<10} tokens {model:<34} in={usage.input_tokens} out={usage.output_tokens}")
        if log.error:
            print(f"{'':<10} error: {str(log.error.message)[:300]}")


if __name__ == "__main__":
    main()
