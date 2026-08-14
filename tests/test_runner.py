"""The baseline run, and what the runner does with an adapter that misbehaves.

The reference edge node satisfies every check the library carries, so the
baseline here is a full pass. That is not a conformance claim about the
reference and the tests say so: the run leaves 68 edge-node assertions
unmeasured, and the coverage those results are reported alongside is what
carries that number.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from reference import Faults, ReferenceAdapter

import spbconform as spb


@pytest.fixture(scope="module")
def report() -> spb.ConformanceReport:
    """One run of the harness against the conformant reference edge node."""
    return spb.run_edge_node_conformance(ReferenceAdapter())


def test_every_check_is_ruled_on_exactly_once(report: spb.ConformanceReport) -> None:
    """The run rules on each in-scope assertion once and no more."""
    ruled = [result.assertion_id for result in report.results]
    assert sorted(ruled) == sorted(a.assertion_id for a in spb.in_scope_assertions())
    assert len(ruled) == len(set(ruled))


def test_the_reference_satisfies_every_check(report: spb.ConformanceReport) -> None:
    """The baseline is a full pass, so a later failure means a real regression."""
    assert [f"{r.assertion_id}: {r.observation}" for r in report.failures] == []
    assert report.coverage.passed == 143
    assert report.coverage.failed == 0


def test_every_result_carries_an_observation(report: spb.ConformanceReport) -> None:
    """A verdict with no observation behind it is a verdict nobody can audit."""
    for result in report.results:
        assert result.observation.strip()


def test_a_full_pass_is_still_not_a_conformance_claim(report: spb.ConformanceReport) -> None:
    """`conformant` is scoped to what ran, and the coverage says how much did not."""
    assert report.conformant
    assert report.coverage.edge_node_out_of_scope == 68
    assert report.coverage.in_scope_total < report.coverage.edge_node_total


def test_the_run_is_deterministic() -> None:
    """Two runs of one adapter agree, so a difference is the implementation's."""
    first = spb.run_edge_node_conformance(ReferenceAdapter())
    second = spb.run_edge_node_conformance(ReferenceAdapter())
    assert [(r.assertion_id, r.passed) for r in first.results] == [
        (r.assertion_id, r.passed) for r in second.results
    ]


def test_the_report_names_every_failure() -> None:
    """A failing run prints the identifier and the observation for each failure."""
    broken = spb.run_edge_node_conformance(ReferenceAdapter(Faults(namespace="spBv9.9")))
    text = spb.format_report(broken)
    assert not broken.conformant
    for failure in broken.failures:
        assert f"FAIL {failure.assertion_id}" in text
    assert "not a conformance certification" in text


def test_the_report_always_carries_the_coverage(report: spb.ConformanceReport) -> None:
    """The numerator is never printed without the denominator under it."""
    text = spb.format_report(report)
    assert "edge-node profile               201" in text
    assert "edge-node unchecked here        68" in text
    assert "unchecked, by the capability that is missing:" in text


def test_coverage_without_a_run_reports_no_results() -> None:
    """The table's coverage stands on its own, with zero passed and zero failed."""
    cover = spb.edge_node_coverage()
    assert (cover.passed, cover.failed) == (0, 0)
    assert cover.in_scope_total == 143


class _ExplodingAdapter(ReferenceAdapter):
    """An adapter that cannot be played at all."""

    def new_session(self, spec: spb.NodeSpec) -> spb.EdgeNodeSession:
        raise ZeroDivisionError("this implementation is broken before it starts")


def test_an_unplayable_adapter_fails_every_check_rather_than_crashing() -> None:
    """A trace that will not play is a report of failures, not a traceback.

    An implementation that raises on the first call has satisfied nothing, and
    a runner that let the exception out would hide that behind one stack trace
    with no assertion identifiers in it.
    """
    report = spb.run_edge_node_conformance(_ExplodingAdapter())
    assert len(report.failures) == 143
    assert not report.conformant
    assert all("ZeroDivisionError" in r.observation for r in report.results)


class _HalfBrokenAdapter(ReferenceAdapter):
    """An adapter whose device births raise something the harness does not expect."""

    def new_session(self, spec: spb.NodeSpec):  # type: ignore[no-untyped-def]
        session = super().new_session(spec)
        original = session.device_birth

        def raising(device_id: str):  # type: ignore[no-untyped-def]
            if device_id == "device-b":
                raise ZeroDivisionError("a birth certificate blew up")
            return original(device_id)

        session.device_birth = raising  # type: ignore[method-assign]
        return session


def test_an_unexpected_error_becomes_an_observation_not_a_crash() -> None:
    """An exception the harness did not ask for is reported against its assertion."""
    report = spb.run_edge_node_conformance(_HalfBrokenAdapter())
    assert not report.conformant
    assert any("ZeroDivisionError" in r.observation for r in report.results)


def test_the_fixture_declares_two_devices_with_distinct_metrics() -> None:
    """Several assertions compare one device's stream against another's."""
    assert len(spb.FIXTURE.devices) == 2
    names = {spec.name for specs in spb.FIXTURE.devices.values() for spec in specs}
    assert len(names) == sum(len(specs) for specs in spb.FIXTURE.devices.values())


def test_the_fixture_can_be_replayed_by_hand() -> None:
    """`play` is public, so a caller can read the trace a check reads."""
    trace = spb.play(ReferenceAdapter())
    assert trace.nbirth.message_type is spb.MessageType.NBIRTH
    assert trace.will is not None
    assert trace.will.message.message_type is spb.MessageType.NDEATH
    assert set(trace.dbirths) == set(spb.FIXTURE.devices)
    assert trace.metric(trace.nbirth, spb.BDSEQ_METRIC).value == 0


def test_a_check_can_be_run_on_its_own() -> None:
    """One assertion at a time, for a caller chasing a single failure."""
    trace = spb.play(ReferenceAdapter())
    observation = spb.CHECKS["tck-id-topic-structure"](trace)
    assert "four levels" in observation

    broken = spb.play(ReferenceAdapter(Faults(topic_suffix=True)))
    with pytest.raises(spb.CheckFailed):
        spb.CHECKS["tck-id-topic-structure"](broken)


def test_a_node_spec_the_adapter_refuses_is_the_adapter_s_verdict() -> None:
    """The harness hands the spec over; refusing it is an answer, not a crash."""
    colliding = (
        spb.MetricSpec(name="Read_Rate", datatype=spb.DataType.Float),
        spb.MetricSpec(name="read_rate", datatype=spb.DataType.Float),
    )
    spec = replace(spb.FIXTURE, node_metrics=(), devices={"device-b": colliding})
    with pytest.raises(ValueError):
        ReferenceAdapter().new_session(spec)
