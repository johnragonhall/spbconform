"""A conformant edge node, and the switches that break it one way at a time.

The harness needs something to check, so this is a small Sparkplug B edge-node
session written against `spbconform`'s own protocols. It exists for the test
suite and is not part of the distribution's public surface: it publishes no
bytes, opens no socket, and models only the session state the assertion checks
read. Reach for it as a worked example of an adapter, not as an MQTT client.

`Faults` is the other half. Every field breaks the session in one documented
way, and the mutation sweep in `test_mutations.py` plants each in turn and
records which assertions stop holding. A check that no fault can turn over is a
check that would report a pass for an edge node doing the opposite, so the
sweep failing is the harness telling you a check is measuring nothing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any

from spbconform import (
    BDSEQ_METRIC,
    NAMESPACE,
    QUALITY_CODES,
    REBIRTH_METRIC,
    SEQUENCE_MODULUS,
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
from spbconform.model import DEVICE_MESSAGE_TYPES, NODE_MESSAGE_TYPES, RESERVED_IN_TOPIC

#: Epoch milliseconds the reference clock opens at, comfortably inside the range
#: a UTC reading falls in, so the two UTC assertions hold unless a fault says
#: otherwise.
EPOCH_BASE_MS = 1_760_000_000_000

_UNSET = object()


@dataclass(frozen=True, slots=True)
class Faults:
    """One documented break per field. Every default is the conformant value."""

    #: Address every topic under a namespace that is not Sparkplug B.
    namespace: str = NAMESPACE
    #: Append a level to every rendered topic.
    topic_suffix: bool = False
    #: Render every topic in upper case, mangling each identifier in it.
    shout_topics: bool = False
    #: Render every topic in lower case, folding two ids that differ by case.
    fold_topic_case: bool = False
    #: Address every device message to one device under a foreign group.
    collapse_device_topics: bool = False
    #: Let an identifier holding an MQTT wildcard or separator through.
    accept_bad_identifiers: bool = False
    #: Stamp every message with the same sequence number.
    constant_sequence: bool = False
    #: Send every message without a sequence number.
    absent_sequence: bool = False
    #: Let the sequence counter run past the byte it is given.
    sequence_never_wraps: bool = False
    #: Publish and declare every topic class under these flags.
    delivery_override: tuple[int, bool] | None = None
    #: Open the session without handing back a will to register.
    no_will: bool = False
    #: Register something other than an NDEATH as the will.
    will_is_birth: bool = False
    #: Register a will carrying a sequence number and a second metric.
    crowded_will: bool = False
    #: Birth every metric without an alias.
    unaliased_births: bool = False
    #: Give every metric on the edge node the same alias.
    shared_aliases: bool = False
    #: Birth the rebirth command metric inside the alias table.
    alias_rebirth_metric: bool = False
    #: Carry the metric name alongside the alias in a data message.
    named_data: bool = False
    #: Repeat the datatype in a data message the birth already declared.
    typed_data: bool = False
    #: Birth every metric with no name and no datatype.
    untyped_births: bool = False
    #: Send every metric without a timestamp.
    undated_metrics: bool = False
    #: Send every payload without its own timestamp.
    undated_payloads: bool = False
    #: Order the metrics of a payload backwards in time.
    backwards_metric_order: bool = False
    #: Publish a birth certificate that declares nothing.
    empty_births: bool = False
    #: Birth with a bdSeq the will never carried.
    wrong_bdseq: bool = False
    #: Reuse one bdSeq for every session.
    frozen_bdseq: bool = False
    #: Carry bdSeq as an unsigned metric rather than the signed one named.
    bdseq_uint64: bool = False
    #: Drop the rebirth command metric from the edge node.
    no_rebirth_metric: bool = False
    #: Birth the rebirth command metric as a string holding true.
    rebirth_metric_is_string: bool = False
    #: Ignore a rebirth request entirely.
    ignore_rebirth: bool = False
    #: Rebirth on any command at all, whatever its name or value.
    rebirth_on_any_command: bool = False
    #: Rebirth without republishing the device birth certificates.
    rebirth_only_nbirth: bool = False
    #: Treat a rebirth as a new session, moving bdSeq under the live will.
    rebirth_reconnects: bool = False
    #: Carry a data message inside the rebirth sequence.
    rebirth_publishes_data: bool = False
    #: Publish anything in any order, refusing nothing.
    refuse_nothing: bool = False
    #: Let a metric no birth certificate declared reach a data message.
    allow_undeclared: bool = False
    #: Republish the whole metric set on every data message.
    republish_everything: bool = False
    #: Report a lost device as a data message rather than a DDEATH.
    ddeath_is_data: bool = False
    #: Write and declare a quality code the specification does not define.
    bad_quality_codes: bool = False
    #: Offer no close, leaving an intentional shutdown to the broker's will.
    no_disconnect: bool = False
    #: Accept two metric names that differ only by letter case.
    accept_case_colliding_metrics: bool = False
    #: Read timestamps from a counter rather than from a UTC wall clock.
    simulation_clock: bool = False


class ReferenceSession:
    """One edge node session: birth certificates, aliases, sequence, and death."""

    def __init__(self, adapter: ReferenceAdapter, spec: NodeSpec) -> None:
        self._adapter = adapter
        self._faults = adapter.faults
        self._spec = spec
        self._connected = False
        self._node_born = False
        self._born: set[str] = set()
        self._seq = 0
        self._bdseq = 0
        self._connects = 0
        self._descending = EPOCH_BASE_MS
        self._aliases: dict[tuple[str | None, str], int] = {}
        self._assign_aliases()

    # ------------------------------------------------------------- the metrics

    def _control_metrics(self) -> tuple[MetricSpec, ...]:
        """The two metrics every edge node declares on its own behalf."""
        bdseq_type = DataType.UInt64 if self._faults.bdseq_uint64 else DataType.Int64
        bdseq = MetricSpec(name=BDSEQ_METRIC, datatype=bdseq_type, unit="1")
        if self._faults.no_rebirth_metric:
            return (bdseq,)
        rebirth_type = (
            DataType.String if self._faults.rebirth_metric_is_string else DataType.Boolean
        )
        return (bdseq, MetricSpec(name=REBIRTH_METRIC, datatype=rebirth_type, unit="1"))

    def _node_specs(self) -> tuple[MetricSpec, ...]:
        return (*self._control_metrics(), *self._spec.node_metrics)

    def _assign_aliases(self) -> None:
        """Number every metric of the edge node, the rebirth command aside.

        A command metric a Host Application writes by name has no alias to
        write it by, so it stays out of the table an aliased data message
        resolves against.
        """
        owned: list[tuple[str | None, str]] = [
            (None, spec.name)
            for spec in self._node_specs()
            if spec.name != REBIRTH_METRIC or self._faults.alias_rebirth_metric
        ]
        for device in sorted(self._spec.devices):
            owned.extend((device, spec.name) for spec in self._spec.devices[device])
        if not self._faults.accept_case_colliding_metrics:
            folded = [(owner, name.lower()) for owner, name in owned]
            if len(set(folded)) != len(folded):
                raise ValueError("two metric names of this edge node differ only by case")
        self._aliases = {key: number for number, key in enumerate(owned, start=1)}
        if self._faults.shared_aliases:
            self._aliases = dict.fromkeys(self._aliases, 1)

    # --------------------------------------------------------------- the clock

    def _payload_time(self) -> int | None:
        return None if self._faults.undated_payloads else self._adapter.now()

    def _metric_time(self) -> int | None:
        if self._faults.undated_metrics:
            return None
        if self._faults.backwards_metric_order:
            self._descending -= 1000
            return self._descending
        return self._adapter.now()

    # -------------------------------------------------------------- the topics

    def topic_for(self, message_type: MessageType, *, device_id: str | None = None) -> str:
        """Render one topic, or refuse a pairing the topic form has no room for."""
        permissive = self._faults.refuse_nothing
        if not permissive:
            if message_type is MessageType.STATE:
                raise Refused("STATE is a Host Application topic, not an edge node's")
            if message_type in DEVICE_MESSAGE_TYPES and device_id is None:
                raise Refused(f"{message_type} has a device id level and was given none")
            if message_type in NODE_MESSAGE_TYPES and device_id is not None:
                raise Refused(f"{message_type} has no device id level")
        parts = [
            self._faults.namespace,
            self._spec.group_id,
            str(message_type),
            self._spec.edge_node_id,
        ]
        if device_id is not None:
            parts.append(device_id)
        topic = "/".join(parts)
        if self._faults.topic_suffix:
            topic = f"{topic}/extra"
        if self._faults.shout_topics:
            topic = topic.upper()
        if self._faults.fold_topic_case:
            topic = topic.lower()
        if self._faults.collapse_device_topics and device_id is not None:
            levels = topic.split("/")
            levels[1] = "elsewhere-group"
            levels[-1] = "one-device"
            topic = "/".join(levels)
        return topic

    # ------------------------------------------------------------ the sequence

    def _next_seq(self) -> int | None:
        if self._faults.absent_sequence:
            return None
        if self._faults.constant_sequence:
            return 7
        value = self._seq
        if self._faults.sequence_never_wraps:
            self._seq += 1
        else:
            self._seq = (self._seq + 1) % SEQUENCE_MODULUS
        return value

    # ------------------------------------------------------------- the guards

    def _require_connected(self) -> None:
        if self._faults.refuse_nothing:
            return
        if not self._connected:
            raise Refused("the session is not open, so nothing may be published")

    def _require_ready(self, device_id: str | None) -> None:
        """Every precondition a data message has, in the order it acquires them."""
        if self._faults.refuse_nothing:
            return
        self._require_connected()
        if not self._node_born:
            raise Refused("no NBIRTH has gone out, so no data may follow it")
        if device_id is not None and device_id not in self._born:
            raise Refused(f"{device_id!r} has sent no DBIRTH")
        unborn = set(self._spec.devices) - self._born
        if unborn:
            raise Refused(f"data before the DBIRTH of {sorted(unborn)}")

    # ------------------------------------------------------------- the session

    def connect(self) -> Will | None:
        """Open the session and compose the will to register with CONNECT."""
        self._bdseq = 41 if self._faults.frozen_bdseq else self._connects % SEQUENCE_MODULUS
        self._connects += 1
        self._connected = True
        self._seq = 0
        self._node_born = False
        self._born = set()
        if self._faults.no_will:
            return None
        stamp = self._metric_time()
        bdseq_type = DataType.UInt64 if self._faults.bdseq_uint64 else DataType.Int64
        metrics = [
            Metric(value=self._bdseq, name=BDSEQ_METRIC, datatype=bdseq_type, timestamp=stamp)
        ]
        seq: int | None = None
        if self._faults.crowded_will:
            seq = 4
            metrics.append(Metric(value=1, name="extra", timestamp=stamp))
        kind = MessageType.NBIRTH if self._faults.will_is_birth else MessageType.NDEATH
        qos, retain = self._adapter.declared_delivery(MessageType.NDEATH)
        message = Message(
            topic=self.topic_for(MessageType.NDEATH),
            message_type=kind,
            payload=Payload(timestamp=self._payload_time(), metrics=tuple(metrics), seq=seq),
            qos=qos,
            retain=retain,
        )
        return Will(message=message, qos=qos, retain=retain)

    def disconnect(self) -> Message | None:
        """Publish the NDEATH a clean shutdown owes, since no will will be sent."""
        if self._faults.no_disconnect:
            return None
        self._require_connected()
        bdseq_type = DataType.UInt64 if self._faults.bdseq_uint64 else DataType.Int64
        metric = Metric(
            value=self._bdseq,
            name=BDSEQ_METRIC,
            datatype=bdseq_type,
            timestamp=self._metric_time(),
        )
        self._connected = False
        return self._message(MessageType.NDEATH, (metric,), device_id=None, seq=None)

    # -------------------------------------------------------------- the births

    def _birth_value(self, device_id: str | None, spec: MetricSpec) -> Any:
        if device_id is None and spec.name == BDSEQ_METRIC:
            return 200 if self._faults.wrong_bdseq else self._bdseq
        if device_id is None and spec.name == REBIRTH_METRIC:
            return True if self._faults.rebirth_metric_is_string else False
        return 0

    def _birth_metric(self, device_id: str | None, spec: MetricSpec) -> Metric:
        alias = None if self._faults.unaliased_births else self._aliases.get((device_id, spec.name))
        name: str | None = spec.name
        datatype: DataType | None = spec.datatype
        if self._faults.untyped_births:
            name, datatype = None, None
        quality = 1 if self._faults.bad_quality_codes else int(Quality.GOOD)
        properties: dict[str, Any] = {"engUnit": spec.unit, "Quality": quality}
        if spec.eng_low is not None:
            properties["engLow"] = spec.eng_low
        if spec.eng_high is not None:
            properties["engHigh"] = spec.eng_high
        return Metric(
            value=self._birth_value(device_id, spec),
            alias=alias,
            name=name,
            datatype=datatype,
            timestamp=self._metric_time(),
            properties=properties,
        )

    def _birth_metrics(
        self, device_id: str | None, specs: tuple[MetricSpec, ...]
    ) -> tuple[Metric, ...]:
        if self._faults.empty_births:
            return tuple(Metric(value=None) for _ in specs)
        return tuple(self._birth_metric(device_id, spec) for spec in specs)

    def node_birth(self) -> Message:
        """Publish the NBIRTH, opening the sequence and declaring every node metric."""
        self._require_connected()
        self._node_born = True
        return self._message(
            MessageType.NBIRTH, self._birth_metrics(None, self._node_specs()), device_id=None
        )

    def device_birth(self, device_id: str) -> Message:
        """Publish one device's DBIRTH, declaring the aliases its data will use."""
        self._require_connected()
        if not self._node_born and not self._faults.refuse_nothing:
            raise Refused("a DBIRTH cannot precede the NBIRTH of the node it hangs off")
        specs = self._spec.devices[device_id]
        self._born.add(device_id)
        return self._message(
            MessageType.DBIRTH, self._birth_metrics(device_id, specs), device_id=device_id
        )

    # ---------------------------------------------------------------- the data

    def _data_metrics(
        self, device_id: str | None, changed: Mapping[str, Any]
    ) -> tuple[Metric, ...]:
        if self._faults.republish_everything:
            return tuple(
                Metric(value=0, alias=alias, timestamp=self._metric_time())
                for (owner, _name), alias in sorted(self._aliases.items(), key=lambda kv: kv[1])
                if owner == device_id
            )
        permissive = self._faults.allow_undeclared or self._faults.refuse_nothing
        metrics = []
        for name in sorted(changed):
            key = (device_id, name)
            if key not in self._aliases and not permissive:
                raise Refused(f"{name!r} was never declared in a birth certificate")
            metric = Metric(
                value=changed[name],
                alias=self._aliases.get(key, 99),
                timestamp=self._metric_time(),
            )
            if self._faults.named_data:
                metric = replace(metric, name=name)
            if self._faults.typed_data:
                metric = replace(metric, datatype=DataType.Double)
            metrics.append(metric)
        return tuple(metrics)

    def node_data(self, changed: Mapping[str, Any]) -> Message:
        """Publish an NDATA carrying the node metrics the caller reported changed."""
        self._require_ready(None)
        return self._message(MessageType.NDATA, self._data_metrics(None, changed), device_id=None)

    def device_data(self, device_id: str, changed: Mapping[str, Any]) -> Message:
        """Publish a DDATA carrying the device metrics the caller reported changed."""
        self._require_ready(device_id)
        return self._message(
            MessageType.DDATA, self._data_metrics(device_id, changed), device_id=device_id
        )

    def device_death(self, device_id: str) -> Message:
        """Report a device lost below an edge node that is still connected."""
        self._require_connected()
        kind = MessageType.DDATA if self._faults.ddeath_is_data else MessageType.DDEATH
        return self._message(kind, (), device_id=device_id)

    # ------------------------------------------------------------- the rebirth

    def rebirth(self) -> tuple[Message, ...]:
        """Republish the whole birth set under the session's existing bdSeq."""
        if self._faults.rebirth_reconnects:
            self._bdseq = (self._bdseq + 1) % SEQUENCE_MODULUS
        self._seq = 0
        self._born = set()
        messages = [self.node_birth()]
        if not self._faults.rebirth_only_nbirth:
            messages.extend(self.device_birth(device) for device in sorted(self._spec.devices))
        if self._faults.rebirth_publishes_data and self._spec.node_metrics:
            messages.append(self.node_data({self._spec.node_metrics[0].name: 1}))
        return tuple(messages)

    def handle_node_command(self, command: Mapping[str, Any]) -> tuple[Message, ...]:
        """Act on an inbound NCMD, which for this edge node means the rebirth alone."""
        if self._faults.ignore_rebirth:
            return ()
        if self._faults.rebirth_on_any_command:
            return self.rebirth()
        if command.get(REBIRTH_METRIC) is True:
            return self.rebirth()
        return ()

    # ------------------------------------------------------------- the message

    def _message(
        self,
        message_type: MessageType,
        metrics: tuple[Metric, ...],
        *,
        device_id: str | None,
        seq: Any = _UNSET,
    ) -> Message:
        qos, retain = self._adapter.declared_delivery(message_type)
        number = self._next_seq() if seq is _UNSET else seq
        return Message(
            topic=self.topic_for(message_type, device_id=device_id),
            message_type=message_type,
            payload=Payload(timestamp=self._payload_time(), metrics=metrics, seq=number),
            qos=qos,
            retain=retain,
        )


class ReferenceAdapter:
    """The implementation under test: a session factory and two published tables."""

    def __init__(self, faults: Faults | None = None) -> None:
        self.faults = faults if faults is not None else Faults()
        self._tick = 0 if self.faults.simulation_clock else EPOCH_BASE_MS

    def now(self) -> int:
        """Epoch milliseconds, advancing by one on every reading.

        A monotonic counter rather than the wall clock, so two runs of the
        suite produce the same timestamps and a test can assert on them.
        """
        self._tick += 1
        return self._tick

    def new_session(self, spec: NodeSpec) -> ReferenceSession:
        """An unconnected session for the node described."""
        return ReferenceSession(self, spec)

    def validate_ids(self, *, group_id: str, edge_node_id: str, device_id: str = "") -> None:
        """Refuse an identifier that would change the topic it is joined into."""
        if self.faults.accept_bad_identifiers:
            return
        for field, value in (
            ("group id", group_id),
            ("edge node id", edge_node_id),
            ("device id", device_id),
        ):
            if value and any(char in value for char in RESERVED_IN_TOPIC):
                raise Refused(
                    f"{field} {value!r} carries one of {RESERVED_IN_TOPIC}, which MQTT reads "
                    "as a level separator or a wildcard"
                )

    def declared_delivery(self, message_type: MessageType) -> tuple[int, bool]:
        """The QoS and retain flag each topic class is published under."""
        if self.faults.delivery_override is not None:
            return self.faults.delivery_override
        if message_type is MessageType.NDEATH:
            return (1, False)
        if message_type is MessageType.STATE:
            return (1, True)
        return (0, False)

    def quality_codes(self) -> frozenset[int]:
        """The codes this edge node writes into a `Quality` property."""
        return frozenset({1, 2}) if self.faults.bad_quality_codes else QUALITY_CODES
