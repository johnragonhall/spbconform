"""One executable observation per in-scope assertion, and the session it reads.

A check takes a played trace and returns what it observed, or raises
`CheckFailed` carrying the observation that falsified the assertion. Every
check reads what an edge node put on the wire, or what it refused to put there.
None of them reach into an implementation's internal state, because an
assertion is about what a subscriber sees and a check that read private
attributes would pass for a node that publishes something else entirely.

`CHECKS` carries exactly one entry per in-scope row of the assertion table. An
assertion with no check cannot be reported as passing, and a check with no row
cannot report on anything, which the test suite enforces in both directions.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Any

from .adapter import EdgeNodeAdapter, EdgeNodeSession
from .model import (
    BDSEQ_METRIC,
    DEVICE_MESSAGE_TYPES,
    NAMESPACE,
    NODE_MESSAGE_TYPES,
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
)

# ------------------------------------------------------------------ the fixture

#: The edge node every check is played against. Two devices, because several
#: assertions are about one device's stream relative to another's and a
#: single-device node satisfies them by accident.
GROUP_ID = "conformance-group"
EDGE_NODE_ID = "edge-node-01"

#: Birthed first, and the device that later dies. Sorts before the second one,
#: so an implementation that births its devices in sorted order and one that
#: births them in the order it was handed produce the same sequence.
DEVICE_ONE = "device-a"

#: Birthed second, and the device that publishes data. Its metrics are the ones
#: the report-by-exception and alias checks are read from.
DEVICE_TWO = "device-b"

NODE_METRIC = "node_uptime_s"
DEVICE_ONE_METRIC = "motor_temp_c"
DEVICE_TWO_METRIC = "read_rate"

NODE_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec(name=NODE_METRIC, datatype=DataType.UInt64, unit="s"),
)
DEVICE_METRICS: Mapping[str, tuple[MetricSpec, ...]] = {
    DEVICE_ONE: (MetricSpec(name=DEVICE_ONE_METRIC, datatype=DataType.Double, unit="Cel"),),
    DEVICE_TWO: (
        MetricSpec(
            name=DEVICE_TWO_METRIC, datatype=DataType.Float, unit="1", eng_low=0.0, eng_high=1.0
        ),
        MetricSpec(name="unique_epcs", datatype=DataType.UInt32, unit="1"),
    ),
}

#: The node handed to `EdgeNodeAdapter.new_session` for every check.
FIXTURE = NodeSpec(
    group_id=GROUP_ID,
    edge_node_id=EDGE_NODE_ID,
    node_metrics=NODE_METRICS,
    devices=DEVICE_METRICS,
)

#: The node topic prefix every rendered topic in this module is compared against.
NODE_TOPIC = f"{NAMESPACE}/{GROUP_ID}"

#: A metric name no birth certificate declares, for the assertions about a data
#: message carrying something the birth set never introduced.
UNDECLARED_METRIC = "never_declared"


class CheckFailed(Exception):
    """One assertion's observation came out the wrong way."""


def _require(condition: object, detail: str) -> None:
    """Fail the assertion under check unless the observation holds."""
    if not condition:
        raise CheckFailed(detail)


def _refuses(call: Callable[[], object]) -> bool:
    """Whether the implementation refuses a call rather than performing it."""
    try:
        call()
    except REFUSALS:
        return True
    return False


# -------------------------------------------------------------------- the trace


@dataclass(frozen=True, slots=True)
class Trace:
    """One session played through the order the specification lays down.

    Every message the play produced is kept, because most assertions are about
    one message relative to another: a sequence number that follows the last
    one, a bdSeq that repeats the will's, a DBIRTH that carries the group its
    NBIRTH carried.
    """

    adapter: EdgeNodeAdapter
    session: EdgeNodeSession
    will: Any
    nbirth: Message
    dbirths: Mapping[str, Message]
    ndata: Message
    ddata: Message
    ddeath: Message
    rebirth: tuple[Message, ...]

    def metric(self, message: Message, name: str) -> Metric:
        """One named metric of a message."""
        for candidate in message.payload.metrics:
            if candidate.name == name:
                return candidate
        raise CheckFailed(f"{message.message_type} carries no metric named {name!r}")

    def fresh(self) -> EdgeNodeSession:
        """A second session, for probing an ordering the trace does not take."""
        return self.adapter.new_session(FIXTURE)

    def fresh_born(self) -> EdgeNodeSession:
        """A second session carried through its whole birth sequence."""
        session = self.fresh()
        session.connect()
        session.node_birth()
        for device in sorted(DEVICE_METRICS):
            session.device_birth(device)
        return session


def play(adapter: EdgeNodeAdapter) -> Trace:
    """Run one session through the order the specification lays down."""
    session = adapter.new_session(FIXTURE)
    will = session.connect()
    nbirth = session.node_birth()
    dbirths = {device: session.device_birth(device) for device in (DEVICE_ONE, DEVICE_TWO)}
    ndata = session.node_data({NODE_METRIC: 3})
    ddata = session.device_data(DEVICE_TWO, {DEVICE_TWO_METRIC: 0.94})
    ddeath = session.device_death(DEVICE_ONE)
    rebirth = session.handle_node_command({REBIRTH_METRIC: True})
    return Trace(
        adapter=adapter,
        session=session,
        will=will,
        nbirth=nbirth,
        dbirths=dbirths,
        ndata=ndata,
        ddata=ddata,
        ddeath=ddeath,
        rebirth=rebirth,
    )


#: A check reads a played trace and returns what it observed, or raises
#: `CheckFailed` carrying the observation that falsified the assertion.
Check = Callable[[Trace], str]


# -------------------------------------------------------------- check factories


def _declared_delivery(message_type: MessageType, qos: int, retain: bool) -> Check:
    """The declared delivery flags of one topic class match the assertion."""

    def check(trace: Trace) -> str:
        declared = trace.adapter.declared_delivery(message_type)
        _require(
            tuple(declared) == (qos, retain),
            f"{message_type} is declared at QoS {declared[0]} retain {declared[1]}",
        )
        return f"{message_type} declared at QoS {declared[0]} retain {declared[1]}"

    return check


def _published_delivery(
    pick: Callable[[Trace], Message], qos: int | None, retain: bool | None
) -> Check:
    """The delivery flags a produced message actually carries."""

    def check(trace: Trace) -> str:
        message = pick(trace)
        if qos is not None:
            _require(message.qos == qos, f"published at QoS {message.qos}")
        if retain is not None:
            _require(message.retain == retain, f"published with retain {message.retain}")
        return f"published at QoS {message.qos} retain {message.retain}"

    return check


def _topic_is(pick: Callable[[Trace], Message], expected: str) -> Check:
    """A produced message is addressed exactly as the assertion spells it."""

    def check(trace: Trace) -> str:
        topic = pick(trace).topic
        _require(topic == expected, f"addressed {topic!r}, not {expected!r}")
        return f"addressed {topic!r}"

    return check


def _payload_timestamp(pick: Callable[[Trace], Message]) -> Check:
    """A produced message carries a payload timestamp."""

    def check(trace: Trace) -> str:
        message = pick(trace)
        _require(message.payload.timestamp is not None, "payload carries no timestamp")
        return f"payload timestamp {message.payload.timestamp}"

    return check


def _seq_present(pick: Callable[[Trace], Message]) -> Check:
    """A produced message carries a sequence number inside the byte range."""

    def check(trace: Trace) -> str:
        seq = pick(trace).payload.seq
        _require(seq is not None, "payload carries no sequence number")
        assert seq is not None
        _require(0 <= seq < SEQUENCE_MODULUS, f"sequence number {seq} is outside the byte range")
        return f"sequence number {seq}"

    return check


def _seq_follows(pick: Callable[[Trace], Message], previous: Callable[[Trace], Message]) -> Check:
    """One message's sequence number is the next one after another's."""

    def check(trace: Trace) -> str:
        earlier, later = previous(trace).payload.seq, pick(trace).payload.seq
        _require(
            earlier is not None and later is not None,
            f"a sequence number is absent: {earlier} then {later}",
        )
        assert earlier is not None and later is not None
        expected = (earlier + 1) % SEQUENCE_MODULUS
        _require(later == expected, f"sequence went {earlier} then {later}, not {expected}")
        return f"sequence went {earlier} then {later}"

    return check


def _refuses_reserved(field: str) -> Check:
    """An identifier holding an MQTT wildcard or separator is refused."""

    def check(trace: Trace) -> str:
        for reserved in ("+", "#", "/"):
            ids = {"group_id": GROUP_ID, "edge_node_id": EDGE_NODE_ID, "device_id": DEVICE_TWO}
            ids[field] = f"bad{reserved}value"
            _require(
                _refuses(lambda values=ids: trace.adapter.validate_ids(**values)),
                f"a {field.replace('_', ' ')} holding {reserved!r} was accepted",
            )
        return f"a {field.replace('_', ' ')} holding '+', '#', or '/' is refused"

    return check


def _identifier_reaches_topic(pick: Callable[[Trace], Message], level: int, expected: str) -> Check:
    """An identifier arrives at its topic level as the UTF-8 string it was.

    Stronger than asking whether the value is a `str`, which every Python
    string is. The observation is that the identifier the caller handed over is
    the one a subscriber reads back off the wire, unchanged.
    """

    def check(trace: Trace) -> str:
        parts = pick(trace).topic.split("/")
        _require(len(parts) > level, f"the topic carries no level {level}")
        value = parts[level]
        _require(value == expected, f"topic level {level} reads {value!r}, not {expected!r}")
        _require(
            isinstance(value, str) and value.encode("utf-8").decode("utf-8") == value,
            f"{value!r} does not round-trip through UTF-8",
        )
        return f"{value!r} reaches topic level {level} unchanged"

    return check


def _every_metric(
    pick: Callable[[Trace], Message], holds: Callable[[Metric], bool], detail: str
) -> Check:
    """Every metric of one message satisfies a property."""

    def check(trace: Trace) -> str:
        message = pick(trace)
        _require(message.payload.metrics, f"{message.message_type} carries no metrics at all")
        for metric in message.payload.metrics:
            _require(holds(metric), f"{message.message_type} has a metric where not {detail}")
        return f"every {message.message_type} metric holds: {detail}"

    return check


def _only_changed(publish: Callable[[EdgeNodeSession], Message], expected: int) -> Check:
    """A data message carries only what the caller reported as changed."""

    def check(trace: Trace) -> str:
        message = publish(trace.fresh_born())
        count = len(message.payload.metrics)
        _require(count == expected, f"{count} metrics published for {expected} changed")
        return f"{count} metrics published for {expected} changed"

    return check


def _undeclared_refused(publish: Callable[[EdgeNodeSession], object]) -> Check:
    """A metric no birth certificate declared cannot reach a data message."""

    def check(trace: Trace) -> str:
        _require(
            _refuses(lambda: publish(trace.fresh_born())), "an undeclared metric was published"
        )
        return "an undeclared metric is refused"

    return check


def _data_before_all_births(publish: Callable[[EdgeNodeSession], object]) -> Check:
    """Data cannot leave while a device of this edge node has not birthed."""

    def check(trace: Trace) -> str:
        session = trace.fresh()
        session.connect()
        session.node_birth()
        session.device_birth(DEVICE_TWO)
        _require(
            _refuses(lambda: publish(session)),
            f"data was published while {DEVICE_ONE!r} had sent no DBIRTH",
        )
        return "data is refused until every device has birthed"

    return check


def _utc_timestamp(read: Callable[[Trace], int | None]) -> Check:
    """A timestamp that reaches the wire is a UTC wall-clock reading."""

    def check(trace: Trace) -> str:
        value = read(trace)
        _require(value is not None, "the timestamp is absent, so it reads as nothing at all")
        assert value is not None
        _require(
            value >= UTC_FLOOR_MS,
            f"timestamp {value} is below the year 2020 in epoch milliseconds, so it is a "
            "counter or a simulation instant rather than a UTC reading",
        )
        return f"timestamp {value} reads as UTC epoch milliseconds"

    return check


def _bdseq_datatype(pick: Callable[[Trace], Message]) -> Check:
    """The bdSeq metric carries the datatype the assertion names."""

    def check(trace: Trace) -> str:
        metric = trace.metric(pick(trace), BDSEQ_METRIC)
        _require(
            metric.datatype is DataType.Int64,
            f"bdSeq carries datatype {metric.datatype!r} rather than Int64",
        )
        return "bdSeq carries datatype Int64"

    return check


def _check_chronological(
    pick: Callable[[Trace], Message], follow: Callable[[Trace], Message]
) -> Check:
    """Metric timestamps within a payload do not move backwards."""

    def check(trace: Trace) -> str:
        for message in (pick(trace), follow(trace)):
            stamps = [m.timestamp for m in message.payload.metrics if m.timestamp is not None]
            for earlier, later in zip(stamps, stamps[1:], strict=False):
                _require(
                    later >= earlier,
                    f"a {message.message_type} metric list runs {earlier} then {later}",
                )
        return "metric timestamps within a payload do not move backwards"

    return check


# --------------------------------------------------------------- the selections


def _nbirth(trace: Trace) -> Message:
    return trace.nbirth


def _dbirth(trace: Trace) -> Message:
    return trace.dbirths[DEVICE_TWO]


def _dbirth_first(trace: Trace) -> Message:
    return trace.dbirths[DEVICE_ONE]


def _ndata(trace: Trace) -> Message:
    return trace.ndata


def _ddata(trace: Trace) -> Message:
    return trace.ddata


def _ddeath(trace: Trace) -> Message:
    return trace.ddeath


def _will(trace: Trace) -> Message:
    """The will's message, or a failure naming the missing registration."""
    if trace.will is None:
        raise CheckFailed("CONNECT handed back no will to register")
    return trace.will.message


# -------------------------------------------------------------- the named checks


def _check_topic_structure(trace: Trace) -> str:
    """A node topic is four levels and a device topic is five."""
    node = trace.nbirth.topic.split("/")
    device = trace.dbirths[DEVICE_TWO].topic.split("/")
    _require(len(node) == 4, f"a node topic came out with {len(node)} levels")
    _require(len(device) == 5, f"a device topic came out with {len(device)} levels")
    _require(node[0] == device[0] == NAMESPACE, "the first level is not the namespace")
    return "node topics are four levels and device topics are five"


def _check_namespace(trace: Trace) -> str:
    """The namespace level is the Sparkplug B constant."""
    level = trace.nbirth.topic.split("/")[0]
    _require(level == NAMESPACE, f"the first topic level is {level!r}, not {NAMESPACE!r}")
    return f"the namespace level is {NAMESPACE!r}"


def _check_device_id_required(trace: Trace) -> str:
    """A device message type refuses to render without a device id."""
    for message_type in DEVICE_MESSAGE_TYPES:
        _require(
            _refuses(lambda mt=message_type: trace.session.topic_for(mt)),
            f"{message_type} rendered a topic with no device id",
        )
        rendered = trace.session.topic_for(message_type, device_id=DEVICE_TWO)
        _require(rendered.endswith(f"/{DEVICE_TWO}"), f"{message_type} dropped the device id")
    return "DBIRTH, DDEATH, DDATA, and DCMD carry a device id level"


def _check_device_id_refused(trace: Trace) -> str:
    """A node message type refuses a device id it has no level for."""
    for message_type in NODE_MESSAGE_TYPES:
        _require(
            _refuses(lambda mt=message_type: trace.session.topic_for(mt, device_id=DEVICE_TWO)),
            f"{message_type} rendered a topic carrying a device id",
        )
    _require(
        _refuses(lambda: trace.session.topic_for(MessageType.STATE)),
        "STATE rendered on an edge node topic",
    )
    return "NBIRTH, NDEATH, NDATA, NCMD, and STATE carry no device id level"


def _check_unique_device_id(trace: Trace) -> str:
    """Two devices of one edge node are addressed apart."""
    topics = {device: message.topic for device, message in trace.dbirths.items()}
    _require(len(set(topics.values())) == len(topics), "two devices share a DBIRTH topic")
    return f"{len(topics)} devices are addressed apart"


def _check_ncmd_topic(trace: Trace) -> str:
    """The NCMD topic is the node form."""
    expected = f"{NODE_TOPIC}/NCMD/{EDGE_NODE_ID}"
    rendered = trace.session.topic_for(MessageType.NCMD)
    _require(rendered == expected, f"NCMD addressed {rendered!r}, not {expected!r}")
    return f"NCMD addressed {rendered!r}"


def _check_dcmd_topic(trace: Trace) -> str:
    """The DCMD topic is the device form."""
    expected = f"{NODE_TOPIC}/DCMD/{EDGE_NODE_ID}/{DEVICE_TWO}"
    rendered = trace.session.topic_for(MessageType.DCMD, device_id=DEVICE_TWO)
    _require(rendered == expected, f"DCMD addressed {rendered!r}, not {expected!r}")
    return f"DCMD addressed {rendered!r}"


def _check_dbirth_matches_node(trace: Trace) -> str:
    """A DBIRTH repeats the group and edge node of the NBIRTH before it."""
    node = trace.nbirth.topic.split("/")
    device = trace.dbirths[DEVICE_TWO].topic.split("/")
    _require(len(node) > 3 and len(device) > 3, "a topic is too short to compare")
    _require(device[1] == node[1], "the DBIRTH group id differs from the NBIRTH's")
    _require(device[3] == node[3], "the DBIRTH edge node id differs from the NBIRTH's")
    return f"the DBIRTH repeats group {node[1]!r} and edge node {node[3]!r}"


def _check_nbirth_seq_zero(trace: Trace) -> str:
    """The NBIRTH opens the sequence at zero."""
    seq = trace.nbirth.payload.seq
    _require(seq == 0, f"the NBIRTH carries sequence number {seq}")
    return "the NBIRTH carries sequence number 0"


def _check_seq_always_present(trace: Trace) -> str:
    """Every message except the NDEATH carries a sequence number."""
    for message in (
        trace.nbirth,
        *trace.dbirths.values(),
        trace.ndata,
        trace.ddata,
        trace.ddeath,
    ):
        _require(
            message.payload.seq is not None, f"{message.message_type} carries no sequence number"
        )
    _require(_will(trace).payload.seq is None, "the NDEATH carries a sequence number")
    return "every message except the NDEATH carries a sequence number"


def _check_seq_wraps(trace: Trace) -> str:
    """The sequence rises by one and returns to zero after 255."""
    session = trace.fresh_born()
    seen = [session.node_data({NODE_METRIC: step}).payload.seq for step in range(300)]
    _require(all(value is not None for value in seen), "a data message carried no sequence number")
    previous = seen[0]
    assert previous is not None
    for value in seen[1:]:
        assert value is not None
        _require(
            value == (previous + 1) % SEQUENCE_MODULUS,
            f"the sequence went {previous} then {value}",
        )
        previous = value
    _require(0 in seen and 255 in seen, "the sequence never reached the wrap")
    return "the sequence rises by one and returns to zero after 255"


def _check_ndeath_payload(trace: Trace) -> str:
    """The NDEATH carries the bdSeq metric alone."""
    metrics = _will(trace).payload.metrics
    _require(len(metrics) == 1, f"the NDEATH carries {len(metrics)} metrics")
    _require(metrics[0].name == BDSEQ_METRIC, f"the NDEATH metric is {metrics[0].name!r}")
    return "the NDEATH carries only the bdSeq metric"


def _check_ndeath_seq_absent(trace: Trace) -> str:
    """The NDEATH carries no sequence number."""
    seq = _will(trace).payload.seq
    _require(seq is None, f"the NDEATH carries sequence number {seq}")
    return "the NDEATH carries no sequence number"


def _check_will_is_ndeath(trace: Trace) -> str:
    """Opening the session hands back an NDEATH to register as the will."""
    message = _will(trace)
    _require(
        message.message_type is MessageType.NDEATH,
        f"the will is a {message.message_type}",
    )
    return "the will registered at CONNECT is an NDEATH"


def _check_will_qos(trace: Trace) -> str:
    """The will is registered at QoS 1."""
    _require(trace.will is not None, "CONNECT handed back no will to register")
    _require(trace.will.qos == 1, f"the will is registered at QoS {trace.will.qos}")
    return "the will is registered at QoS 1"


def _check_will_retain(trace: Trace) -> str:
    """The will is registered with the retain flag clear."""
    _require(trace.will is not None, "CONNECT handed back no will to register")
    _require(trace.will.retain is False, f"the will is registered with retain {trace.will.retain}")
    return "the will is registered with the retain flag clear"


def _check_bdseq_present(trace: Trace) -> str:
    """The NBIRTH carries a bdSeq metric."""
    trace.metric(trace.nbirth, BDSEQ_METRIC)
    return "the NBIRTH carries a bdSeq metric"


def _check_bdseq_matches_will(trace: Trace) -> str:
    """The NBIRTH bdSeq repeats the will's."""
    born = trace.metric(trace.nbirth, BDSEQ_METRIC).value
    willed = trace.metric(_will(trace), BDSEQ_METRIC).value
    _require(born == willed, f"the NBIRTH carries bdSeq {born} and the will carries {willed}")
    return f"the NBIRTH and the will both carry bdSeq {born}"


def _check_bdseq_increments(trace: Trace) -> str:
    """bdSeq opens at zero and advances by one for each session."""
    session = trace.fresh()
    seen = []
    for _ in range(SEQUENCE_MODULUS + 2):
        will = session.connect()
        _require(will is not None, "CONNECT handed back no will to read bdSeq from")
        seen.append(next(m.value for m in will.message.payload.metrics if m.name == BDSEQ_METRIC))
    _require(seen[0] == 0, f"the first session opened bdSeq at {seen[0]}")
    for index in range(1, len(seen)):
        _require(
            seen[index] == (seen[index - 1] + 1) % SEQUENCE_MODULUS,
            f"bdSeq went {seen[index - 1]} then {seen[index]}",
        )
    return "bdSeq opens at zero, advances by one, and returns to zero after 255"


def _check_rebirth_metric_present(trace: Trace) -> str:
    """The NBIRTH declares the rebirth command metric."""
    trace.metric(trace.nbirth, REBIRTH_METRIC)
    return f"the NBIRTH declares {REBIRTH_METRIC!r}"


def _check_rebirth_metric_datatype(trace: Trace) -> str:
    """The rebirth command metric is a boolean."""
    metric = trace.metric(trace.nbirth, REBIRTH_METRIC)
    _require(metric.datatype is DataType.Boolean, f"its datatype is {metric.datatype!r}")
    return f"{REBIRTH_METRIC!r} carries the Boolean datatype"


def _check_rebirth_metric_value(trace: Trace) -> str:
    """The rebirth command metric is born false."""
    metric = trace.metric(trace.nbirth, REBIRTH_METRIC)
    _require(metric.value is False, f"its birth value is {metric.value!r}")
    return f"{REBIRTH_METRIC!r} is born holding false"


def _check_rebirth_metric_unaliased(trace: Trace) -> str:
    """The rebirth command metric is born without an alias."""
    metric = trace.metric(trace.nbirth, REBIRTH_METRIC)
    _require(
        metric.alias is None,
        f"the NBIRTH gives {REBIRTH_METRIC!r} alias {metric.alias} while the edge "
        "node uses aliases",
    )
    return f"{REBIRTH_METRIC!r} is born with no alias"


def _check_birth_metrics_named_and_aliased(trace: Trace) -> str:
    """Birth metrics carry both a name and an alias.

    The rebirth command metric is left out of the sweep, because a separate
    assertion takes it out of the alias table for an edge node that aliases.
    """
    swept = 0
    for message in (trace.nbirth, *trace.dbirths.values()):
        for metric in message.payload.metrics:
            if metric.name == REBIRTH_METRIC:
                continue
            _require(metric.name is not None, f"a {message.message_type} metric carries no name")
            _require(
                metric.alias is not None,
                f"{message.message_type} metric {metric.name!r} carries no alias",
            )
            swept += 1
    _require(swept, "the birth certificates declare no metrics at all")
    return f"{swept} birth metrics carry both a name and an alias"


def _check_data_metrics_aliased_only(trace: Trace) -> str:
    """Data metrics carry the alias and leave the name out."""
    for message in (trace.ndata, trace.ddata):
        _require(message.payload.metrics, f"{message.message_type} carries no metrics at all")
        for metric in message.payload.metrics:
            _require(metric.alias is not None, f"a {message.message_type} metric carries no alias")
            _require(
                metric.name is None,
                f"a {message.message_type} metric still carries the name {metric.name!r}",
            )
    return "data metrics carry only the alias"


def _check_alias_uniqueness(trace: Trace) -> str:
    """Aliases are unique across the whole edge node.

    Read off the birth certificates rather than out of the implementation,
    because the alias space a subscriber has to resolve against is the one the
    births announced, not whatever table the publisher keeps internally.
    """
    aliases = [
        metric.alias
        for message in (trace.nbirth, *trace.dbirths.values())
        for metric in message.payload.metrics
        if metric.alias is not None
    ]
    _require(aliases, "no birth metric carries an alias, so the alias space cannot be read")
    _require(len(set(aliases)) == len(aliases), "two metrics of this edge node share an alias")
    _require(all(alias >= 1 for alias in aliases), "an alias of zero was assigned")
    return f"{len(aliases)} birth metrics hold {len(set(aliases))} distinct aliases"


def _check_metric_timestamps(trace: Trace) -> str:
    """Every metric of a birth or data message carries a timestamp."""
    for message in (trace.nbirth, *trace.dbirths.values(), trace.ndata, trace.ddata):
        _require(message.payload.metrics, f"{message.message_type} carries no metrics at all")
        for metric in message.payload.metrics:
            _require(
                metric.timestamp is not None,
                f"a {message.message_type} metric carries no timestamp",
            )
    return "every birth and data metric carries a timestamp"


def _check_datatype_enumerated(trace: Trace) -> str:
    """Every birth datatype is one the payload definition enumerates."""
    for message in (trace.nbirth, *trace.dbirths.values()):
        _require(message.payload.metrics, f"{message.message_type} carries no metrics at all")
        for metric in message.payload.metrics:
            _require(
                isinstance(metric.datatype, DataType),
                f"a {message.message_type} metric carries datatype {metric.datatype!r}",
            )
    return "every birth datatype is an enumerated value"


def _check_quality_codes(trace: Trace) -> str:
    """No quality code outside the three the specification defines reaches a payload.

    Read from two places, because either one alone can be silent. The codes the
    implementation says it can write catch a table that has drifted; the codes
    that actually reached the fixture's payloads catch a table that is right
    and a publisher that is not.
    """
    declared = frozenset(trace.adapter.quality_codes())
    stray = sorted(declared - QUALITY_CODES)
    _require(not stray, f"the implementation declares quality codes {stray}")
    observed: list[int] = []
    for message in (trace.nbirth, *trace.dbirths.values(), trace.ndata, trace.ddata):
        for metric in message.payload.metrics:
            value = metric.properties.get("Quality")
            if value is None:
                continue
            try:
                code = int(value)
            except (TypeError, ValueError):
                raise CheckFailed(f"a metric carries quality {value!r}") from None
            _require(code in QUALITY_CODES, f"a metric carries quality {code}")
            observed.append(code)
    if not declared and not observed:
        return "no Quality property is declared or published, so no code was observed"
    return (
        f"{len(declared)} declared and {len(observed)} published quality codes are 0, 192, or 500"
    )


def _check_connect_first(trace: Trace) -> str:
    """Nothing is published before the session is opened."""
    _require(_refuses(trace.fresh().node_birth), "an NBIRTH was published before CONNECT")
    return "publishing before CONNECT is refused"


def _check_will_returned(trace: Trace) -> str:
    """Opening the session hands back a will to register."""
    registration = trace.fresh().connect()
    _require(registration is not None, "CONNECT returned no will registration")
    _require(
        getattr(registration, "message", None) is not None,
        "the will registration carries no message",
    )
    return "CONNECT hands back a will registration"


def _check_birth_first(trace: Trace) -> str:
    """A data message before the birth certificate is refused."""
    session = trace.fresh()
    session.connect()
    _require(
        _refuses(lambda: session.node_data({NODE_METRIC: 1})),
        "NDATA was published before the NBIRTH",
    )
    return "a data message before the birth certificate is refused"


def _check_dbirth_after_nbirth(trace: Trace) -> str:
    """A DBIRTH before its NBIRTH is refused."""
    session = trace.fresh()
    session.connect()
    _require(
        _refuses(lambda: session.device_birth(DEVICE_TWO)),
        "a DBIRTH was published before the NBIRTH",
    )
    return "a DBIRTH before the NBIRTH is refused"


def _check_ddeath(trace: Trace) -> str:
    """Losing a device produces a DDEATH addressed to it."""
    _require(
        trace.ddeath.message_type is MessageType.DDEATH,
        f"losing a device produced a {trace.ddeath.message_type}",
    )
    _require(
        trace.ddeath.topic.endswith(f"/{DEVICE_ONE}"),
        f"the DDEATH addressed {trace.ddeath.topic!r}",
    )
    return "losing a device produces a DDEATH on the device's topic"


def _check_rebirth_stops_data(trace: Trace) -> str:
    """A rebirth request produces no data message."""
    kinds = [message.message_type for message in trace.rebirth]
    _require(kinds, "the rebirth request produced nothing")
    for kind in kinds:
        _require(
            kind not in (MessageType.NDATA, MessageType.DDATA),
            f"the rebirth sequence carries a {kind}",
        )
    return f"the rebirth sequence carries only {sorted({str(k) for k in kinds})}"


def _check_rebirth_sequence(trace: Trace) -> str:
    """A rebirth request produces the NBIRTH and every DBIRTH."""
    _require(bool(trace.rebirth), "the rebirth request produced nothing")
    _require(
        trace.rebirth[0].message_type is MessageType.NBIRTH,
        f"the rebirth opened with a {trace.rebirth[0].message_type}",
    )
    reborn = {m.topic.rsplit("/", 1)[-1] for m in trace.rebirth[1:]}
    _require(
        reborn == set(DEVICE_METRICS),
        f"the rebirth carried DBIRTHs for {sorted(reborn)}",
    )
    return "a rebirth produces the NBIRTH and a DBIRTH for every device"


def _check_rebirth_keeps_bdseq(trace: Trace) -> str:
    """A rebirth keeps the session's bdSeq."""
    _require(bool(trace.rebirth), "the rebirth request produced nothing")
    willed = trace.metric(_will(trace), BDSEQ_METRIC).value
    reborn = trace.metric(trace.rebirth[0], BDSEQ_METRIC).value
    _require(reborn == willed, f"the rebirth NBIRTH carries bdSeq {reborn}, the will {willed}")
    return f"the rebirth NBIRTH keeps bdSeq {reborn}"


def _check_rebirth_request_name(trace: Trace) -> str:
    """Only the rebirth command metric triggers a rebirth."""
    session = trace.fresh_born()
    _require(
        session.handle_node_command({"Node Control/Something Else": True}) == (),
        "a command under another name triggered a rebirth",
    )
    _require(
        bool(session.handle_node_command({REBIRTH_METRIC: True})),
        f"a command named {REBIRTH_METRIC!r} triggered nothing",
    )
    return f"a rebirth is triggered by {REBIRTH_METRIC!r} alone"


def _check_rebirth_request_value(trace: Trace) -> str:
    """Only a true value triggers a rebirth."""
    session = trace.fresh_born()
    _require(
        session.handle_node_command({REBIRTH_METRIC: False}) == (),
        "a false rebirth command triggered a rebirth",
    )
    _require(
        bool(session.handle_node_command({REBIRTH_METRIC: True})),
        "a true rebirth command triggered nothing",
    )
    return "a rebirth is triggered by a true value alone"


def _check_intentional_disconnect(trace: Trace) -> str:
    """Closing the session produces an NDEATH to publish."""
    message = trace.fresh_born().disconnect()
    _require(
        message is not None,
        "the session offers no close that publishes an NDEATH, so an edge node shutting down "
        "on purpose leaves its death to the broker's will delivery",
    )
    assert message is not None
    _require(
        message.message_type is MessageType.NDEATH,
        f"closing the session produced a {message.message_type}",
    )
    return "closing the session produces an NDEATH"


def _check_case_distinct_ids(trace: Trace) -> str:
    """Two identifiers differing only by letter case cannot collide.

    Two ways an implementation satisfies this, and both are accepted. It may
    refuse the identifier outright, in which case the pair cannot exist; or it
    may carry case through to the topic, in which case the pair is addressed
    apart. What fails is an implementation that folds case, because then two
    ids the deployment believes are distinct arrive at one topic.
    """
    refused = 0
    for label, altered in (
        ("group id", replace(FIXTURE, group_id=GROUP_ID.upper())),
        ("edge node id", replace(FIXTURE, edge_node_id=EDGE_NODE_ID.upper())),
    ):
        plain = _rendered_or_refused(trace, FIXTURE, MessageType.NBIRTH)
        shouted = _rendered_or_refused(trace, altered, MessageType.NBIRTH)
        if shouted is None:
            refused += 1
            continue
        _require(plain != shouted, f"a {label} differing only by case reached the same topic")
    plain_device = _device_topic_or_refused(trace, DEVICE_TWO)
    shouted_device = _device_topic_or_refused(trace, DEVICE_TWO.upper())
    if shouted_device is None:
        refused += 1
    else:
        _require(
            plain_device != shouted_device,
            "a device id differing only by case reached the same topic",
        )
    return f"identifiers differing only by case are addressed apart or refused ({refused} refused)"


def _rendered_or_refused(trace: Trace, spec: NodeSpec, message_type: MessageType) -> str | None:
    """One node topic under a given spec, or None if the spec is refused."""
    try:
        return trace.adapter.new_session(spec).topic_for(message_type)
    except REFUSALS:
        return None


def _device_topic_or_refused(trace: Trace, device_id: str) -> str | None:
    """One device topic, or None if the device id is refused."""
    try:
        return trace.session.topic_for(MessageType.DBIRTH, device_id=device_id)
    except REFUSALS:
        return None


def _check_case_distinct_metric_names(trace: Trace) -> str:
    """Two metric names differing only by case cannot both be published."""
    colliding = (
        MetricSpec(name="Read_Rate", datatype=DataType.Float, unit="1"),
        MetricSpec(name="read_rate", datatype=DataType.Float, unit="1"),
    )
    spec = replace(FIXTURE, node_metrics=(), devices={DEVICE_TWO: colliding})
    try:
        session = trace.adapter.new_session(spec)
        session.connect()
        session.node_birth()
        birth = session.device_birth(DEVICE_TWO)
    except REFUSALS:
        return "metric names that differ only by case are refused"
    names = [metric.name for metric in birth.payload.metrics if metric.name is not None]
    folded = [name.lower() for name in names]
    _require(
        len(set(folded)) == len(folded),
        "a DBIRTH carried two metric names that differ only by case",
    )
    return "metric names that differ only by case are refused"


#: One executable check per in-scope assertion. An assertion with no check
#: cannot be reported as passing, which the test suite enforces.
CHECKS: Mapping[str, Check] = {
    # ----------------------------------------------------------- identifiers
    "tck-id-intro-group-id-string": _identifier_reaches_topic(_nbirth, 1, GROUP_ID),
    "tck-id-intro-edge-node-id-string": _identifier_reaches_topic(_nbirth, 3, EDGE_NODE_ID),
    "tck-id-intro-device-id-string": _identifier_reaches_topic(_dbirth, 4, DEVICE_TWO),
    "tck-id-intro-group-id-chars": _refuses_reserved("group_id"),
    "tck-id-intro-edge-node-id-chars": _refuses_reserved("edge_node_id"),
    "tck-id-intro-device-id-chars": _refuses_reserved("device_id"),
    "tck-id-topic-structure-namespace-valid-group-id": _refuses_reserved("group_id"),
    "tck-id-topic-structure-namespace-valid-edge-node-id": _refuses_reserved("edge_node_id"),
    "tck-id-topic-structure-namespace-valid-device-id": _refuses_reserved("device_id"),
    "tck-id-topic-structure-namespace-unique-device-id": _check_unique_device_id,
    "tck-id-case-sensitivity-sparkplug-ids": _check_case_distinct_ids,
    "tck-id-case-sensitivity-metric-names": _check_case_distinct_metric_names,
    # ---------------------------------------------------------------- topics
    "tck-id-topic-structure": _check_topic_structure,
    "tck-id-topic-structure-namespace-a": _check_namespace,
    "tck-id-topic-structure-namespace-device-id-associated-message-types": (
        _check_device_id_required
    ),
    "tck-id-topic-structure-namespace-device-id-non-associated-message-types": (
        _check_device_id_refused
    ),
    "tck-id-topics-nbirth-topic": _topic_is(_nbirth, f"{NODE_TOPIC}/NBIRTH/{EDGE_NODE_ID}"),
    "tck-id-topics-ndata-topic": _topic_is(_ndata, f"{NODE_TOPIC}/NDATA/{EDGE_NODE_ID}"),
    "tck-id-topics-ndeath-topic": _topic_is(_will, f"{NODE_TOPIC}/NDEATH/{EDGE_NODE_ID}"),
    "tck-id-topics-ncmd-topic": _check_ncmd_topic,
    "tck-id-topics-dbirth-topic": _topic_is(
        _dbirth, f"{NODE_TOPIC}/DBIRTH/{EDGE_NODE_ID}/{DEVICE_TWO}"
    ),
    "tck-id-topics-ddata-topic": _topic_is(
        _ddata, f"{NODE_TOPIC}/DDATA/{EDGE_NODE_ID}/{DEVICE_TWO}"
    ),
    "tck-id-topics-ddeath-topic": _topic_is(
        _ddeath, f"{NODE_TOPIC}/DDEATH/{EDGE_NODE_ID}/{DEVICE_ONE}"
    ),
    "tck-id-topics-dcmd-topic": _check_dcmd_topic,
    "tck-id-message-flow-edge-node-birth-publish-nbirth-topic": _topic_is(
        _nbirth, f"{NODE_TOPIC}/NBIRTH/{EDGE_NODE_ID}"
    ),
    "tck-id-message-flow-edge-node-birth-publish-will-message-topic": _topic_is(
        _will, f"{NODE_TOPIC}/NDEATH/{EDGE_NODE_ID}"
    ),
    "tck-id-message-flow-device-birth-publish-dbirth-topic": _topic_is(
        _dbirth, f"{NODE_TOPIC}/DBIRTH/{EDGE_NODE_ID}/{DEVICE_TWO}"
    ),
    "tck-id-message-flow-device-birth-publish-dbirth-match-edge-node-topic": (
        _check_dbirth_matches_node
    ),
    # -------------------------------------------------------- delivery flags
    "tck-id-topics-nbirth-mqtt": _published_delivery(_nbirth, 0, False),
    "tck-id-topics-ndata-mqtt": _published_delivery(_ndata, 0, False),
    "tck-id-topics-dbirth-mqtt": _published_delivery(_dbirth, 0, False),
    "tck-id-topics-ddata-mqtt": _published_delivery(_ddata, 0, False),
    "tck-id-topics-ddeath-mqtt": _published_delivery(_ddeath, 0, False),
    "tck-id-topics-ncmd-mqtt": _declared_delivery(MessageType.NCMD, 0, False),
    "tck-id-topics-dcmd-mqtt": _declared_delivery(MessageType.DCMD, 0, False),
    "tck-id-payloads-nbirth-qos": _published_delivery(_nbirth, 0, None),
    "tck-id-payloads-nbirth-retain": _published_delivery(_nbirth, None, False),
    "tck-id-payloads-dbirth-qos": _published_delivery(_dbirth, 0, None),
    "tck-id-payloads-dbirth-retain": _published_delivery(_dbirth, None, False),
    "tck-id-payloads-ndata-qos": _published_delivery(_ndata, 0, None),
    "tck-id-payloads-ndata-retain": _published_delivery(_ndata, None, False),
    "tck-id-payloads-ddata-qos": _published_delivery(_ddata, 0, None),
    "tck-id-payloads-ddata-retain": _published_delivery(_ddata, None, False),
    "tck-id-payloads-ncmd-qos": _declared_delivery(MessageType.NCMD, 0, False),
    "tck-id-payloads-ncmd-retain": _declared_delivery(MessageType.NCMD, 0, False),
    "tck-id-payloads-dcmd-qos": _declared_delivery(MessageType.DCMD, 0, False),
    "tck-id-payloads-dcmd-retain": _declared_delivery(MessageType.DCMD, 0, False),
    "tck-id-message-flow-edge-node-birth-publish-nbirth-qos": _published_delivery(_nbirth, 0, None),
    "tck-id-message-flow-edge-node-birth-publish-nbirth-retained": _published_delivery(
        _nbirth, None, False
    ),
    "tck-id-message-flow-device-birth-publish-dbirth-qos": _published_delivery(_dbirth, 0, None),
    "tck-id-message-flow-device-birth-publish-dbirth-retained": _published_delivery(
        _dbirth, None, False
    ),
    "tck-id-payloads-ndeath-will-message-qos": _check_will_qos,
    "tck-id-payloads-ndeath-will-message-retain": _check_will_retain,
    "tck-id-message-flow-edge-node-birth-publish-will-message-qos": _check_will_qos,
    "tck-id-message-flow-edge-node-birth-publish-will-message-will-retained": _check_will_retain,
    "tck-id-host-topic-phid-birth-qos": _declared_delivery(MessageType.STATE, 1, True),
    "tck-id-host-topic-phid-birth-retain": _declared_delivery(MessageType.STATE, 1, True),
    # ---------------------------------------------------------- the sequence
    "tck-id-topics-nbirth-seq-num": _check_nbirth_seq_zero,
    "tck-id-payloads-sequence-num-always-included": _check_seq_always_present,
    "tck-id-payloads-sequence-num-req-nbirth": _seq_present(_nbirth),
    "tck-id-payloads-sequence-num-incrementing": _check_seq_wraps,
    "tck-id-payloads-nbirth-seq": _seq_present(_nbirth),
    "tck-id-message-flow-edge-node-birth-publish-nbirth-payload-seq": _seq_present(_nbirth),
    "tck-id-topics-dbirth-seq": _seq_follows(_dbirth_first, _nbirth),
    "tck-id-payloads-dbirth-seq": _seq_present(_dbirth),
    "tck-id-payloads-dbirth-seq-inc": _seq_follows(_dbirth_first, _nbirth),
    "tck-id-message-flow-device-birth-publish-dbirth-payload-seq": _seq_follows(
        _dbirth_first, _nbirth
    ),
    "tck-id-topics-ndata-seq-num": _seq_follows(_ndata, _dbirth),
    "tck-id-payloads-ndata-seq": _seq_present(_ndata),
    "tck-id-payloads-ndata-seq-inc": _seq_follows(_ndata, _dbirth),
    "tck-id-topics-ddata-seq-num": _seq_follows(_ddata, _ndata),
    "tck-id-payloads-ddata-seq": _seq_present(_ddata),
    "tck-id-payloads-ddata-seq-inc": _seq_follows(_ddata, _ndata),
    "tck-id-topics-ddeath-seq-num": _seq_follows(_ddeath, _ddata),
    "tck-id-payloads-ddeath-seq": _seq_present(_ddeath),
    "tck-id-payloads-ddeath-seq-inc": _seq_follows(_ddeath, _ddata),
    "tck-id-payloads-ddeath-seq-number": _seq_present(_ddeath),
    "tck-id-topics-ndeath-seq": _check_ndeath_seq_absent,
    "tck-id-payloads-ndeath-seq": _check_ndeath_seq_absent,
    # ----------------------------------------------------------------- the will
    "tck-id-message-flow-edge-node-birth-publish-connect": _check_connect_first,
    "tck-id-message-flow-edge-node-birth-publish-will-message": _check_will_returned,
    "tck-id-payloads-ndeath-will-message": _check_will_is_ndeath,
    "tck-id-topics-ndeath-payload": _check_ndeath_payload,
    "tck-id-payloads-ndeath-bdseq": _check_bdseq_matches_will,
    "tck-id-payloads-ndeath-will-message-publisher": _check_intentional_disconnect,
    "tck-id-operational-behavior-edge-node-intentional-disconnect-ndeath": (
        _check_intentional_disconnect
    ),
    # ---------------------------------------------------------------- the bdSeq
    "tck-id-topics-nbirth-bdseq-included": _check_bdseq_present,
    "tck-id-payloads-nbirth-bdseq": _check_bdseq_present,
    "tck-id-topics-nbirth-bdseq-matching": _check_bdseq_matches_will,
    "tck-id-payloads-nbirth-bdseq-repeat": _check_bdseq_matches_will,
    "tck-id-topics-nbirth-bdseq-increment": _check_bdseq_increments,
    "tck-id-message-flow-edge-node-birth-publish-will-message-payload-bdSeq": _bdseq_datatype(
        _will
    ),
    "tck-id-message-flow-edge-node-birth-publish-nbirth-payload-bdSeq": _bdseq_datatype(_nbirth),
    # -------------------------------------------------------------- the metrics
    "tck-id-topics-nbirth-metrics": _every_metric(
        _nbirth,
        lambda m: m.name is not None and m.datatype is not None,
        "a metric carries a name and a datatype",
    ),
    "tck-id-topics-dbirth-metrics": _every_metric(
        _dbirth,
        lambda m: m.name is not None and m.datatype is not None,
        "a metric carries a name and a datatype",
    ),
    "tck-id-payloads-name-requirement": _every_metric(
        _nbirth, lambda m: m.name is not None, "a metric carries its name"
    ),
    "tck-id-payloads-alias-birth-requirement": _check_birth_metrics_named_and_aliased,
    "tck-id-payloads-alias-data-cmd-requirement": _check_data_metrics_aliased_only,
    "tck-id-payloads-alias-uniqueness": _check_alias_uniqueness,
    "tck-id-payloads-name-birth-data-requirement": _check_metric_timestamps,
    "tck-id-payloads-metric-datatype-req": _every_metric(
        _dbirth, lambda m: m.datatype is not None, "a metric carries its datatype"
    ),
    "tck-id-payloads-metric-datatype-not-req": _every_metric(
        _ddata, lambda m: m.datatype is None, "a metric leaves the datatype out"
    ),
    "tck-id-payloads-metric-datatype-value": _check_datatype_enumerated,
    "tck-id-payloads-propertyset-quality-value-value": _check_quality_codes,
    "tck-id-topics-nbirth-metric-reqs": _undeclared_refused(
        lambda s: s.node_data({UNDECLARED_METRIC: 1})
    ),
    "tck-id-topics-dbirth-metric-reqs": _undeclared_refused(
        lambda s: s.device_data(DEVICE_TWO, {UNDECLARED_METRIC: 1})
    ),
    "tck-id-operational-behavior-data-publish-nbirth": _undeclared_refused(
        lambda s: s.node_data({UNDECLARED_METRIC: 1})
    ),
    "tck-id-operational-behavior-data-publish-dbirth": _undeclared_refused(
        lambda s: s.device_data(DEVICE_TWO, {UNDECLARED_METRIC: 1})
    ),
    "tck-id-topics-nbirth-rebirth-metric": _check_rebirth_metric_present,
    "tck-id-payloads-nbirth-rebirth-req": _check_rebirth_metric_value,
    "tck-id-operational-behavior-data-commands-rebirth-name": _check_rebirth_metric_present,
    "tck-id-operational-behavior-data-commands-rebirth-datatype": _check_rebirth_metric_datatype,
    "tck-id-operational-behavior-data-commands-rebirth-value": _check_rebirth_metric_value,
    "tck-id-operational-behavior-data-commands-rebirth-name-aliases": (
        _check_rebirth_metric_unaliased
    ),
    # ------------------------------------------------------------- timestamps
    "tck-id-topics-nbirth-timestamp": _payload_timestamp(_nbirth),
    "tck-id-topics-dbirth-timestamp": _payload_timestamp(_dbirth),
    "tck-id-topics-ndata-timestamp": _payload_timestamp(_ndata),
    "tck-id-topics-ddata-timestamp": _payload_timestamp(_ddata),
    "tck-id-payloads-nbirth-timestamp": _payload_timestamp(_nbirth),
    "tck-id-payloads-dbirth-timestamp": _payload_timestamp(_dbirth),
    "tck-id-payloads-ndata-timestamp": _payload_timestamp(_ndata),
    "tck-id-payloads-ddata-timestamp": _payload_timestamp(_ddata),
    "tck-id-payloads-ddeath-timestamp": _payload_timestamp(_ddeath),
    "tck-id-payloads-timestamp-in-UTC": _utc_timestamp(lambda t: t.nbirth.payload.timestamp),
    "tck-id-payloads-metric-timestamp-in-UTC": _utc_timestamp(
        lambda t: t.metric(t.nbirth, BDSEQ_METRIC).timestamp
    ),
    # ---------------------------------------------------------------- ordering
    "tck-id-principles-birth-certificates-order": _check_birth_first,
    "tck-id-message-flow-device-birth-publish-nbirth-wait": _check_dbirth_after_nbirth,
    "tck-id-payloads-dbirth-order": _data_before_all_births(
        lambda s: s.device_data(DEVICE_TWO, {DEVICE_TWO_METRIC: 0.5})
    ),
    "tck-id-payloads-ndata-order": _data_before_all_births(lambda s: s.node_data({NODE_METRIC: 1})),
    "tck-id-payloads-ddata-order": _data_before_all_births(
        lambda s: s.device_data(DEVICE_TWO, {DEVICE_TWO_METRIC: 0.5})
    ),
    "tck-id-operational-behavior-data-publish-nbirth-order": _check_chronological(_nbirth, _ndata),
    "tck-id-operational-behavior-data-publish-dbirth-order": _check_chronological(_dbirth, _ddata),
    # ----------------------------------------------------- report by exception
    "tck-id-principles-rbe-recommended": _only_changed(
        lambda s: s.device_data(DEVICE_TWO, {DEVICE_TWO_METRIC: 0.5}), 1
    ),
    "tck-id-topics-ndata-payload": _only_changed(lambda s: s.node_data({NODE_METRIC: 1}), 1),
    "tck-id-topics-ddata-payload": _only_changed(
        lambda s: s.device_data(DEVICE_TWO, {DEVICE_TWO_METRIC: 0.5}), 1
    ),
    "tck-id-operational-behavior-data-publish-nbirth-change": _only_changed(
        lambda s: s.node_data({NODE_METRIC: 1}), 1
    ),
    "tck-id-operational-behavior-data-publish-dbirth-change": _only_changed(
        lambda s: s.device_data(DEVICE_TWO, {DEVICE_TWO_METRIC: 0.5}), 1
    ),
    # --------------------------------------------------------------- lifecycle
    "tck-id-operational-behavior-device-ddeath": _check_ddeath,
    "tck-id-operational-behavior-data-commands-rebirth-action-1": _check_rebirth_stops_data,
    "tck-id-operational-behavior-data-commands-rebirth-action-2": _check_rebirth_sequence,
    "tck-id-operational-behavior-data-commands-rebirth-action-3": _check_rebirth_keeps_bdseq,
    "tck-id-operational-behavior-data-commands-ncmd-rebirth-name": _check_rebirth_request_name,
    "tck-id-operational-behavior-data-commands-ncmd-rebirth-value": _check_rebirth_request_value,
}
