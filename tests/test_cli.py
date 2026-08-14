"""`python -m spbconform`: what it prints, and what it exits with.

The exit code is the part a pipeline reads, so it is asserted for each path:
zero when every check held, one when a check found something, two when the
adapter could not be loaded at all. The third is separate from the second on
purpose, because a harness that cannot import your code has measured nothing
and should not be mistaken for a harness that measured a pass.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest
from reference import Faults, ReferenceAdapter

from spbconform.cli import load_adapter, main

# Loaded through the command line's own import path, which is what proves the
# `module:attribute` form works against a factory as well as an instance.
CONFORMANT = "reference:ReferenceAdapter"


def broken_adapter() -> ReferenceAdapter:
    """A factory the command line can import, for the failing-run path."""
    return ReferenceAdapter(Faults(namespace="spBv9.9"))


def test_help_prints_without_an_adapter(capsys: pytest.CaptureFixture[str]) -> None:
    """`--help` works with nothing installed and nothing implemented."""
    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])
    assert exit_info.value.code == 0
    text = capsys.readouterr().out
    assert "spbconform" in text
    assert "not the Eclipse TCK" in text
    assert "coverage" in text and "list" in text and "run" in text


def test_the_module_entry_point_runs_as_a_subprocess() -> None:
    """`python -m spbconform --help` is the documented invocation, so it is run."""
    finished = subprocess.run(
        [sys.executable, "-m", "spbconform", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert finished.returncode == 0
    assert "spbconform" in finished.stdout


def test_no_arguments_prints_the_coverage(capsys: pytest.CaptureFixture[str]) -> None:
    """The default output is the honest denominator, which needs no adapter."""
    assert main([]) == 0
    text = capsys.readouterr().out
    assert "specification assertions        299" in text
    assert "not a conformance certification" in text


def test_coverage_as_json_says_it_certifies_nothing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A machine reading the numbers reads the disclaimer with them."""
    assert main(["coverage", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["spec_total"] == 299
    assert payload["edge_node_total"] == 201
    assert payload["edge_node_checked"] == 133
    assert payload["edge_node_unchecked"] == 68
    assert payload["checks_in_library"] == 143
    assert payload["certifies_conformance"] is False
    assert sum(payload["unchecked_by_reason"].values()) == 299 - 143


def test_list_prints_every_assertion(capsys: pytest.CaptureFixture[str]) -> None:
    """Every identifier and its requirement, for a reader with no adapter yet."""
    assert main(["list", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 299
    assert sum(1 for row in rows if row["checked"]) == 143
    for row in rows:
        assert row["checked"] is (row["unchecked_because"] is None)


def test_list_filters_by_profile_and_scope(capsys: pytest.CaptureFixture[str]) -> None:
    """The filters narrow the list without changing what any row says."""
    assert main(["list", "--profile", "edge-node", "--checked", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 133
    assert all(row["profile"] == "edge-node" and row["checked"] for row in rows)

    assert main(["list", "--profile", "edge-node", "--no-checked", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 68
    assert all(row["unchecked_because"] for row in rows)


def test_list_as_text_marks_what_is_checked(capsys: pytest.CaptureFixture[str]) -> None:
    """The plain listing prints the requirement under each identifier, marked."""
    assert main(["list", "--profile", "edge-node"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len([line for line in lines if line.startswith("check")]) == 133
    assert len([line for line in lines if line.startswith("  -  ")]) == 68
    assert any("The NBIRTH" in line for line in lines)


def test_run_against_a_conformant_adapter_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A full pass exits zero and still prints the coverage beneath it."""
    assert main(["run", CONFORMANT]) == 0
    text = capsys.readouterr().out
    assert "passed                          143" in text
    assert "failed                          0" in text


def test_run_against_a_broken_adapter_exits_one(capsys: pytest.CaptureFixture[str]) -> None:
    """A failing check is an exit code a pipeline can read, not only a paragraph."""
    assert main(["run", "test_cli:broken_adapter"]) == 1
    assert "FAIL tck-id-topic-structure-namespace-a" in capsys.readouterr().out


def test_run_as_json_carries_every_result(capsys: pytest.CaptureFixture[str]) -> None:
    """The machine-readable run names each assertion and what was observed."""
    assert main(["run", CONFORMANT, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] == 143
    assert payload["certifies_conformance"] is False
    assert len(payload["results"]) == 143
    assert all(result["observation"] for result in payload["results"])


def test_quiet_prints_nothing_and_still_reports(capsys: pytest.CaptureFixture[str]) -> None:
    """For a gate that wants the verdict and none of the prose."""
    assert main(["run", CONFORMANT, "--quiet"]) == 0
    assert capsys.readouterr().out == ""


def test_an_adapter_that_cannot_be_loaded_exits_two(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Nothing measured is a different outcome from something measured and passed."""
    assert main(["run", "reference:NoSuchThing"]) == 2
    assert "no attribute" in capsys.readouterr().err
    assert main(["run", "not_a_module_anybody_has:Adapter"]) == 2
    assert main(["run", "malformed"]) == 2


def test_load_adapter_accepts_an_instance_as_well_as_a_factory() -> None:
    """A module-level instance is a legal target, and is returned as it is."""
    assert isinstance(load_adapter(CONFORMANT), ReferenceAdapter)
    assert load_adapter("test_cli:broken_adapter").faults.namespace == "spBv9.9"
