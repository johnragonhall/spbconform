"""The published Sparkplug B v3.0.0 assertion identifiers, and what each denotes.

The only conformance suite for Eclipse Sparkplug B is the Eclipse Technology
Compatibility Kit, a Java suite under EPL-2.0. This table is not derived from
it. Every identifier here is one the v3.0.0 specification anchors with a
`tck-testable` role, and every `statement` is written here from the technical
requirement rather than copied from the specification text. Identifiers and
technical requirements are facts; the specification's prose is expression, and
none of it is reproduced.

The table is the honest denominator. It carries all 299 anchored assertions of
v3.0.0, not only the ones this library can observe, and each row records three
independent facts: which conformance profile the assertion constrains, whether
this library carries a check for it, and, when it does not, the capability that
is missing. A high pass count over a table pruned to what already works would
say nothing, so the pruning is recorded rather than performed.

`profile` and `scope` are orthogonal. An assertion can constrain a Host
Application and still be in scope, because an edge node's own delivery table
declares flags for topic classes it never publishes on. The edge-node coverage
numbers `spbconform.runner` reports read `profile` alone.

The specification's own anchor and its displayed label disagree for four
assertions. The anchor is the identifier used here, because the anchor is what
a cross-reference resolves against.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

#: The specification edition every identifier here is read from.
SPEC_VERSION = "3.0.0"

#: Assertions the v3.0.0 specification anchors with a `tck-testable` role. The
#: table below carries exactly this many rows, which is what makes the coverage
#: denominator checkable rather than asserted.
SPEC_ASSERTION_COUNT = 299


class Profile(StrEnum):
    """The conformance profile an assertion constrains.

    v3.0.0 names four target applications and marks no assertion with the one
    it belongs to, so the profile here is read from the actor each assertion's
    sentence constrains: the client that publishes the message, or the server
    that stores it. The compatibility kit's own grouping is a Java artifact and
    is not consulted, so this column is a reading and is open to correction.
    """

    EDGE_NODE = "edge-node"
    HOST_APPLICATION = "host-application"
    MQTT_SERVER = "mqtt-server"


class Level(StrEnum):
    """The requirement level the assertion's sentence carries."""

    MUST = "MUST"
    SHOULD = "SHOULD"
    MAY = "MAY"


class Exclusion(StrEnum):
    """Why an assertion has no check in this library.

    Every value names a capability the harness lacks, rather than a judgement
    that the assertion does not matter. An excluded assertion is an unmeasured
    requirement, not a satisfied one.
    """

    ENCODING = "protobuf wire encoding, which this harness does not decode"
    TEMPLATES = (
        "Template, DataSet, and PropertySet wire structures, which this harness does not model"
    )
    TRANSPORT = "a live MQTT client and broker, which sits outside an in-process harness"
    DEPLOYMENT = "uniqueness across a whole infrastructure, which one session cannot observe"
    PRIMARY_HOST = (
        "Primary Host coordination and multi-server failover, which this harness does not drive"
    )
    OTHER_PROFILE = (
        "the behavior of a Host Application or an MQTT Server, which an edge node is not"
    )


@dataclass(frozen=True, slots=True)
class Assertion:
    """One published assertion identifier and this library's position on it."""

    assertion_id: str
    profile: Profile
    level: Level
    statement: str
    exclusion: Exclusion | None

    @property
    def in_scope(self) -> bool:
        """Whether this library carries a check for this assertion."""
        return self.exclusion is None


_EDGE = Profile.EDGE_NODE
_HOST = Profile.HOST_APPLICATION
_SERVER = Profile.MQTT_SERVER
_MUST = Level.MUST
_SHOULD = Level.SHOULD
_MAY = Level.MAY
_ENC = Exclusion.ENCODING
_TPL = Exclusion.TEMPLATES
_TRN = Exclusion.TRANSPORT
_DEP = Exclusion.DEPLOYMENT
_PHI = Exclusion.PRIMARY_HOST
_OTH = Exclusion.OTHER_PROFILE

#: `(identifier, profile, level, exclusion, statement)`, in specification order.
#: A `None` exclusion means this library carries an executable check for the
#: assertion, and `spbconform.checks` holds it.
_ROWS: tuple[tuple[str, Profile, Level, Exclusion | None, str], ...] = (
    # ---------------------------------------------------------- 1 Introduction
    (
        "tck-id-intro-sparkplug-host-state",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application announces its own online and offline status with STATE messages.",
    ),
    (
        "tck-id-intro-group-id-string",
        _EDGE,
        _MUST,
        None,
        "The Group ID is a UTF-8 string carried as a level of the Sparkplug topic.",
    ),
    (
        "tck-id-intro-group-id-chars",
        _EDGE,
        _MUST,
        None,
        "The Group ID holds only characters MQTT permits inside a topic string.",
    ),
    (
        "tck-id-intro-edge-node-id-string",
        _EDGE,
        _MUST,
        None,
        "The Edge Node ID is a UTF-8 string carried as a level of the Sparkplug topic.",
    ),
    (
        "tck-id-intro-edge-node-id-chars",
        _EDGE,
        _MUST,
        None,
        "The Edge Node ID holds only characters MQTT permits inside a topic string.",
    ),
    (
        "tck-id-intro-device-id-string",
        _EDGE,
        _MUST,
        None,
        "The Device ID is a UTF-8 string carried as a level of the Sparkplug topic.",
    ),
    (
        "tck-id-intro-device-id-chars",
        _EDGE,
        _MUST,
        None,
        "The Device ID holds only characters MQTT permits inside a topic string.",
    ),
    (
        "tck-id-intro-edge-node-id-uniqueness",
        _EDGE,
        _MUST,
        _DEP,
        "The Edge Node Descriptor is unique among every edge node of the infrastructure.",
    ),
    # ------------------------------------------------------------ 2 Principles
    (
        "tck-id-principles-rbe-recommended",
        _EDGE,
        _SHOULD,
        None,
        "An edge node reports by exception rather than on a timer.",
    ),
    (
        "tck-id-principles-birth-certificates-order",
        _EDGE,
        _MUST,
        None,
        "A birth certificate is the first message an edge node or a host publishes.",
    ),
    (
        "tck-id-principles-persistence-clean-session-311",
        _EDGE,
        _MUST,
        _TRN,
        "Over MQTT 3.1.1 the edge node's CONNECT sets the clean-session flag.",
    ),
    (
        "tck-id-principles-persistence-clean-session-50",
        _EDGE,
        _MUST,
        _TRN,
        "Over MQTT 5.0 the edge node's CONNECT sets clean start and a zero session expiry.",
    ),
    # ------------------------------------------------------------ 3 Components
    (
        "tck-id-components-ph-state",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application uses STATE to say whether it is online at any moment.",
    ),
    # ---------------------------------------------------------------- 4 Topics
    (
        "tck-id-topic-structure",
        _EDGE,
        _MUST,
        None,
        "Every Sparkplug client addresses messages with the fixed topic namespace structure.",
    ),
    (
        "tck-id-topic-structure-namespace-a",
        _EDGE,
        _MUST,
        None,
        "The namespace level of a Sparkplug B topic is the constant spBv1.0.",
    ),
    (
        "tck-id-topic-structure-namespace-valid-group-id",
        _EDGE,
        _MUST,
        None,
        "The Group ID is a UTF-8 string that excludes plus, forward slash, and hash.",
    ),
    (
        "tck-id-topic-structure-namespace-unique-edge-node-descriptor",
        _EDGE,
        _MUST,
        _DEP,
        "No two edge nodes in the infrastructure share a group and edge-node id pair.",
    ),
    (
        "tck-id-topic-structure-namespace-valid-edge-node-id",
        _EDGE,
        _MUST,
        None,
        "The Edge Node ID is a UTF-8 string that excludes plus, forward slash, and hash.",
    ),
    (
        "tck-id-topic-structure-namespace-valid-device-id",
        _EDGE,
        _MUST,
        None,
        "The Device ID is a UTF-8 string that excludes plus, forward slash, and hash.",
    ),
    (
        "tck-id-topic-structure-namespace-unique-device-id",
        _EDGE,
        _MUST,
        None,
        "No two devices reported by one edge node share a Device ID.",
    ),
    (
        "tck-id-topic-structure-namespace-duplicate-device-id-across-edge-node",
        _EDGE,
        _MAY,
        _DEP,
        "Two different edge nodes may report devices under the same Device ID.",
    ),
    (
        "tck-id-topic-structure-namespace-device-id-associated-message-types",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH, DDEATH, DDATA, or DCMD topic carries a device id level.",
    ),
    (
        "tck-id-topic-structure-namespace-device-id-non-associated-message-types",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH, NDEATH, NDATA, NCMD, or STATE topic carries no device id level.",
    ),
    (
        "tck-id-topics-nbirth-topic",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH is addressed as namespace, group id, NBIRTH, edge node id.",
    ),
    (
        "tck-id-topics-nbirth-mqtt",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH goes out at QoS 0 with the retain flag clear.",
    ),
    (
        "tck-id-topics-nbirth-seq-num",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH payload carries a sequence number whose value is zero.",
    ),
    (
        "tck-id-topics-nbirth-timestamp",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH carries the instant the edge node sent it.",
    ),
    (
        "tck-id-topics-nbirth-metric-reqs",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH declares every metric the edge node will ever report.",
    ),
    (
        "tck-id-topics-nbirth-metrics",
        _EDGE,
        _MUST,
        None,
        "Each NBIRTH metric carries at least a name, a datatype, and a value.",
    ),
    (
        "tck-id-topics-nbirth-templates",
        _EDGE,
        _MUST,
        _TPL,
        "Template definitions used anywhere below this edge node appear in its NBIRTH.",
    ),
    (
        "tck-id-topics-nbirth-bdseq-included",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH payload carries a bdSeq metric.",
    ),
    (
        "tck-id-topics-nbirth-bdseq-matching",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH bdSeq equals the bdSeq in the will registered at the same CONNECT.",
    ),
    (
        "tck-id-topics-nbirth-bdseq-increment",
        _EDGE,
        _MUST,
        None,
        "bdSeq opens at zero and advances by one for each new CONNECT.",
    ),
    (
        "tck-id-topics-nbirth-rebirth-metric",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH carries a boolean Node Control/Rebirth metric whose value is false.",
    ),
    (
        "tck-id-topics-ndata-topic",
        _EDGE,
        _MUST,
        None,
        "An NDATA is addressed as namespace, group id, NDATA, edge node id.",
    ),
    (
        "tck-id-topics-ndata-mqtt",
        _EDGE,
        _MUST,
        None,
        "An NDATA goes out at QoS 0 with the retain flag clear.",
    ),
    (
        "tck-id-topics-ndata-seq-num",
        _EDGE,
        _MUST,
        None,
        "An NDATA sequence number is one above the edge node's previous message.",
    ),
    (
        "tck-id-topics-ndata-timestamp",
        _EDGE,
        _MUST,
        None,
        "An NDATA carries the instant the edge node sent it.",
    ),
    (
        "tck-id-topics-ndata-payload",
        _EDGE,
        _MUST,
        None,
        "An NDATA carries the node metrics that changed since the last NBIRTH or NDATA.",
    ),
    (
        "tck-id-topics-ndeath-topic",
        _EDGE,
        _MUST,
        None,
        "An NDEATH is addressed as namespace, group id, NDEATH, edge node id.",
    ),
    (
        "tck-id-topics-ndeath-payload",
        _EDGE,
        _MUST,
        None,
        "An NDEATH payload carries the bdSeq metric and nothing else.",
    ),
    (
        "tck-id-topics-ndeath-seq",
        _EDGE,
        _MUST,
        None,
        "An NDEATH payload carries no sequence number.",
    ),
    (
        "tck-id-topics-ncmd-topic",
        _EDGE,
        _MUST,
        None,
        "An NCMD is addressed as namespace, group id, NCMD, edge node id.",
    ),
    (
        "tck-id-topics-ncmd-mqtt",
        _HOST,
        _MUST,
        None,
        "An NCMD goes out at QoS 0 with the retain flag clear.",
    ),
    (
        "tck-id-topics-ncmd-timestamp",
        _HOST,
        _MUST,
        _OTH,
        "An NCMD carries the instant the host's client sent it.",
    ),
    (
        "tck-id-topics-ncmd-payload",
        _HOST,
        _MUST,
        _OTH,
        "An NCMD carries the metrics to be written on the edge node.",
    ),
    (
        "tck-id-topics-dbirth-topic",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH is addressed as namespace, group id, DBIRTH, edge node id, device id.",
    ),
    (
        "tck-id-topics-dbirth-mqtt",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH goes out at QoS 0 with the retain flag clear.",
    ),
    (
        "tck-id-topics-dbirth-seq",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH sequence number is one above the edge node's previous message.",
    ),
    (
        "tck-id-topics-dbirth-timestamp",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH carries the instant the edge node sent it.",
    ),
    (
        "tck-id-topics-dbirth-metric-reqs",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH declares every metric this device will ever report.",
    ),
    (
        "tck-id-topics-dbirth-metrics",
        _EDGE,
        _MUST,
        None,
        "Each DBIRTH metric carries at least a name, a datatype, and a value.",
    ),
    (
        "tck-id-topics-ddata-topic",
        _EDGE,
        _MUST,
        None,
        "A DDATA is addressed as namespace, group id, DDATA, edge node id, device id.",
    ),
    (
        "tck-id-topics-ddata-mqtt",
        _EDGE,
        _MUST,
        None,
        "A DDATA goes out at QoS 0 with the retain flag clear.",
    ),
    (
        "tck-id-topics-ddata-seq-num",
        _EDGE,
        _MUST,
        None,
        "A DDATA sequence number is one above the edge node's previous message.",
    ),
    (
        "tck-id-topics-ddata-timestamp",
        _EDGE,
        _MUST,
        None,
        "A DDATA carries the instant the edge node sent it.",
    ),
    (
        "tck-id-topics-ddata-payload",
        _EDGE,
        _MUST,
        None,
        "A DDATA carries the device metrics that changed since the last DBIRTH or DDATA.",
    ),
    (
        "tck-id-topics-ddeath-topic",
        _EDGE,
        _MUST,
        None,
        "A DDEATH is addressed as namespace, group id, DDEATH, edge node id, device id.",
    ),
    (
        "tck-id-topics-ddeath-mqtt",
        _EDGE,
        _MUST,
        None,
        "A DDEATH goes out at QoS 0 with the retain flag clear.",
    ),
    (
        "tck-id-topics-ddeath-seq-num",
        _EDGE,
        _MUST,
        None,
        "A DDEATH sequence number is one above the edge node's previous message.",
    ),
    (
        "tck-id-topics-dcmd-topic",
        _EDGE,
        _MUST,
        None,
        "A DCMD is addressed as namespace, group id, DCMD, edge node id, device id.",
    ),
    (
        "tck-id-topics-dcmd-mqtt",
        _HOST,
        _MUST,
        None,
        "A DCMD goes out at QoS 0 with the retain flag clear.",
    ),
    (
        "tck-id-topics-dcmd-timestamp",
        _HOST,
        _MUST,
        _OTH,
        "A DCMD carries the instant the host's client sent it.",
    ),
    (
        "tck-id-topics-dcmd-payload",
        _HOST,
        _MUST,
        _OTH,
        "A DCMD carries the metrics to be written on the device.",
    ),
    (
        "tck-id-host-topic-phid-birth-message",
        _HOST,
        _MUST,
        _OTH,
        "The first message a Host Application publishes is its birth certificate.",
    ),
    (
        "tck-id-host-topic-phid-birth-qos",
        _HOST,
        _MUST,
        None,
        "The Host Application birth certificate goes out at QoS 1.",
    ),
    (
        "tck-id-host-topic-phid-birth-retain",
        _HOST,
        _MUST,
        None,
        "The Host Application birth certificate goes out with the retain flag set.",
    ),
    (
        "tck-id-host-topic-phid-birth-topic",
        _HOST,
        _MUST,
        _OTH,
        "The Host Application birth is addressed as spBv1.0, STATE, host id.",
    ),
    (
        "tck-id-host-topic-phid-birth-sub-required",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application subscribes to its own STATE topic and the namespace on connect.",
    ),
    (
        "tck-id-host-topic-phid-birth-required",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application publishes its birth once those subscriptions are in place.",
    ),
    (
        "tck-id-host-topic-phid-birth-payload",
        _HOST,
        _MUST,
        _OTH,
        "The Host Application birth payload is JSON carrying an online flag and a timestamp.",
    ),
    (
        "tck-id-host-topic-phid-birth-payload-timestamp",
        _HOST,
        _MUST,
        _OTH,
        "The birth timestamp repeats the one in the will of the preceding CONNECT.",
    ),
    (
        "tck-id-host-topic-phid-death-qos",
        _HOST,
        _MUST,
        _OTH,
        "The Host Application death certificate goes out at QoS 1.",
    ),
    (
        "tck-id-host-topic-phid-death-retain",
        _HOST,
        _MUST,
        _OTH,
        "The Host Application death certificate goes out with the retain flag set.",
    ),
    (
        "tck-id-host-topic-phid-death-topic",
        _HOST,
        _MUST,
        _OTH,
        "The Host Application death is addressed as spBv1.0, STATE, host id.",
    ),
    (
        "tck-id-host-topic-phid-death-required",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application registers a will in its CONNECT.",
    ),
    (
        "tck-id-host-topic-phid-death-payload",
        _HOST,
        _MUST,
        _OTH,
        "The STATE death payload is JSON carrying a false online flag and a timestamp.",
    ),
    (
        "tck-id-host-topic-phid-death-payload-timestamp-connect",
        _HOST,
        _MUST,
        _OTH,
        "The will's death timestamp is the UTC instant of the CONNECT that registered it.",
    ),
    (
        "tck-id-host-topic-phid-death-payload-timestamp-disconnect-clean",
        _HOST,
        _MUST,
        _OTH,
        "A host disconnecting with a DISCONNECT packet publishes its death first.",
    ),
    (
        "tck-id-host-topic-phid-death-payload-timestamp-disconnect-with-no-disconnect-packet",
        _HOST,
        _MUST,
        _OTH,
        "A host dropping the connection without a DISCONNECT publishes its death first.",
    ),
    # -------------------------------------------------- 5 Operational Behavior
    (
        "tck-id-case-sensitivity-sparkplug-ids",
        _EDGE,
        _SHOULD,
        None,
        "Two Sparkplug ids on one edge node do not differ only by letter case.",
    ),
    (
        "tck-id-case-sensitivity-metric-names",
        _EDGE,
        _SHOULD,
        None,
        "Two metric names published by one edge node do not differ only by letter case.",
    ),
    (
        "tck-id-message-flow-phid-sparkplug-clean-session-311",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application on MQTT 3.1.1 sets the clean-session flag in its CONNECT.",
    ),
    (
        "tck-id-message-flow-phid-sparkplug-clean-session-50",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application on MQTT 5.0 sets clean start and a zero session expiry.",
    ),
    (
        "tck-id-message-flow-phid-sparkplug-subscription",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application subscribes before publishing its own STATE message.",
    ),
    (
        "tck-id-message-flow-phid-sparkplug-state-publish",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application publishes STATE once its session and subscriptions are up.",
    ),
    (
        "tck-id-message-flow-phid-sparkplug-state-publish-payload",
        _HOST,
        _MUST,
        _OTH,
        "The Host Application STATE birth payload is JSON with an online flag and a timestamp.",
    ),
    (
        "tck-id-message-flow-phid-sparkplug-state-publish-payload-timestamp",
        _HOST,
        _MUST,
        _OTH,
        "That STATE birth timestamp repeats the one from the preceding CONNECT will.",
    ),
    (
        "tck-id-message-flow-hid-sparkplug-state-message-delivered",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application seeing a false online flag on its own id republishes its birth.",
    ),
    (
        "tck-id-message-flow-edge-node-ncmd-subscribe",
        _EDGE,
        _MUST,
        _TRN,
        "An edge node subscribes to its own NCMD topic.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-connect",
        _EDGE,
        _MUST,
        None,
        "An edge node establishes its MQTT session before publishing any birth.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-will-message",
        _EDGE,
        _MUST,
        None,
        "An edge node's CONNECT carries a will message.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-will-message-topic",
        _EDGE,
        _MUST,
        None,
        "The will is addressed as spBv1.0, group id, NDEATH, edge node id.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-will-message-payload",
        _EDGE,
        _MUST,
        _ENC,
        "The will payload is a Sparkplug protobuf-encoded payload.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-will-message-payload-bdSeq",
        _EDGE,
        _MUST,
        None,
        "The will carries a bdSeq metric of datatype Int64, one above the previous CONNECT and "
        "returning to zero after 255.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-will-message-qos",
        _EDGE,
        _MUST,
        None,
        "The will is registered at QoS 1.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-will-message-will-retained",
        _EDGE,
        _MUST,
        None,
        "The will is registered with the retain flag clear.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-phid-wait",
        _EDGE,
        _MUST,
        _PHI,
        "An edge node configured for a Primary Host waits for it to be online before birthing.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-phid-wait-id",
        _EDGE,
        _MUST,
        _PHI,
        "Such an edge node matches the host id in the STATE topic against its configured one.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-phid-wait-online",
        _EDGE,
        _MUST,
        _PHI,
        "Such an edge node requires a true online flag in the STATE payload.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-phid-wait-timestamp",
        _EDGE,
        _MUST,
        _PHI,
        "Such an edge node requires the STATE timestamp not to move backwards.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-nbirth-topic",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH is addressed as spBv1.0, group id, NBIRTH, edge node id.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-nbirth-payload",
        _EDGE,
        _MUST,
        _ENC,
        "The NBIRTH payload is a Sparkplug protobuf-encoded payload.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-nbirth-payload-bdSeq",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH carries a bdSeq metric of datatype Int64 holding the CONNECT's value.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-nbirth-qos",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH is published at QoS 0.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-nbirth-retained",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH is published with the retain flag clear.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-nbirth-payload-seq",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH payload carries a sequence number inside the byte range zero to 255.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-phid-offline",
        _EDGE,
        _MUST,
        _PHI,
        "An edge node watching a Primary Host reacts to a STATE message by its timestamp.",
    ),
    (
        "tck-id-operational-behavior-edge-node-intentional-disconnect-ndeath",
        _EDGE,
        _MUST,
        None,
        "An edge node closing its own connection publishes an NDEATH before it goes.",
    ),
    (
        "tck-id-operational-behavior-edge-node-intentional-disconnect-packet",
        _EDGE,
        _MAY,
        _TRN,
        "A DISCONNECT packet may follow that NDEATH.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-action-ndeath-node-offline",
        _HOST,
        _MUST,
        _OTH,
        "A host receiving an NDEATH marks that edge node offline at its own UTC time.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-action-ndeath-node-tags-stale",
        _HOST,
        _MUST,
        _OTH,
        "A host receiving an NDEATH marks that node's birthed metrics stale.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-action-ndeath-devices-offline",
        _HOST,
        _MUST,
        _OTH,
        "A host receiving an NDEATH marks that node's devices offline.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-action-ndeath-devices-tags-stale",
        _HOST,
        _MUST,
        _OTH,
        "A host receiving an NDEATH marks those devices' birthed metrics stale.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-offline",
        _EDGE,
        _MUST,
        _PHI,
        "An edge node leaves the server when its Primary Host reports itself offline.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-offline-reconnect",
        _EDGE,
        _MUST,
        _PHI,
        "Having left for that reason, the edge node tries the next server in its list.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-offline-timestamp",
        _EDGE,
        _MUST,
        _PHI,
        "An edge node ignores an offline STATE message whose timestamp is stale.",
    ),
    (
        "tck-id-message-flow-device-dcmd-subscribe",
        _EDGE,
        _MUST,
        _TRN,
        "A device that accepts writes has its edge node subscribe to the device's DCMD topic.",
    ),
    (
        "tck-id-message-flow-device-birth-publish-nbirth-wait",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH follows an NBIRTH sent in the same session.",
    ),
    (
        "tck-id-message-flow-device-birth-publish-dbirth-topic",
        _EDGE,
        _MUST,
        None,
        "The DBIRTH is addressed as spBv1.0, group id, DBIRTH, edge node id, device id.",
    ),
    (
        "tck-id-message-flow-device-birth-publish-dbirth-match-edge-node-topic",
        _EDGE,
        _MUST,
        None,
        "The DBIRTH topic repeats the group id and edge node id of the preceding NBIRTH.",
    ),
    (
        "tck-id-message-flow-device-birth-publish-dbirth-payload",
        _EDGE,
        _MUST,
        _ENC,
        "The DBIRTH payload is a Sparkplug protobuf-encoded payload.",
    ),
    (
        "tck-id-message-flow-device-birth-publish-dbirth-qos",
        _EDGE,
        _MUST,
        None,
        "The DBIRTH is published at QoS 0.",
    ),
    (
        "tck-id-message-flow-device-birth-publish-dbirth-retained",
        _EDGE,
        _MUST,
        None,
        "The DBIRTH is published with the retain flag clear.",
    ),
    (
        "tck-id-message-flow-device-birth-publish-dbirth-payload-seq",
        _EDGE,
        _MUST,
        None,
        "The DBIRTH sequence number is inside the byte range and one above the previous message.",
    ),
    (
        "tck-id-operational-behavior-device-ddeath",
        _EDGE,
        _MUST,
        None,
        "An edge node that loses a device publishes a DDEATH on the device's behalf.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-action-ddeath-devices-offline",
        _HOST,
        _MUST,
        _OTH,
        "A host receiving a DDEATH marks that device offline at the payload timestamp.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-action-ddeath-devices-tags-stale",
        _HOST,
        _MUST,
        _OTH,
        "A host receiving a DDEATH marks that device's birthed metrics stale.",
    ),
    (
        "tck-id-operational-behavior-host-reordering-param",
        _HOST,
        _SHOULD,
        _OTH,
        "A Host Application offers a configurable reorder timeout.",
    ),
    (
        "tck-id-operational-behavior-host-reordering-start",
        _HOST,
        _MUST,
        _OTH,
        "A host with that timeout starts a timer on an out-of-order sequence number.",
    ),
    (
        "tck-id-operational-behavior-host-reordering-rebirth",
        _HOST,
        _MUST,
        _OTH,
        "A host whose reorder timer expires requests a rebirth.",
    ),
    (
        "tck-id-operational-behavior-host-reordering-success",
        _HOST,
        _MUST,
        _OTH,
        "A host that receives the missing messages in time cancels the timer.",
    ),
    (
        "tck-id-operational-behavior-primary-application-state-with-multiple-servers-state-subs",
        _HOST,
        _MUST,
        _OTH,
        "A Primary Host across several servers publishes its STATE birth on each of them.",
    ),
    (
        "tck-id-operational-behavior-primary-application-state-with-multiple-servers-state",
        _HOST,
        _MUST,
        _OTH,
        "A Primary Host republishes its STATE birth on every new session with a server.",
    ),
    (
        "tck-id-operational-behavior-primary-application-state-with-multiple-servers-single-server",
        _EDGE,
        _MUST,
        _PHI,
        "An edge node holds a connection to at most one server at a time.",
    ),
    (
        "tck-id-operational-behavior-primary-application-state-with-multiple-servers-walk",
        _EDGE,
        _MUST,
        _PHI,
        "An edge node whose Primary Host goes offline moves to the next available server.",
    ),
    (
        "tck-id-operational-behavior-edge-node-birth-sequence-wait",
        _EDGE,
        _MUST,
        _PHI,
        "An edge node holds its birth sequence until it sees an online STATE message.",
    ),
    (
        "tck-id-operational-behavior-host-application-host-id",
        _HOST,
        _MUST,
        _OTH,
        "The Sparkplug host id is unique across the infrastructure.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-will",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application's CONNECT carries a will message.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-will-topic",
        _HOST,
        _MUST,
        _OTH,
        "That will is addressed as spBv1.0, STATE, host id.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-will-payload",
        _HOST,
        _MUST,
        _OTH,
        "That will payload is JSON with a false online flag and a timestamp.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-will-qos",
        _HOST,
        _MUST,
        _OTH,
        "That will is registered at QoS 1.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-will-retained",
        _HOST,
        _MUST,
        _OTH,
        "That will is registered with the retain flag set.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-birth",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application publishes its birth immediately after connecting.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-birth-topic",
        _HOST,
        _MUST,
        _OTH,
        "That birth is addressed as spBv1.0, STATE, host id.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-birth-payload",
        _HOST,
        _MUST,
        _OTH,
        "That birth payload is JSON with a true online flag and a timestamp.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-birth-qos",
        _HOST,
        _MUST,
        _OTH,
        "That birth is published at QoS 1.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-birth-retained",
        _HOST,
        _MUST,
        _OTH,
        "That birth is published with the retain flag set.",
    ),
    (
        "tck-id-operational-behavior-host-application-multi-server-timestamp",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application tracks a STATE timestamp per server.",
    ),
    (
        "tck-id-operational-behavior-host-application-termination",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application closing its own connection publishes a death message.",
    ),
    (
        "tck-id-operational-behavior-host-application-death-topic",
        _HOST,
        _MUST,
        _OTH,
        "That death is addressed as spBv1.0, STATE, host id.",
    ),
    (
        "tck-id-operational-behavior-host-application-death-payload",
        _HOST,
        _MUST,
        _OTH,
        "That death payload is JSON with a false online flag and a timestamp.",
    ),
    (
        "tck-id-operational-behavior-host-application-death-qos",
        _HOST,
        _MUST,
        _OTH,
        "That death is published at QoS 1.",
    ),
    (
        "tck-id-operational-behavior-host-application-death-retained",
        _HOST,
        _MUST,
        _OTH,
        "That death is published with the retain flag set.",
    ),
    (
        "tck-id-operational-behavior-host-application-disconnect-intentional",
        _HOST,
        _MAY,
        _OTH,
        "A DISCONNECT packet may follow that death message.",
    ),
    (
        "tck-id-operational-behavior-data-publish-nbirth",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH declares every node metric the session will ever publish.",
    ),
    (
        "tck-id-operational-behavior-data-publish-nbirth-values",
        _EDGE,
        _MUST,
        _ENC,
        "An NBIRTH metric holds its current value, or is flagged null with no value present.",
    ),
    (
        "tck-id-operational-behavior-data-publish-nbirth-change",
        _EDGE,
        _SHOULD,
        None,
        "An NDATA goes out only when a node metric changes.",
    ),
    (
        "tck-id-operational-behavior-data-publish-nbirth-order",
        _EDGE,
        _MUST,
        None,
        "Non-historical metric values in an NBIRTH or NDATA appear in chronological order.",
    ),
    (
        "tck-id-operational-behavior-data-publish-dbirth",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH declares every metric that device will ever publish in the session.",
    ),
    (
        "tck-id-operational-behavior-data-publish-dbirth-values",
        _EDGE,
        _MUST,
        _ENC,
        "A DBIRTH metric holds its current value, or is flagged null with no value present.",
    ),
    (
        "tck-id-operational-behavior-data-publish-dbirth-change",
        _EDGE,
        _SHOULD,
        None,
        "A DDATA goes out only when a device metric changes.",
    ),
    (
        "tck-id-operational-behavior-data-publish-dbirth-order",
        _EDGE,
        _MUST,
        None,
        "Non-historical metric values in a DBIRTH or DDATA appear in chronological order.",
    ),
    (
        "tck-id-operational-behavior-data-commands-rebirth-name",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH carries a metric named Node Control/Rebirth.",
    ),
    (
        "tck-id-operational-behavior-data-commands-rebirth-name-aliases",
        _EDGE,
        _MUST,
        None,
        "An edge node using aliases gives the Node Control/Rebirth metric no alias in its NBIRTH.",
    ),
    (
        "tck-id-operational-behavior-data-commands-rebirth-datatype",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH's Node Control/Rebirth metric has the Boolean datatype.",
    ),
    (
        "tck-id-operational-behavior-data-commands-rebirth-value",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH's Node Control/Rebirth metric holds the value false.",
    ),
    (
        "tck-id-operational-behavior-data-commands-ncmd-rebirth-verb",
        _HOST,
        _MUST,
        _OTH,
        "A rebirth request travels as an NCMD.",
    ),
    (
        "tck-id-operational-behavior-data-commands-ncmd-rebirth-name",
        _HOST,
        _MUST,
        None,
        "A rebirth request names the metric Node Control/Rebirth.",
    ),
    (
        "tck-id-operational-behavior-data-commands-ncmd-rebirth-value",
        _HOST,
        _MUST,
        None,
        "A rebirth request carries the value true.",
    ),
    (
        "tck-id-operational-behavior-data-commands-rebirth-action-1",
        _EDGE,
        _MUST,
        None,
        "An edge node given a rebirth request stops sending data messages at once.",
    ),
    (
        "tck-id-operational-behavior-data-commands-rebirth-action-2",
        _EDGE,
        _MUST,
        None,
        "It then sends a complete birth sequence: the NBIRTH and every DBIRTH.",
    ),
    (
        "tck-id-operational-behavior-data-commands-rebirth-action-3",
        _EDGE,
        _MUST,
        None,
        "That NBIRTH repeats the bdSeq value from the will of the current CONNECT.",
    ),
    (
        "tck-id-operational-behavior-data-commands-ncmd-verb",
        _HOST,
        _MUST,
        _OTH,
        "A node-level command travels as an NCMD.",
    ),
    (
        "tck-id-operational-behavior-data-commands-ncmd-metric-name",
        _HOST,
        _SHOULD,
        _OTH,
        "An NCMD names a metric the node's NBIRTH declared.",
    ),
    (
        "tck-id-operational-behavior-data-commands-ncmd-metric-value",
        _HOST,
        _MUST,
        _OTH,
        "An NCMD carries a value compatible with the metric it writes.",
    ),
    (
        "tck-id-operational-behavior-data-commands-dcmd-verb",
        _HOST,
        _MUST,
        _OTH,
        "A device-level command travels as a DCMD.",
    ),
    (
        "tck-id-operational-behavior-data-commands-dcmd-metric-name",
        _HOST,
        _SHOULD,
        _OTH,
        "A DCMD names a metric the device's DBIRTH declared.",
    ),
    (
        "tck-id-operational-behavior-data-commands-dcmd-metric-value",
        _HOST,
        _MUST,
        _OTH,
        "A DCMD carries a value compatible with the metric it writes.",
    ),
    # -------------------------------------------------------------- 6 Payloads
    (
        "tck-id-payloads-timestamp-in-UTC",
        _EDGE,
        _MUST,
        None,
        "The payload timestamp is a UTC reading.",
    ),
    (
        "tck-id-payloads-sequence-num-always-included",
        _EDGE,
        _MUST,
        None,
        "Every message from an edge node except an NDEATH carries a sequence number.",
    ),
    (
        "tck-id-payloads-sequence-num-req-nbirth",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH sequence number lies inside the byte range zero to 255.",
    ),
    (
        "tck-id-payloads-sequence-num-incrementing",
        _EDGE,
        _MUST,
        None,
        "Sequence numbers after an NBIRTH rise by one and return to zero after 255.",
    ),
    (
        "tck-id-payloads-name-requirement",
        _EDGE,
        _MUST,
        None,
        "A metric carries its name unless the edge node is using aliases.",
    ),
    (
        "tck-id-payloads-alias-uniqueness",
        _EDGE,
        _MUST,
        None,
        "An alias given at birth is unique across the edge node's whole metric set.",
    ),
    (
        "tck-id-payloads-alias-birth-requirement",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH or DBIRTH metric carries both its name and its alias.",
    ),
    (
        "tck-id-payloads-alias-data-cmd-requirement",
        _EDGE,
        _MUST,
        None,
        "An NDATA, DDATA, NCMD, or DCMD metric carries only the alias, with the name left out.",
    ),
    (
        "tck-id-payloads-name-birth-data-requirement",
        _EDGE,
        _MUST,
        None,
        "Every metric in an NBIRTH, DBIRTH, NDATA, or DDATA carries a timestamp.",
    ),
    (
        "tck-id-payloads-name-cmd-requirement",
        _HOST,
        _MAY,
        _OTH,
        "A metric in an NCMD or DCMD may carry a timestamp.",
    ),
    (
        "tck-id-payloads-metric-timestamp-in-UTC",
        _EDGE,
        _MUST,
        None,
        "The metric timestamp is a UTC reading.",
    ),
    (
        "tck-id-payloads-metric-datatype-value-type",
        _EDGE,
        _MUST,
        _ENC,
        "The datatype field is encoded as an unsigned 32-bit integer.",
    ),
    (
        "tck-id-payloads-metric-datatype-value",
        _EDGE,
        _MUST,
        None,
        "The datatype is one of the values the payload definition enumerates.",
    ),
    (
        "tck-id-payloads-metric-datatype-req",
        _EDGE,
        _MUST,
        None,
        "Each metric in an NBIRTH or DBIRTH carries its datatype.",
    ),
    (
        "tck-id-payloads-metric-datatype-not-req",
        _EDGE,
        _SHOULD,
        None,
        "A metric in an NDATA, NCMD, DDATA, or DCMD leaves the datatype out.",
    ),
    (
        "tck-id-payloads-propertyset-keys-array-size",
        _EDGE,
        _MUST,
        _ENC,
        "A PropertySet holds as many keys as it holds values.",
    ),
    (
        "tck-id-payloads-propertyset-values-array-size",
        _EDGE,
        _MUST,
        _ENC,
        "A PropertySet holds as many values as it holds keys.",
    ),
    (
        "tck-id-payloads-metric-propertyvalue-type-type",
        _EDGE,
        _MUST,
        _ENC,
        "A property value's type field is encoded as an unsigned 32-bit integer.",
    ),
    (
        "tck-id-payloads-metric-propertyvalue-type-value",
        _EDGE,
        _MUST,
        _ENC,
        "A property value's type is one of the enumerated datatypes.",
    ),
    (
        "tck-id-payloads-metric-propertyvalue-type-req",
        _EDGE,
        _MUST,
        _ENC,
        "A property value definition in an NBIRTH or DBIRTH carries its type.",
    ),
    (
        "tck-id-payloads-propertyset-quality-value-type",
        _EDGE,
        _MUST,
        _ENC,
        "The Quality property's type field is the signed 32-bit integer code.",
    ),
    (
        "tck-id-payloads-propertyset-quality-value-value",
        _EDGE,
        _MUST,
        None,
        "The Quality property holds one of the codes 0, 192, or 500.",
    ),
    (
        "tck-id-payloads-dataset-column-size",
        _EDGE,
        _MUST,
        _TPL,
        "A DataSet's column count is an unsigned 64-bit integer.",
    ),
    (
        "tck-id-payloads-dataset-column-num-headers",
        _EDGE,
        _MUST,
        _TPL,
        "A DataSet holds as many column headers as it holds types.",
    ),
    (
        "tck-id-payloads-dataset-types-def",
        _EDGE,
        _MUST,
        _TPL,
        "A DataSet's types are unsigned 32-bit integers naming the column datatypes.",
    ),
    (
        "tck-id-payloads-dataset-types-num",
        _EDGE,
        _MUST,
        _TPL,
        "A DataSet holds as many types as it holds columns.",
    ),
    (
        "tck-id-payloads-dataset-types-type",
        _EDGE,
        _MUST,
        _TPL,
        "Each DataSet type entry is an unsigned 32-bit integer.",
    ),
    (
        "tck-id-payloads-dataset-types-value",
        _EDGE,
        _MUST,
        _TPL,
        "Each DataSet type entry is one of the enumerated datatypes.",
    ),
    (
        "tck-id-payloads-dataset-parameter-type-req",
        _EDGE,
        _MUST,
        _TPL,
        "Every DataSet carries its types array.",
    ),
    (
        "tck-id-payloads-template-dataset-value",
        _EDGE,
        _MUST,
        _TPL,
        "A template DataSet value uses one of the permitted protobuf scalar types.",
    ),
    (
        "tck-id-payloads-template-definition-nbirth-only",
        _EDGE,
        _MUST,
        _TPL,
        "Template definitions appear only in NBIRTH messages.",
    ),
    (
        "tck-id-payloads-template-definition-is-definition",
        _EDGE,
        _MUST,
        _TPL,
        "A template definition sets its is-definition flag true.",
    ),
    (
        "tck-id-payloads-template-definition-ref",
        _EDGE,
        _MUST,
        _TPL,
        "A template definition leaves the template reference field out.",
    ),
    (
        "tck-id-payloads-template-definition-members",
        _EDGE,
        _MUST,
        _TPL,
        "A template definition lists every member its instances will ever carry.",
    ),
    (
        "tck-id-payloads-template-definition-nbirth",
        _EDGE,
        _MUST,
        _TPL,
        "Every template instance published has its definition in the NBIRTH.",
    ),
    (
        "tck-id-payloads-template-definition-parameters",
        _EDGE,
        _MUST,
        _TPL,
        "A template definition lists every parameter its instances will carry.",
    ),
    (
        "tck-id-payloads-template-definition-parameters-default",
        _EDGE,
        _MAY,
        _TPL,
        "A template definition may give default values for its parameters.",
    ),
    (
        "tck-id-payloads-template-instance-is-definition",
        _EDGE,
        _MUST,
        _TPL,
        "A template instance sets its is-definition flag false.",
    ),
    (
        "tck-id-payloads-template-instance-ref",
        _EDGE,
        _MUST,
        _TPL,
        "A template instance names the definition it refers to.",
    ),
    (
        "tck-id-payloads-template-instance-members",
        _EDGE,
        _MUST,
        _TPL,
        "A template instance carries only members its definition declared.",
    ),
    (
        "tck-id-payloads-template-instance-members-birth",
        _EDGE,
        _MUST,
        _TPL,
        "A template instance in a birth carries every member of its definition.",
    ),
    (
        "tck-id-payloads-template-instance-members-data",
        _EDGE,
        _MAY,
        _TPL,
        "A template instance in a data message may carry a subset of members.",
    ),
    (
        "tck-id-payloads-template-instance-parameters",
        _EDGE,
        _MAY,
        _TPL,
        "A template instance may carry values for its definition's parameters.",
    ),
    (
        "tck-id-payloads-template-version",
        _EDGE,
        _MUST,
        _TPL,
        "A template version, when present, is a UTF-8 string.",
    ),
    (
        "tck-id-payloads-template-ref-definition",
        _EDGE,
        _MUST,
        _TPL,
        "The template reference is absent on a definition.",
    ),
    (
        "tck-id-payloads-template-ref-instance",
        _EDGE,
        _MUST,
        _TPL,
        "The template reference on an instance is the definition's name.",
    ),
    (
        "tck-id-payloads-template-is-definition",
        _EDGE,
        _MUST,
        _TPL,
        "Every template definition and instance carries the is-definition flag.",
    ),
    (
        "tck-id-payloads-template-is-definition-definition",
        _EDGE,
        _MUST,
        _TPL,
        "The is-definition flag is true on a definition.",
    ),
    (
        "tck-id-payloads-template-is-definition-instance",
        _EDGE,
        _MUST,
        _TPL,
        "The is-definition flag is false on an instance.",
    ),
    (
        "tck-id-payloads-template-parameter-name-required",
        _EDGE,
        _MUST,
        _TPL,
        "Every template parameter definition carries a name.",
    ),
    (
        "tck-id-payloads-template-parameter-name-type",
        _EDGE,
        _MUST,
        _TPL,
        "A template parameter name is a UTF-8 string.",
    ),
    (
        "tck-id-payloads-template-parameter-value-type",
        _EDGE,
        _MUST,
        _TPL,
        "A template parameter's type field is an unsigned 32-bit integer.",
    ),
    (
        "tck-id-payloads-template-parameter-type-value",
        _EDGE,
        _MUST,
        _TPL,
        "A template parameter's type is one of the enumerated datatypes.",
    ),
    (
        "tck-id-payloads-template-parameter-type-req",
        _EDGE,
        _MUST,
        _TPL,
        "A template parameter definition in a birth carries its type.",
    ),
    (
        "tck-id-payloads-template-parameter-value",
        _EDGE,
        _MUST,
        _TPL,
        "A template parameter value uses one of the permitted protobuf scalar types.",
    ),
    (
        "tck-id-payloads-nbirth-timestamp",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH payload carries the instant it was published.",
    ),
    (
        "tck-id-payloads-nbirth-edge-node-descriptor",
        _EDGE,
        _MUST,
        _DEP,
        "Every Edge Node Descriptor in the infrastructure is unique.",
    ),
    (
        "tck-id-payloads-nbirth-seq",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH carries a sequence number inside the byte range zero to 255.",
    ),
    ("tck-id-payloads-nbirth-bdseq", _EDGE, _MUST, None, "An NBIRTH carries a bdSeq metric."),
    (
        "tck-id-payloads-nbirth-bdseq-repeat",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH bdSeq repeats the value sent in the preceding CONNECT will.",
    ),
    (
        "tck-id-payloads-nbirth-rebirth-req",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH carries a Node Control/Rebirth metric holding false.",
    ),
    ("tck-id-payloads-nbirth-qos", _EDGE, _MUST, None, "An NBIRTH is published at QoS 0."),
    (
        "tck-id-payloads-nbirth-retain",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH is published with the retain flag clear.",
    ),
    (
        "tck-id-payloads-dbirth-timestamp",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH payload carries the instant it was published.",
    ),
    ("tck-id-payloads-dbirth-seq", _EDGE, _MUST, None, "A DBIRTH carries a sequence number."),
    (
        "tck-id-payloads-dbirth-seq-inc",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH sequence number is one above the previous, returning to zero after 255.",
    ),
    (
        "tck-id-payloads-dbirth-order",
        _EDGE,
        _MUST,
        None,
        "Every DBIRTH follows the NBIRTH and precedes any NDATA or DDATA.",
    ),
    ("tck-id-payloads-dbirth-qos", _EDGE, _MUST, None, "A DBIRTH is published at QoS 0."),
    (
        "tck-id-payloads-dbirth-retain",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH is published with the retain flag clear.",
    ),
    (
        "tck-id-payloads-ndata-timestamp",
        _EDGE,
        _MUST,
        None,
        "An NDATA payload carries the instant it was published.",
    ),
    ("tck-id-payloads-ndata-seq", _EDGE, _MUST, None, "An NDATA carries a sequence number."),
    (
        "tck-id-payloads-ndata-seq-inc",
        _EDGE,
        _MUST,
        None,
        "An NDATA sequence number is one above the previous, returning to zero after 255.",
    ),
    (
        "tck-id-payloads-ndata-order",
        _EDGE,
        _MUST,
        None,
        "No NDATA leaves the edge node until the NBIRTH and every DBIRTH have gone out.",
    ),
    ("tck-id-payloads-ndata-qos", _EDGE, _MUST, None, "An NDATA is published at QoS 0."),
    (
        "tck-id-payloads-ndata-retain",
        _EDGE,
        _MUST,
        None,
        "An NDATA is published with the retain flag clear.",
    ),
    (
        "tck-id-payloads-ddata-timestamp",
        _EDGE,
        _MUST,
        None,
        "A DDATA payload carries the instant it was published.",
    ),
    ("tck-id-payloads-ddata-seq", _EDGE, _MUST, None, "A DDATA carries a sequence number."),
    (
        "tck-id-payloads-ddata-seq-inc",
        _EDGE,
        _MUST,
        None,
        "A DDATA sequence number is one above the previous, returning to zero after 255.",
    ),
    (
        "tck-id-payloads-ddata-order",
        _EDGE,
        _MUST,
        None,
        "No DDATA leaves the edge node until the NBIRTH and every DBIRTH have gone out.",
    ),
    ("tck-id-payloads-ddata-qos", _EDGE, _MUST, None, "A DDATA is published at QoS 0."),
    (
        "tck-id-payloads-ddata-retain",
        _EDGE,
        _MUST,
        None,
        "A DDATA is published with the retain flag clear.",
    ),
    (
        "tck-id-payloads-ncmd-timestamp",
        _HOST,
        _MUST,
        _OTH,
        "An NCMD payload carries the instant it was published.",
    ),
    ("tck-id-payloads-ncmd-seq", _HOST, _MUST, _OTH, "An NCMD carries no sequence number."),
    ("tck-id-payloads-ncmd-qos", _HOST, _MUST, None, "An NCMD is published at QoS 0."),
    (
        "tck-id-payloads-ncmd-retain",
        _HOST,
        _MUST,
        None,
        "An NCMD is published with the retain flag clear.",
    ),
    (
        "tck-id-payloads-dcmd-timestamp",
        _HOST,
        _MUST,
        _OTH,
        "A DCMD payload carries the instant it was published.",
    ),
    ("tck-id-payloads-dcmd-seq", _HOST, _MUST, _OTH, "A DCMD carries no sequence number."),
    ("tck-id-payloads-dcmd-qos", _HOST, _MUST, None, "A DCMD is published at QoS 0."),
    (
        "tck-id-payloads-dcmd-retain",
        _HOST,
        _MUST,
        None,
        "A DCMD is published with the retain flag clear.",
    ),
    ("tck-id-payloads-ndeath-seq", _EDGE, _MUST, None, "An NDEATH carries no sequence number."),
    (
        "tck-id-payloads-ndeath-will-message",
        _EDGE,
        _MUST,
        None,
        "The NDEATH is the will registered in the CONNECT packet.",
    ),
    (
        "tck-id-payloads-ndeath-will-message-qos",
        _EDGE,
        _MUST,
        None,
        "The NDEATH will is registered at QoS 1.",
    ),
    (
        "tck-id-payloads-ndeath-will-message-retain",
        _EDGE,
        _MUST,
        None,
        "The NDEATH will is registered with the retain flag clear.",
    ),
    (
        "tck-id-payloads-ndeath-bdseq",
        _EDGE,
        _MUST,
        None,
        "The NDEATH bdSeq is the value the matching NBIRTH will carry.",
    ),
    (
        "tck-id-payloads-ndeath-will-message-publisher",
        _EDGE,
        _SHOULD,
        None,
        "An edge node publishes an NDEATH itself before disconnecting on purpose.",
    ),
    (
        "tck-id-payloads-ndeath-will-message-publisher-disconnect-mqtt311",
        _EDGE,
        _MUST,
        _TRN,
        "On MQTT 3.1.1 that NDEATH precedes the DISCONNECT packet.",
    ),
    (
        "tck-id-payloads-ndeath-will-message-publisher-disconnect-mqtt50",
        _EDGE,
        _MUST,
        _TRN,
        "On MQTT 5.0 the DISCONNECT carries the disconnect-with-will reason code.",
    ),
    (
        "tck-id-payloads-ddeath-timestamp",
        _EDGE,
        _MUST,
        None,
        "A DDEATH payload carries the instant it was published.",
    ),
    ("tck-id-payloads-ddeath-seq", _EDGE, _MUST, None, "A DDEATH carries a sequence number."),
    (
        "tck-id-payloads-ddeath-seq-inc",
        _EDGE,
        _MUST,
        None,
        "A DDEATH sequence number is one above the previous, returning to zero after 255.",
    ),
    (
        "tck-id-payloads-ddeath-seq-number",
        _EDGE,
        _MUST,
        None,
        "The DDEATH sequence number lets a host order it against the rest of the stream.",
    ),
    (
        "tck-id-payloads-state-will-message",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application registers its STATE will in the CONNECT packet.",
    ),
    (
        "tck-id-payloads-state-will-message-qos",
        _HOST,
        _MUST,
        _OTH,
        "That STATE will is registered at QoS 1.",
    ),
    (
        "tck-id-payloads-state-will-message-retain",
        _HOST,
        _MUST,
        _OTH,
        "That STATE will is registered with the retain flag set.",
    ),
    (
        "tck-id-payloads-state-will-message-payload",
        _HOST,
        _MUST,
        _OTH,
        "That STATE will payload is JSON with a false online flag and a timestamp.",
    ),
    (
        "tck-id-payloads-state-subscribe",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application subscribes to its own STATE topic after connecting.",
    ),
    (
        "tck-id-payloads-state-birth",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application then publishes its STATE birth on that topic.",
    ),
    (
        "tck-id-payloads-state-birth-payload",
        _HOST,
        _MUST,
        _OTH,
        "That STATE birth payload is JSON with a true online flag and a timestamp.",
    ),
    # ---------------------------------------------------------- 10 Conformance
    (
        "tck-id-conformance-primary-host",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application publishes STATE messages as its birth and death certificates.",
    ),
    (
        "tck-id-conformance-mqtt-qos0",
        _SERVER,
        _MUST,
        _OTH,
        "A conformant server supports publish and subscribe at QoS 0.",
    ),
    (
        "tck-id-conformance-mqtt-qos1",
        _SERVER,
        _MUST,
        _OTH,
        "A conformant server supports publish and subscribe at QoS 1.",
    ),
    (
        "tck-id-conformance-mqtt-will-messages",
        _SERVER,
        _MUST,
        _OTH,
        "A conformant server supports will messages with retain and QoS 1.",
    ),
    (
        "tck-id-conformance-mqtt-retained",
        _SERVER,
        _MUST,
        _OTH,
        "A conformant server supports the retain flag in full.",
    ),
    (
        "tck-id-conformance-mqtt-aware-basic",
        _SERVER,
        _MUST,
        _OTH,
        "A Sparkplug Aware server meets everything a conformant server meets.",
    ),
    (
        "tck-id-conformance-mqtt-aware-store",
        _SERVER,
        _MUST,
        _OTH,
        "A Sparkplug Aware server stores the NBIRTH and DBIRTH messages passing through it.",
    ),
    (
        "tck-id-conformance-mqtt-aware-nbirth-mqtt-topic",
        _SERVER,
        _MUST,
        _OTH,
        "It republishes each NBIRTH under the sparkplug certificates topic.",
    ),
    (
        "tck-id-conformance-mqtt-aware-nbirth-mqtt-retain",
        _SERVER,
        _MUST,
        _OTH,
        "It republishes that NBIRTH with the retain flag set.",
    ),
    (
        "tck-id-conformance-mqtt-aware-dbirth-mqtt-topic",
        _SERVER,
        _MUST,
        _OTH,
        "It republishes each DBIRTH under the sparkplug certificates topic.",
    ),
    (
        "tck-id-conformance-mqtt-aware-dbirth-mqtt-retain",
        _SERVER,
        _MUST,
        _OTH,
        "It republishes that DBIRTH with the retain flag set.",
    ),
    (
        "tck-id-conformance-mqtt-aware-ndeath-timestamp",
        _SERVER,
        _MAY,
        _OTH,
        "It may restamp an NDEATH, and then uses the UTC instant of delivery.",
    ),
)

#: Every assertion, keyed by the identifier the specification anchors it with.
ASSERTIONS: Mapping[str, Assertion] = {
    row[0]: Assertion(
        assertion_id=row[0], profile=row[1], level=row[2], statement=row[4], exclusion=row[3]
    )
    for row in _ROWS
}


def assertions_for(profile: Profile) -> tuple[Assertion, ...]:
    """Every assertion constraining one conformance profile."""
    return tuple(a for a in ASSERTIONS.values() if a.profile is profile)


def in_scope_assertions() -> tuple[Assertion, ...]:
    """Every assertion this library checks, whatever its profile."""
    return tuple(a for a in ASSERTIONS.values() if a.in_scope)


def exclusions_by_reason(profile: Profile) -> Mapping[Exclusion, tuple[str, ...]]:
    """The unchecked identifiers of one profile, grouped by the missing capability."""
    grouped: dict[Exclusion, list[str]] = {}
    for assertion in assertions_for(profile):
        if assertion.exclusion is not None:
            grouped.setdefault(assertion.exclusion, []).append(assertion.assertion_id)
    return {reason: tuple(ids) for reason, ids in grouped.items()}
