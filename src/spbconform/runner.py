"""Run every check against one adapter, and report the gap honestly.

A green run is not a conformance claim and this module never phrases it as one.
`ConformanceReport.conformant` says the in-scope subset held; `Coverage` says
how much smaller that subset is than the edge-node profile, and why. The two
are reported together because either one alone misleads.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .adapter import EdgeNodeAdapter
from .assertions import (
    ASSERTIONS,
    SPEC_ASSERTION_COUNT,
    SPEC_VERSION,
    Exclusion,
    Profile,
    assertions_for,
    in_scope_assertions,
)
from .checks import CHECKS, CheckFailed, play


@dataclass(frozen=True, slots=True)
class AssertionResult:
    """What the runner observed for one assertion."""

    assertion_id: str
    passed: bool
    observation: str


@dataclass(frozen=True, slots=True)
class Coverage:
    """The honest denominator, and what sits under it.

    `edge_node_total` is every assertion of the edge-node profile, whether or
    not this library can observe it. `passed` is never reported without it.
    """

    spec_version: str
    spec_total: int
    edge_node_total: int
    edge_node_in_scope: int
    in_scope_total: int
    passed: int
    failed: int
    out_of_scope: Mapping[Exclusion, int]

    @property
    def edge_node_out_of_scope(self) -> int:
        """Edge-node assertions this library carries no check for."""
        return self.edge_node_total - self.edge_node_in_scope


@dataclass(frozen=True, slots=True)
class ConformanceReport:
    """Every in-scope assertion's result, and the coverage around them."""

    results: tuple[AssertionResult, ...]
    coverage: Coverage

    @property
    def failures(self) -> tuple[AssertionResult, ...]:
        """The assertions the edge node did not satisfy."""
        return tuple(result for result in self.results if not result.passed)

    @property
    def conformant(self) -> bool:
        """Whether every in-scope assertion held.

        True here is not a conformance claim. It says the in-scope subset held,
        and that subset is smaller than the edge-node profile by exactly
        `coverage.edge_node_out_of_scope` assertions.
        """
        return not self.failures


def run_edge_node_conformance(adapter: EdgeNodeAdapter) -> ConformanceReport:
    """Play one edge-node session through the adapter and rule on every check.

    A trace that cannot be played at all is reported as every in-scope
    assertion failing with the error that stopped it, rather than as a crash.
    An implementation that raises where the specification expects a message has
    not satisfied the assertions that read that message, and a traceback out of
    the runner would hide the other results behind the first one.
    """
    try:
        trace = play(adapter)
    except Exception as error:  # noqa: BLE001
        detail = f"the session could not be played: {type(error).__name__}: {error}"
        results = tuple(
            AssertionResult(assertion_id, False, detail) for assertion_id in sorted(CHECKS)
        )
        return ConformanceReport(results=results, coverage=edge_node_coverage(results))

    results = []
    for assertion_id in sorted(CHECKS):
        try:
            observation = CHECKS[assertion_id](trace)
        except CheckFailed as failure:
            results.append(AssertionResult(assertion_id, False, str(failure)))
        except Exception as error:  # noqa: BLE001
            # An edge node that raises where the assertion expects a message
            # has not satisfied the assertion, so the error is the observation
            # rather than a crash that hides every other result.
            results.append(AssertionResult(assertion_id, False, f"{type(error).__name__}: {error}"))
        else:
            results.append(AssertionResult(assertion_id, True, observation))
    return ConformanceReport(results=tuple(results), coverage=edge_node_coverage(tuple(results)))


def edge_node_coverage(results: tuple[AssertionResult, ...] = ()) -> Coverage:
    """The coverage statement, with or without a run behind it."""
    edge = assertions_for(Profile.EDGE_NODE)
    by_reason: dict[Exclusion, int] = {}
    for assertion in ASSERTIONS.values():
        if assertion.exclusion is not None:
            by_reason[assertion.exclusion] = by_reason.get(assertion.exclusion, 0) + 1
    return Coverage(
        spec_version=SPEC_VERSION,
        spec_total=SPEC_ASSERTION_COUNT,
        edge_node_total=len(edge),
        edge_node_in_scope=sum(1 for a in edge if a.in_scope),
        in_scope_total=len(in_scope_assertions()),
        passed=sum(1 for r in results if r.passed),
        failed=sum(1 for r in results if not r.passed),
        out_of_scope=by_reason,
    )


def format_coverage(coverage: Coverage) -> str:
    """The coverage statement as lines, with the unchecked reasons beneath it."""
    lines = [
        f"Sparkplug B v{coverage.spec_version} edge-node assertion coverage",
        f"  specification assertions        {coverage.spec_total}",
        f"  edge-node profile               {coverage.edge_node_total}",
        f"  edge-node checked here          {coverage.edge_node_in_scope}",
        f"  edge-node unchecked here        {coverage.edge_node_out_of_scope}",
        f"  checks in the library           {coverage.in_scope_total}",
        "",
        "unchecked, by the capability that is missing:",
    ]
    ordered = sorted(coverage.out_of_scope.items(), key=lambda item: (-item[1], item[0]))
    for reason, count in ordered:
        lines.append(f"  {count:3d}  {reason.value}")
    lines.append("")
    lines.append(
        "This is a gap measurement against a published assertion list, not a "
        "conformance certification."
    )
    return "\n".join(lines)


def format_report(report: ConformanceReport) -> str:
    """The run as lines: the numbers, then the failures, then the coverage."""
    cover = report.coverage
    lines = [
        f"Sparkplug B v{cover.spec_version} edge-node conformance run",
        f"  specification assertions        {cover.spec_total}",
        f"  edge-node profile               {cover.edge_node_total}",
        f"  edge-node checked here          {cover.edge_node_in_scope}",
        f"  edge-node unchecked here        {cover.edge_node_out_of_scope}",
        f"  checks run (all profiles)       {cover.in_scope_total}",
        f"  passed                          {cover.passed}",
        f"  failed                          {cover.failed}",
        "",
    ]
    for result in report.failures:
        lines.append(f"FAIL {result.assertion_id}")
        lines.append(f"     {result.observation}")
    if report.failures:
        lines.append("")
    lines.append(format_coverage(cover))
    return "\n".join(lines)
