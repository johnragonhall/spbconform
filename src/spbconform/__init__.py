"""spbconform: the Sparkplug B assertion table, and a runner for it.

The specification anchors 299 assertions with a `tck-testable` role. This
library carries every one of them, written as a requirement rather than quoted,
together with an executable check for each of the 143 an in-process harness can
observe and a recorded reason for each of the 156 it cannot.

Point it at your own edge node by implementing `EdgeNodeAdapter` and
`EdgeNodeSession` over it, then call `run_edge_node_conformance`. There are no
third-party dependencies at runtime or at test time.

This is not the Eclipse Sparkplug Technology Compatibility Kit and it certifies
nothing. It measures the gap between one implementation and a published list.
"""

from __future__ import annotations

from .adapter import EdgeNodeAdapter, EdgeNodeSession
from .assertions import (
    ASSERTIONS,
    SPEC_ASSERTION_COUNT,
    SPEC_VERSION,
    Assertion,
    Exclusion,
    Level,
    Profile,
    assertions_for,
    exclusions_by_reason,
    in_scope_assertions,
)
from .checks import CHECKS, FIXTURE, Check, CheckFailed, Trace, play
from .model import (
    BDSEQ_METRIC,
    NAMESPACE,
    QUALITY_CODES,
    REBIRTH_METRIC,
    REFUSALS,
    SEQUENCE_MODULUS,
    UTC_FLOOR_MS,
    DataType,
    Message,
    MessageType,
    Metric,
    MetricSpec,
    NodeSpec,
    Payload,
    Quality,
    Refused,
    Will,
)
from .runner import (
    AssertionResult,
    ConformanceReport,
    Coverage,
    edge_node_coverage,
    format_coverage,
    format_report,
    run_edge_node_conformance,
)

__version__ = "0.1.0"

__all__ = [
    "ASSERTIONS",
    "BDSEQ_METRIC",
    "CHECKS",
    "FIXTURE",
    "NAMESPACE",
    "QUALITY_CODES",
    "REBIRTH_METRIC",
    "REFUSALS",
    "SEQUENCE_MODULUS",
    "SPEC_ASSERTION_COUNT",
    "SPEC_VERSION",
    "UTC_FLOOR_MS",
    "Assertion",
    "AssertionResult",
    "Check",
    "CheckFailed",
    "ConformanceReport",
    "Coverage",
    "DataType",
    "EdgeNodeAdapter",
    "EdgeNodeSession",
    "Exclusion",
    "Level",
    "Message",
    "MessageType",
    "Metric",
    "MetricSpec",
    "NodeSpec",
    "Payload",
    "Profile",
    "Quality",
    "Refused",
    "Trace",
    "Will",
    "__version__",
    "assertions_for",
    "edge_node_coverage",
    "exclusions_by_reason",
    "format_coverage",
    "format_report",
    "in_scope_assertions",
    "play",
    "run_edge_node_conformance",
]
