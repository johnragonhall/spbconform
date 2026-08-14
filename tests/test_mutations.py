"""Evidence that every check can fail, which is the only reason a pass is worth reading.

A conformance runner whose checks cannot fail is a runner that reports a pass
for anything, so this file is falsifiability evidence rather than assertions
about the current result. `MUTATIONS` breaks the reference edge node in one
documented way at a time and records which assertion identifiers stop holding.
`test_every_passing_check_has_a_killing_mutation` then fails if any check
survives the whole library, because a check nothing can break is measuring
nothing and would report a pass for an edge node doing the opposite.

The baseline is a full pass, so the sweep has to account for all 143 checks
with no carve-out. `test_the_baseline_survives_the_whole_sweep` runs the
baseline again afterwards: every fault is a field of a frozen dataclass handed
to a freshly built adapter, so nothing is patched and nothing needs restoring,
and this test is what keeps that true if a future fault reaches for global
state instead.

Nothing here is a conformance claim. The table records 299 specification
assertions and this library checks 143 of them, so a green sweep leaves the
larger part of the edge-node profile unmeasured.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest
from reference import Faults, ReferenceAdapter

import spbconform as spb

#: Each entry breaks the reference edge node in one documented way. The sweep
#: below records which assertions stop holding under each, and every check has
#: to appear under at least one of them.
MUTATIONS: Mapping[str, Faults] = {
    "namespace is not spBv1.0": Faults(namespace="spBv9.9"),
    "every topic grows a level": Faults(topic_suffix=True),
    "every topic is shouted": Faults(shout_topics=True),
    "every topic is case-folded": Faults(fold_topic_case=True),
    "device topics collapse onto one": Faults(collapse_device_topics=True),
    "identifier grammar is not enforced": Faults(accept_bad_identifiers=True),
    "the sequence never moves": Faults(constant_sequence=True),
    "the sequence is absent": Faults(absent_sequence=True),
    "the sequence never wraps": Faults(sequence_never_wraps=True),
    # The two delivery mutations are companions: between them every row of the
    # matrix is moved off its declared value, which the NDEATH and STATE rows
    # need because they are the two the specification puts at QoS 1.
    "every class is QoS 1 retained": Faults(delivery_override=(1, True)),
    "every class is QoS 0 unretained": Faults(delivery_override=(0, False)),
    "CONNECT hands back no will": Faults(no_will=True),
    "the will is a birth certificate": Faults(will_is_birth=True),
    "the will carries a sequence number": Faults(crowded_will=True),
    "births carry no alias": Faults(unaliased_births=True),
    "every metric shares one alias": Faults(shared_aliases=True),
    "the rebirth metric is aliased": Faults(alias_rebirth_metric=True),
    "data carries the metric name": Faults(named_data=True),
    "data repeats the datatype": Faults(typed_data=True),
    "births carry no name or datatype": Faults(untyped_births=True),
    "metrics carry no timestamp": Faults(undated_metrics=True),
    "payloads carry no timestamp": Faults(undated_payloads=True),
    "metrics run backwards in time": Faults(backwards_metric_order=True),
    "births declare nothing": Faults(empty_births=True),
    "the birth bdSeq drifts from the will": Faults(wrong_bdseq=True),
    "bdSeq never advances": Faults(frozen_bdseq=True),
    "bdSeq is unsigned": Faults(bdseq_uint64=True),
    "the rebirth metric is absent": Faults(no_rebirth_metric=True),
    "the rebirth metric is a true string": Faults(rebirth_metric_is_string=True),
    "a rebirth request is ignored": Faults(ignore_rebirth=True),
    "any command triggers a rebirth": Faults(rebirth_on_any_command=True),
    "a rebirth skips the device births": Faults(rebirth_only_nbirth=True),
    "a rebirth opens a new session": Faults(rebirth_reconnects=True),
    "a rebirth keeps publishing data": Faults(rebirth_publishes_data=True),
    "nothing is refused": Faults(refuse_nothing=True),
    "undeclared metrics are published": Faults(allow_undeclared=True),
    "every metric is republished": Faults(republish_everything=True),
    "a lost device reports as data": Faults(ddeath_is_data=True),
    "quality codes are undefined": Faults(bad_quality_codes=True),
    "no close publishes the NDEATH": Faults(no_disconnect=True),
    "metric names may collide on case": Faults(accept_case_colliding_metrics=True),
    "timestamps come from a counter": Faults(simulation_clock=True),
}


def _failures_under(faults: Faults) -> frozenset[str]:
    """The assertions that stop holding once one mutation is planted."""
    report = spb.run_edge_node_conformance(ReferenceAdapter(faults))
    return frozenset(result.assertion_id for result in report.failures)


@pytest.fixture(scope="module")
def baseline() -> spb.ConformanceReport:
    """The unmutated run every sweep result is read against."""
    return spb.run_edge_node_conformance(ReferenceAdapter())


@pytest.fixture(scope="module")
def killed() -> Mapping[str, frozenset[str]]:
    """Every mutation, and the assertions it falsifies."""
    return {name: _failures_under(faults) for name, faults in MUTATIONS.items()}


def test_the_sweep_covers_every_fault_the_reference_offers() -> None:
    """A fault with no entry here is a break nothing in the suite ever plants."""
    planted = {
        field
        for faults in MUTATIONS.values()
        for field in Faults.__dataclass_fields__
        if getattr(faults, field) != getattr(Faults(), field)
    }
    assert sorted(set(Faults.__dataclass_fields__) - planted) == []


def test_every_mutation_breaks_something(killed: Mapping[str, frozenset[str]]) -> None:
    """A mutation nothing notices is a hole in the harness, not a safe edit."""
    silent = [name for name, broken in killed.items() if not broken]
    assert silent == []


def test_every_passing_check_has_a_killing_mutation(
    killed: Mapping[str, frozenset[str]], baseline: spb.ConformanceReport
) -> None:
    """No check reports a pass that nothing in the library can turn over.

    This is the evidence that the numerator means something. A check that
    survives every mutation is measuring nothing, and would report a pass for
    an edge node that does the opposite of what the assertion asks.
    """
    broken_by_something = frozenset().union(*killed.values())
    survivors = sorted(
        result.assertion_id
        for result in baseline.results
        if result.passed and result.assertion_id not in broken_by_something
    )
    assert survivors == []


def test_the_baseline_survives_the_whole_sweep(baseline: spb.ConformanceReport) -> None:
    """Running every mutation leaves the next run exactly as it was.

    A fault that reached for module state or a class attribute would make every
    later result meaningless, so the baseline is re-derived after the sweep and
    compared against the one taken before it.
    """
    for faults in MUTATIONS.values():
        _failures_under(faults)
    after = spb.run_edge_node_conformance(ReferenceAdapter())
    assert [(r.assertion_id, r.passed) for r in after.results] == [
        (r.assertion_id, r.passed) for r in baseline.results
    ]


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_a_mutated_run_is_never_reported_as_conformant(name: str) -> None:
    """A run with failures does not read as a pass, whichever check found them."""
    report = spb.run_edge_node_conformance(ReferenceAdapter(MUTATIONS[name]))
    assert not report.conformant
    assert report.coverage.failed == len(report.failures)
    assert report.coverage.passed + report.coverage.failed == report.coverage.in_scope_total
    for failure in report.failures:
        assert failure.observation.strip()


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_the_default_adapter_clears_every_mutation(name: str) -> None:
    """Each assertion a mutation broke holds again once the break is removed.

    The other direction from the sweep, and the one that separates a check that
    has found something from a check that is wired shut. Every identifier a
    mutation falsifies passes under the plain reference, so the failure was an
    observation about the mutation rather than a verdict the check always
    reaches.
    """
    broken = _failures_under(MUTATIONS[name])
    restored = spb.run_edge_node_conformance(ReferenceAdapter())
    still_failing = frozenset(r.assertion_id for r in restored.failures)
    assert broken & still_failing == frozenset()


#: One mutation and the assertion it is specifically aimed at, written down so
#: a check that quietly stopped observing the thing it names fails here rather
#: than staying green on the strength of a neighbour's kill.
AIMED: Mapping[str, str] = {
    "namespace is not spBv1.0": "tck-id-topic-structure-namespace-a",
    "the sequence never wraps": "tck-id-payloads-sequence-num-incrementing",
    "the sequence never moves": "tck-id-topics-nbirth-seq-num",
    "the will carries a sequence number": "tck-id-payloads-ndeath-seq",
    "the will is a birth certificate": "tck-id-payloads-ndeath-will-message",
    "CONNECT hands back no will": "tck-id-message-flow-edge-node-birth-publish-will-message",
    "every metric shares one alias": "tck-id-payloads-alias-uniqueness",
    "births carry no alias": "tck-id-payloads-alias-birth-requirement",
    "data carries the metric name": "tck-id-payloads-alias-data-cmd-requirement",
    "data repeats the datatype": "tck-id-payloads-metric-datatype-not-req",
    "metrics carry no timestamp": "tck-id-payloads-name-birth-data-requirement",
    "metrics run backwards in time": "tck-id-operational-behavior-data-publish-nbirth-order",
    "the birth bdSeq drifts from the will": "tck-id-topics-nbirth-bdseq-matching",
    "bdSeq never advances": "tck-id-topics-nbirth-bdseq-increment",
    "bdSeq is unsigned": "tck-id-message-flow-edge-node-birth-publish-nbirth-payload-bdSeq",
    "the rebirth metric is absent": "tck-id-topics-nbirth-rebirth-metric",
    "the rebirth metric is a true string": (
        "tck-id-operational-behavior-data-commands-rebirth-datatype"
    ),
    "the rebirth metric is aliased": (
        "tck-id-operational-behavior-data-commands-rebirth-name-aliases"
    ),
    "a rebirth request is ignored": "tck-id-operational-behavior-data-commands-rebirth-action-2",
    "any command triggers a rebirth": (
        "tck-id-operational-behavior-data-commands-ncmd-rebirth-name"
    ),
    "a rebirth skips the device births": (
        "tck-id-operational-behavior-data-commands-rebirth-action-2"
    ),
    "a rebirth opens a new session": "tck-id-operational-behavior-data-commands-rebirth-action-3",
    "a rebirth keeps publishing data": (
        "tck-id-operational-behavior-data-commands-rebirth-action-1"
    ),
    "undeclared metrics are published": "tck-id-topics-nbirth-metric-reqs",
    "every metric is republished": "tck-id-principles-rbe-recommended",
    "a lost device reports as data": "tck-id-operational-behavior-device-ddeath",
    "quality codes are undefined": "tck-id-payloads-propertyset-quality-value-value",
    "no close publishes the NDEATH": (
        "tck-id-operational-behavior-edge-node-intentional-disconnect-ndeath"
    ),
    "metric names may collide on case": "tck-id-case-sensitivity-metric-names",
    "timestamps come from a counter": "tck-id-payloads-timestamp-in-UTC",
    "every topic is case-folded": "tck-id-case-sensitivity-sparkplug-ids",
    "identifier grammar is not enforced": "tck-id-intro-group-id-chars",
    "device topics collapse onto one": "tck-id-topic-structure-namespace-unique-device-id",
    "every topic grows a level": "tck-id-topic-structure",
    "nothing is refused": "tck-id-principles-birth-certificates-order",
    "payloads carry no timestamp": "tck-id-payloads-nbirth-timestamp",
    "births declare nothing": "tck-id-topics-nbirth-bdseq-included",
    "every class is QoS 1 retained": "tck-id-payloads-nbirth-qos",
    "every class is QoS 0 unretained": "tck-id-host-topic-phid-birth-qos",
}


@pytest.mark.parametrize("name", sorted(AIMED))
def test_a_mutation_kills_the_check_it_is_aimed_at(
    name: str, killed: Mapping[str, frozenset[str]]
) -> None:
    """The named check, not merely some check, notices the named break."""
    assert AIMED[name] in killed[name]
