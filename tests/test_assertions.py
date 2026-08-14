"""The table is the denominator, so its shape is asserted before anything runs.

Nothing here touches an implementation. These tests are about the published
list itself: that it carries every anchored assertion, that no row leaves scope
without naming what is missing, and that the checks and the rows agree in both
directions.
"""

from __future__ import annotations

import spbconform as spb


def test_table_carries_every_published_assertion() -> None:
    """The table's row count is the specification's assertion count."""
    assert len(spb.ASSERTIONS) == spb.SPEC_ASSERTION_COUNT == 299


def test_every_key_is_a_published_identifier() -> None:
    """Every key is spelled as the specification anchors it."""
    for assertion_id, assertion in spb.ASSERTIONS.items():
        assert assertion_id.startswith("tck-id-")
        assert assertion.assertion_id == assertion_id
        assert assertion.statement.endswith(".")


def test_every_row_names_a_profile_and_a_level() -> None:
    """No row is carried without saying who it constrains and how hard."""
    for assertion in spb.ASSERTIONS.values():
        assert isinstance(assertion.profile, spb.Profile)
        assert isinstance(assertion.level, spb.Level)


def test_out_of_scope_rows_name_a_missing_capability() -> None:
    """Nothing is dropped from scope without saying what the harness lacks."""
    for assertion in spb.ASSERTIONS.values():
        assert assertion.in_scope or isinstance(assertion.exclusion, spb.Exclusion)


def test_every_in_scope_assertion_has_a_check() -> None:
    """A row cannot claim scope without an executable observation behind it."""
    missing = [
        a.assertion_id for a in spb.in_scope_assertions() if a.assertion_id not in spb.CHECKS
    ]
    assert missing == []


def test_no_check_runs_without_a_row() -> None:
    """A check cannot report on an assertion the table does not carry."""
    stray = [key for key in spb.CHECKS if key not in spb.ASSERTIONS]
    assert stray == []


def test_the_profiles_partition_the_table() -> None:
    """Every assertion belongs to exactly one profile, and they add up."""
    counted = sum(len(spb.assertions_for(profile)) for profile in spb.Profile)
    assert counted == len(spb.ASSERTIONS)
    assert len(spb.assertions_for(spb.Profile.EDGE_NODE)) == 201


def test_coverage_denominator_is_larger_than_the_numerator() -> None:
    """The edge-node profile is bigger than the part this library checks.

    The point of the number is that it is not reported alone. A run that passes
    every check still leaves this many edge-node assertions unmeasured, and a
    caller reading the coverage sees the difference.
    """
    cover = spb.edge_node_coverage()
    assert cover.edge_node_total > cover.edge_node_in_scope
    assert cover.edge_node_out_of_scope == cover.edge_node_total - cover.edge_node_in_scope
    assert cover.spec_total == len(spb.ASSERTIONS)
    assert cover.in_scope_total == len(spb.CHECKS) == 143
    assert cover.edge_node_in_scope == 133
    assert cover.edge_node_out_of_scope == 68


def test_the_exclusion_counts_add_up_to_the_unchecked_rows() -> None:
    """Every unchecked assertion is counted under exactly one reason."""
    cover = spb.edge_node_coverage()
    assert sum(cover.out_of_scope.values()) == cover.spec_total - cover.in_scope_total


def test_exclusions_by_reason_lists_only_that_profile() -> None:
    """The grouping answers for one profile at a time."""
    grouped = spb.exclusions_by_reason(spb.Profile.EDGE_NODE)
    listed = [assertion_id for ids in grouped.values() for assertion_id in ids]
    assert len(listed) == len(set(listed)) == 68
    for assertion_id in listed:
        assert spb.ASSERTIONS[assertion_id].profile is spb.Profile.EDGE_NODE
        assert not spb.ASSERTIONS[assertion_id].in_scope


def test_no_statement_quotes_a_requirement_keyword_verbatim() -> None:
    """Statements are written as requirements, not pasted as normative prose.

    A weak check for a legal property, and it is here to catch the obvious
    regression rather than to prove the clean-room claim: a statement carrying
    the specification's own SHALL or MUST NOT capitalization is a sentence
    somebody copied rather than wrote.
    """
    copied = [
        a.assertion_id
        for a in spb.ASSERTIONS.values()
        if "SHALL" in a.statement or "MUST" in a.statement or "MAY NOT" in a.statement
    ]
    assert copied == []
