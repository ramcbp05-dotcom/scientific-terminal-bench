"""Command line entry point: ``stbench`` (or ``python -m harness.cli``)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import models, runner

TASKS_DIR = runner.REPO_ROOT / "tasks"


def _load(selected: list[str] | None) -> list[models.TaskSpec]:
    specs = models.discover(TASKS_DIR)
    if not selected:
        return specs
    by_id = {s.task_id: s for s in specs}
    missing = [t for t in selected if t not in by_id]
    if missing:
        raise SystemExit(f"unknown task id(s): {missing}\navailable: {sorted(by_id)}")
    return [by_id[t] for t in selected]


def cmd_list(args: argparse.Namespace) -> int:
    specs = _load(None)
    width = max(len(s.task_id) for s in specs)
    print(f"{'TASK'.ljust(width)}  DIFF    TAGS")
    for spec in specs:
        print(f"{spec.task_id.ljust(width)}  {spec.difficulty:<6}  {','.join(spec.tags)}")
    print(f"\n{len(specs)} tasks "
          f"({sum(s.difficulty == 'easy' for s in specs)} easy / "
          f"{sum(s.difficulty == 'medium' for s in specs)} medium / "
          f"{sum(s.difficulty == 'hard' for s in specs)} hard)")
    return 0


def cmd_instructions(args: argparse.Namespace) -> int:
    for spec in _load(args.task):
        print(spec.instructions_path.read_text())
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    specs = _load(None)
    print(f"ok: {len(specs)} task directories satisfy the layout contract")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    specs = _load(args.task)
    results: list[runner.RunResult] = []
    for spec in specs:
        for mode in args.mode:
            res = runner.run_task(
                spec, mode=mode, backend=args.backend, seed=args.seed,
                agent_cmd=args.agent_cmd,
            )
            flag = "OK " if res.calibrated else "BAD"
            verdict = "pass" if res.passed else "fail"
            print(f"[{flag}] {spec.task_id:<32} {mode:<9} {verdict:<4} "
                  f"{res.duration_sec:>6.2f}s  seed={res.seed}")
            if not res.calibrated:
                print(f"       expected {'pass' if res.expected_pass else 'fail'}; "
                      f"log: {res.run_dir}/run.log")
            results.append(res)

    summary = runner.summarise(results)
    print(f"\n{summary['passed']}/{summary['total']} verifier passes, "
          f"{summary['calibrated']}/{summary['total']} calibrated as expected")
    if args.report:
        report = Path(args.report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(summary, indent=2) + "\n")
        print(f"report written to {report}")
    return 0 if summary["calibrated"] == summary["total"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stbench", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list all tasks").set_defaults(func=cmd_list)
    sub.add_parser("validate", help="check every task directory").set_defaults(func=cmd_validate)

    p_instr = sub.add_parser("instructions", help="print the agent-visible prompt")
    p_instr.add_argument("task", nargs="+")
    p_instr.set_defaults(func=cmd_instructions)

    p_run = sub.add_parser("run", help="run tasks in a sandbox and verify")
    p_run.add_argument("-t", "--task", action="append", help="task id (repeatable; default all)")
    p_run.add_argument("-m", "--mode", action="append", choices=runner.MODES,
                       help="run mode (repeatable; default oracle)")
    p_run.add_argument("-b", "--backend", choices=runner.BACKENDS, default="local")
    p_run.add_argument("--seed", type=int, default=None,
                       help="fix the verifier seed (debugging only)")
    p_run.add_argument("--agent-cmd", default=None, help="shell command for mode=agent")
    p_run.add_argument("--report", default=None, help="write a JSON summary here")
    p_run.set_defaults(func=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "mode", None) is not None and not args.mode:
        args.mode = ["oracle"]
    if getattr(args, "command", None) == "run" and not args.mode:
        args.mode = ["oracle"]
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
