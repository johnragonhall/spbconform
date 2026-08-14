"""The vocabulary a check reads: the specification's constants and one message.

Everything here is a fact the specification fixes rather than a design choice:
the namespace level, the sequence modulus, the two reserved metric names, the
datatype enumeration, and the three quality codes. An adapter maps its own
types onto these so a check can read one shape whatever implementation it is
pointed at.

The message types are deliberately plain frozen dataclasses. A check reads what
an edge node would put on the wire, so every field is one a subscriber could
observe; nothing here reaches into an implementation's internal state.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Any

#: The first level of every Sparkplug B topic.
NAMESPACE = "spBv1.0"

#: The sequence number is one byte, so it returns to zero after 255.
SEQUENCE_MODULUS = 256

#: The metric that carries the birth-death sequence number.
BDSEQ_METRIC = "bdSeq"

#: The metric an NCMD writes to ask an edge node to republish its birth set.
REBIRTH_METRIC = "Node Control/Rebirth"

#: Epoch milliseconds at 2020-01-01T00:00:00Z. A payload timestamp at or above
#: this reads as a UTC wall-clock instant; one below it is a counter, a
#: simulation instant, or an uptime, which is how the two UTC assertions are
#: decided without a second time source to compare against.
UTC_FLOOR_MS = 1_577_836_800_000

#: The characters MQTT reads as a level separator or a wildcard, which a
#: Sparkplug identifier therefore cannot carry.
RESERVED_IN_TOPIC = ("+", "#", "/")


class Refused(Exception):
    """An adapter refused a call rather than performing it.

    Several assertions are about what an edge node declines to do: publish
    before CONNECT, publish a metric no birth certificate declared, render a
    device topic with no device id. An adapter may raise this, or any of
    `ValueError`, `RuntimeError`, or `LookupError`, and the harness reads all
    four the same way. Anything else propagates and is reported as a failure,
    because a harness that treated every exception as a deliberate refusal
    would score a broken implementation as a careful one.
    """


#: The exception types a check reads as a deliberate refusal.
REFUSALS: tuple[type[BaseException], ...] = (Refused, ValueError, RuntimeError, LookupError)


class MessageType(StrEnum):
    """The Sparkplug message types, spelled as they appear in a topic."""

    NBIRTH = "NBIRTH"
    NDEATH = "NDEATH"
    NDATA = "NDATA"
    NCMD = "NCMD"
    DBIRTH = "DBIRTH"
    DDEATH = "DDEATH"
    DDATA = "DDATA"
    DCMD = "DCMD"
    STATE = "STATE"


#: The message types whose topic carries a device id level.
DEVICE_MESSAGE_TYPES = (
    MessageType.DBIRTH,
    MessageType.DDEATH,
    MessageType.DDATA,
    MessageType.DCMD,
)

#: The message types whose topic ends at the edge node id.
NODE_MESSAGE_TYPES = (
    MessageType.NBIRTH,
    MessageType.NDEATH,
    MessageType.NDATA,
    MessageType.NCMD,
)


class DataType(IntEnum):
    """The payload datatype enumeration, with the values the specification fixes."""

    Unknown = 0
    Int8 = 1
    Int16 = 2
    Int32 = 3
    Int64 = 4
    UInt8 = 5
    UInt16 = 6
    UInt32 = 7
    UInt64 = 8
    Float = 9
    Double = 10
    Boolean = 11
    String = 12
    DateTime = 13
    Text = 14
    UUID = 15
    DataSet = 16
    Bytes = 17
    File = 18
    Template = 19
    PropertySet = 20
    PropertySetList = 21
    Int8Array = 22
    Int16Array = 23
    Int32Array = 24
    Int64Array = 25
    UInt8Array = 26
    UInt16Array = 27
    UInt32Array = 28
    UInt64Array = 29
    FloatArray = 30
    DoubleArray = 31
    BooleanArray = 32
    StringArray = 33
    DateTimeArray = 34


class Quality(IntEnum):
    """The three codes the `Quality` metric property may carry."""

    BAD = 0
    GOOD = 192
    STALE = 500


#: The quality codes as plain integers, for comparing against what an adapter
#: declares without forcing it to import the enumeration.
QUALITY_CODES = frozenset(int(code) for code in Quality)


@dataclass(frozen=True, slots=True)
class MetricSpec:
    """One metric a node or device declares at birth and may publish thereafter.

    The engineering range is optional because not every quantity has one, and
    an absent range is written as absent rather than as a zero a consumer would
    read as a real limit.
    """

    name: str
    datatype: DataType
    unit: str = "1"
    eng_low: float | None = None
    eng_high: float | None = None
    description: str = ""


@dataclass(frozen=True, slots=True)
class Metric:
    """One metric inside a payload, as a subscriber would read it.

    At birth a metric carries its name, its datatype, its alias, and its
    property set. In an aliased data message it carries the alias, the value,
    and the timestamp and nothing else, which is the rule that makes aliasing
    worth doing and the one a reimplementation most often gets wrong.
    """

    value: Any = None
    alias: int | None = None
    name: str | None = None
    datatype: DataType | None = None
    timestamp: int | None = None
    properties: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Payload:
    """A Sparkplug payload, before it reaches a wire format.

    `seq` is absent on an NDEATH alone, because the will is composed at CONNECT
    before the session has spent a sequence number, and any value written there
    would be one the session never actually reached.
    """

    timestamp: int | None
    metrics: tuple[Metric, ...] = ()
    seq: int | None = None


@dataclass(frozen=True, slots=True)
class Message:
    """One payload with the topic and delivery flags it is published under."""

    topic: str
    message_type: MessageType
    payload: Payload
    qos: int
    retain: bool


@dataclass(frozen=True, slots=True)
class Will:
    """The NDEATH an edge node registers as its MQTT Last Will at CONNECT.

    A separate type from `Message` because the delivery flags are the will's
    own and because registering it is part of the CONNECT packet rather than a
    publish. The ordering is the whole point: a will registered after the birth
    is a will the broker never publishes for the failure it exists to cover.
    """

    message: Message
    qos: int
    retain: bool


@dataclass(frozen=True, slots=True)
class NodeSpec:
    """The edge node a harness asks an adapter to build.

    `devices` maps a device id to the metrics that device declares at birth.
    The harness hands this to `EdgeNodeAdapter.new_session` rather than letting
    the adapter choose, because several checks compare what reached the topic
    against the identifiers and metric names that were handed in.
    """

    group_id: str
    edge_node_id: str
    node_metrics: tuple[MetricSpec, ...] = ()
    devices: Mapping[str, tuple[MetricSpec, ...]] = field(default_factory=dict)
