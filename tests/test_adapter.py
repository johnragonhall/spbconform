"""The adapter surface: how small it is, and that each member says why it exists.

The protocols are the library's contract with an implementation it has never
seen, so the tests here are about the contract itself. A member added without a
reason written on it is a member nobody can decide whether to implement, and a
surface that grows quietly is one that stops being portable.
"""

from __future__ import annotations

import inspect

import spbconform as spb
from spbconform.adapter import EdgeNodeAdapter, EdgeNodeSession

ADAPTER_MEMBERS = ("new_session", "validate_ids", "declared_delivery", "quality_codes")
SESSION_MEMBERS = (
    "connect",
    "node_birth",
    "device_birth",
    "node_data",
    "device_data",
    "device_death",
    "handle_node_command",
    "disconnect",
    "topic_for",
)


def _declared(protocol: type) -> tuple[str, ...]:
    """The members a protocol declares, ignoring what `Protocol` itself brings."""
    return tuple(
        name
        for name, value in vars(protocol).items()
        if not name.startswith("_") and inspect.isfunction(value)
    )


def test_the_adapter_surface_is_exactly_what_is_documented() -> None:
    """A member added without a docs entry is a portability cost nobody agreed to."""
    assert _declared(EdgeNodeAdapter) == ADAPTER_MEMBERS
    assert _declared(EdgeNodeSession) == SESSION_MEMBERS
    assert len(ADAPTER_MEMBERS) + len(SESSION_MEMBERS) == 13


def test_every_protocol_member_says_why_a_check_needs_it() -> None:
    """The reason lives on the member, so nobody has to infer it from the runner."""
    for protocol in (EdgeNodeAdapter, EdgeNodeSession):
        for name, value in vars(protocol).items():
            if name.startswith("_") or not inspect.isfunction(value):
                continue
            assert value.__doc__, f"{protocol.__name__}.{name} carries no docstring"
            assert len(value.__doc__.strip()) > 40, f"{protocol.__name__}.{name} says too little"


def test_the_protocols_are_not_runtime_checkable() -> None:
    """A structural isinstance would answer a question the harness never asks.

    An object with thirteen correctly named attributes is not an edge node.
    The runner calls the members and reports what came back, so a passing
    isinstance would only ever be a false reassurance.
    """
    assert not getattr(EdgeNodeAdapter, "_is_runtime_protocol", False)
    assert not getattr(EdgeNodeSession, "_is_runtime_protocol", False)


def test_the_refusal_types_are_published() -> None:
    """An adapter has to know which exceptions the harness reads as a refusal."""
    assert spb.Refused in spb.REFUSALS
    assert ValueError in spb.REFUSALS and RuntimeError in spb.REFUSALS
    assert KeyError not in spb.REFUSALS  # LookupError already covers it
    assert LookupError in spb.REFUSALS
    assert not any(issubclass(TypeError, kind) for kind in spb.REFUSALS)


def test_the_constants_are_the_ones_the_specification_fixes() -> None:
    """An adapter maps onto these, so they are asserted rather than assumed."""
    assert spb.NAMESPACE == "spBv1.0"
    assert spb.SEQUENCE_MODULUS == 256
    assert spb.BDSEQ_METRIC == "bdSeq"
    assert spb.REBIRTH_METRIC == "Node Control/Rebirth"
    assert set(spb.QUALITY_CODES) == {0, 192, 500}
    assert int(spb.DataType.Int64) == 4
    assert int(spb.DataType.Boolean) == 11
    assert spb.UTC_FLOOR_MS == 1_577_836_800_000


def test_the_message_types_are_immutable() -> None:
    """A check cannot edit the message it is reading, deliberately."""
    message = spb.Message(
        topic="spBv1.0/g/NBIRTH/e",
        message_type=spb.MessageType.NBIRTH,
        payload=spb.Payload(timestamp=1, metrics=(), seq=0),
        qos=0,
        retain=False,
    )
    for target, field, value in (
        (message, "topic", "other"),
        (message.payload, "seq", 1),
        (spb.Metric(value=1), "value", 2),
        (spb.MetricSpec(name="m", datatype=spb.DataType.Int64), "name", "n"),
    ):
        try:
            setattr(target, field, value)
        except (AttributeError, TypeError):
            continue
        raise AssertionError(f"{type(target).__name__}.{field} was writable")


def test_the_public_names_are_all_importable() -> None:
    """Everything `__all__` promises resolves, so a documented name is a real one."""
    for name in spb.__all__:
        assert hasattr(spb, name), name
    assert spb.__version__
