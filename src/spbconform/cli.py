"""The command line: read the table, or run it against an adapter.

Two of the three subcommands need no implementation at all, because the table
is worth reading on its own: it is the published assertion list with a
requirement written against each identifier and a recorded reason wherever this
library carries no check. `run` is the one that needs an adapter, and it takes
it as an import path so the harness can be pointed at a project without that
project importing anything from here at build time.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections.abc import Sequence
from typing import Any

from .adapter import EdgeNodeAdapter
from .assertions import ASSERTIONS, SPEC_VERSION, Profile
from .runner import edge_node_coverage, format_coverage, format_report, run_edge_node_conformance


def load_adapter(target: str) -> EdgeNodeAdapter:
    """Import `module:attribute` and call it if it is callable.

    A factory is accepted as well as an instance, because most adapters need
    construction and a module-level singleton would make every run share one
    implementation's state.
    """
    module_name, _, attribute = target.partition(":")
    if not module_name or not attribute:
        raise ValueError(f"{target!r} is not of the form 'module:attribute'")
    module = importlib.import_module(module_name)
    try:
        found: Any = getattr(module, attribute)
    except AttributeError:
        raise ValueError(f"{module_name!r} has no attribute {attribute!r}") from None
    return found() if callable(found) else found


def _assertion_rows() -> list[dict[str, Any]]:
    """Every assertion as a plain dictionary, in specification order."""
    return [
        {
            "assertion_id": assertion.assertion_id,
            "profile": str(assertion.profile),
            "level": str(assertion.level),
            "checked": assertion.in_scope,
            "unchecked_because": None if assertion.in_scope else str(assertion.exclusion.value),
            "statement": assertion.statement,
        }
        for assertion in ASSERTIONS.values()
    ]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spbconform",
        description=(
            f"Check a Sparkplug B v{SPEC_VERSION} edge-node implementation against the "
            "specification's own tck-testable assertion identifiers. Clean-room, "
            "MIT-licensed, and not the Eclipse TCK: it measures a gap, it does not certify."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    coverage = sub.add_parser(
        "coverage",
        help="print the assertion counts and the reason each unchecked assertion is unchecked",
    )
    coverage.add_argument("--json", action="store_true", help="emit the counts as JSON")

    listing = sub.add_parser("list", help="print every assertion identifier and its requirement")
    listing.add_argument(
        "--profile",
        choices=[str(p) for p in Profile],
        help="only the assertions constraining one conformance profile",
    )
    listing.add_argument(
        "--checked",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="only the assertions this library does, or does not, carry a check for",
    )
    listing.add_argument("--json", action="store_true", help="emit the rows as JSON")

    run = sub.add_parser("run", help="run every check against an adapter")
    run.add_argument(
        "adapter",
        metavar="MODULE:ATTRIBUTE",
        help=(
            "import path of an EdgeNodeAdapter, or of a zero-argument factory that "
            "returns one, for example 'myproject.spb_adapter:Adapter'"
        ),
    )
    run.add_argument("--json", action="store_true", help="emit the results as JSON")
    run.add_argument(
        "--quiet", action="store_true", help="print nothing; report only through the exit code"
    )
    return parser


def _run_coverage(args: argparse.Namespace) -> int:
    coverage = edge_node_coverage()
    if args.json:
        print(
            json.dumps(
                {
                    "spec_version": coverage.spec_version,
                    "spec_total": coverage.spec_total,
                    "edge_node_total": coverage.edge_node_total,
                    "edge_node_checked": coverage.edge_node_in_scope,
                    "edge_node_unchecked": coverage.edge_node_out_of_scope,
                    "checks_in_library": coverage.in_scope_total,
                    "unchecked_by_reason": {
                        reason.name: count for reason, count in coverage.out_of_scope.items()
                    },
                    "certifies_conformance": False,
                },
                indent=2,
            )
        )
    else:
        print(format_coverage(coverage))
    return 0


def _run_list(args: argparse.Namespace) -> int:
    rows = _assertion_rows()
    if args.profile is not None:
        rows = [row for row in rows if row["profile"] == args.profile]
    if args.checked is not None:
        rows = [row for row in rows if row["checked"] is args.checked]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for row in rows:
        mark = "check" if row["checked"] else "  -  "
        print(f"{mark}  {row['profile']:<16}  {row['level']:<6}  {row['assertion_id']}")
        print(f"         {row['statement']}")
    return 0


def _run_check(args: argparse.Namespace) -> int:
    try:
        adapter = load_adapter(args.adapter)
    except (ImportError, ValueError) as error:
        print(f"spbconform: {error}", file=sys.stderr)
        return 2
    report = run_edge_node_conformance(adapter)
    if args.quiet:
        pass
    elif args.json:
        print(
            json.dumps(
                {
                    "spec_version": report.coverage.spec_version,
                    "passed": report.coverage.passed,
                    "failed": report.coverage.failed,
                    "checks_run": report.coverage.in_scope_total,
                    "edge_node_total": report.coverage.edge_node_total,
                    "edge_node_unchecked": report.coverage.edge_node_out_of_scope,
                    "certifies_conformance": False,
                    "results": [
                        {
                            "assertion_id": result.assertion_id,
                            "passed": result.passed,
                            "observation": result.observation,
                        }
                        for result in report.results
                    ],
                },
                indent=2,
            )
        )
    else:
        print(format_report(report))
    return 0 if report.conformant else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Print what was asked for, and exit non-zero when an in-scope check fails."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        args = parser.parse_args(["coverage"])
    if args.command == "coverage":
        return _run_coverage(args)
    if args.command == "list":
        return _run_list(args)
    return _run_check(args)
