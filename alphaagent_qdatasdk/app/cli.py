"""Command line interface for AlphaAgent_qdatasdk."""

from __future__ import annotations

import argparse

from alphaagent_qdatasdk.app.conf import build_loop_config
from alphaagent_qdatasdk.workflow import AlphaAgentLoop


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="alphaagent-qdatasdk")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the mock AlphaAgent loop.")
    run_parser.add_argument("--rounds", type=int, default=1, help="Number of rounds to run.")
    run_parser.add_argument(
        "--direction",
        default=None,
        help="Active research direction for hypothesis generation.",
    )
    run_parser.add_argument(
        "--workspace",
        default=None,
        help="Workspace directory used by coder and runner stages.",
    )
    run_parser.add_argument(
        "--real-run",
        action="store_true",
        help="Mark config as non-dry-run. Real integrations are not implemented yet.",
    )
    return parser


def run_command(args: argparse.Namespace) -> int:
    config = build_loop_config(
        active_direction=args.direction,
        max_rounds=args.rounds,
        workspace=args.workspace,
        dry_run=not args.real_run,
    )
    loop = AlphaAgentLoop(config)
    outputs = loop.run()

    for output in outputs:
        print(
            "round={round_id} status={status} decision={decision} tasks={task_count}".format(
                round_id=output.round_id,
                status=output.result.status.value,
                decision=output.feedback.decision.value,
                task_count=len(output.experiment.factor_tasks),
            )
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return run_command(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
