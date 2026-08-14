"""The surface an implementation exposes to be checked.

Two protocols, thirteen members between them. Each one exists because at least
one assertion cannot be observed without it, and the reason is written on the
member rather than left to be inferred. Nothing here reaches into an
implementation's internal state: every member either produces a message a
subscriber could read, renders a topic, or answers a question about a table the
specification fixes.

Implement these over your own Sparkplug code, translating its message objects
into `spbconform.model` values as you go. The translation is the adapter's only
job, and keeping it in one place is what makes the harness's observations
observations about your wire format rather than about your class layout.

Neither protocol is `runtime_checkable`. A structural check would report that
an object has thirteen attributes with the right names, which is not the
question a harness needs answered; the runner instead calls the members and
reports what came back.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from .model import Message, MessageType, NodeSpec, Will


class EdgeNodeSession(Protocol):
    """One edge node's MQTT session, from CONNECT to death.

    One session per edge node, not one per device. The devices of a node share
    its sequence number, its alias space, and its birth ordering, and several
    assertions are about exactly those shared things, so a harness that drove
    one session per device would satisfy them by accident.

    A session is driven more than once by the runner: the trace plays the
    conformant order through one, and individual checks build others to probe
    orderings the trace does not take. Every session an adapter returns starts
    unconnected.
    """

    def connect(self) -> Will | None:
        """Open the session and hand back the will to register with CONNECT.

        Needed because the will is the only thing a subscriber will ever see if
        the edge node vanishes, and four assertions are about it: that it is an
        NDEATH, that it is registered at QoS 1 with retain clear, that it
        carries the session's bdSeq and nothing else, and that it exists at
        all. Returning `None` says the implementation registers no will, which
        those checks report as the failure it is.
        """

    def node_birth(self) -> Message:
        """Publish the NBIRTH, or refuse if the session is not open.

        The birth certificate is where the sequence opens at zero, where every
        node metric is declared with a name, a datatype, and an alias, and
        where the bdSeq and rebirth control metrics appear. More assertions
        read this one message than any other.
        """

    def device_birth(self, device_id: str) -> Message:
        """Publish one device's DBIRTH, or refuse if the NBIRTH has not gone out.

        Needed for the device topic form, the alias table the later DDATA
        references, and the ordering assertion that a device cannot birth
        before the node it hangs off.
        """

    def node_data(self, changed: Mapping[str, Any]) -> Message:
        """Publish an NDATA carrying the named node metrics, or refuse.

        `changed` is what the caller says has changed. Assertions read three
        things off the result: that only those metrics are carried, that they
        are carried by alias with the name left out, and that a name no birth
        certificate declared is refused rather than published.
        """

    def device_data(self, device_id: str, changed: Mapping[str, Any]) -> Message:
        """Publish one device's DDATA, or refuse. The DDATA half of `node_data`."""

    def device_death(self, device_id: str) -> Message:
        """Publish the DDEATH for a device lost below a live edge node.

        Needed because a device going away under a node that is still connected
        is the one death the will cannot cover, and the assertion is that it is
        reported as a DDEATH on the device's own topic rather than as a data
        message or as silence.
        """

    def handle_node_command(self, command: Mapping[str, Any]) -> tuple[Message, ...]:
        """Act on an inbound NCMD and hand back everything it caused to publish.

        Needed for the six rebirth assertions. A command holding the rebirth
        metric set true republishes the NBIRTH and every DBIRTH, keeping the
        session's bdSeq and carrying no data message; any other name, and any
        other value, causes nothing. Returning an empty tuple is the honest
        answer for a command that should cause nothing.
        """

    def disconnect(self) -> Message | None:
        """Close the session deliberately, handing back the NDEATH to publish.

        Needed for the two assertions about an intentional disconnect. A client
        that closes cleanly sends no will, so an edge node shutting down on
        purpose must publish its own NDEATH first. Returning `None` says the
        implementation has no such path, which those two checks report as a
        failure rather than skipping.
        """

    def topic_for(self, message_type: MessageType, *, device_id: str | None = None) -> str:
        """Render the topic for one message type, or refuse an impossible pairing.

        Needed because NCMD, DCMD, and STATE never leave an edge node, so their
        topic form cannot be read off anything the session publishes. It is
        also how the two structural assertions are observed: a device message
        type must refuse to render without a device id, and a node message type
        must refuse one it has no level for. STATE is a Host Application topic
        and an edge-node session refuses it outright.
        """


class EdgeNodeAdapter(Protocol):
    """The implementation under test, as a factory and two published tables.

    Four members. The factory is what lets a check probe an ordering the main
    trace does not take without the harness having to reset a session it does
    not own; the other three answer questions no published message can.
    """

    def new_session(self, spec: NodeSpec) -> EdgeNodeSession:
        """Build an unconnected session for the node the harness describes.

        Needed because several assertions are about what an edge node refuses,
        and a refusal can only be observed from a session that has not yet
        reached the point where the call would be legal. The harness also
        builds a session with deliberately colliding metric names to observe
        the case-distinctness assertion, so the spec is an argument rather than
        something the adapter chooses.
        """

    def validate_ids(self, *, group_id: str, edge_node_id: str, device_id: str = "") -> None:
        """Raise if any identifier is one this implementation will not address.

        Needed for the six assertions about the identifier grammar. A Group ID,
        Edge Node ID, or Device ID holding `+`, `#`, or `/` would change the
        topic it is joined into, so an implementation must refuse it rather
        than render it. Raise `Refused`, `ValueError`, `RuntimeError`, or
        `LookupError`; return `None` to accept.
        """

    def declared_delivery(self, message_type: MessageType) -> tuple[int, bool]:
        """The QoS and retain flag this implementation publishes a class under.

        Needed for the six delivery assertions covering NCMD, DCMD, and STATE,
        which an edge node never publishes and whose flags therefore cannot be
        read off a message. The flags of the classes it does publish are read
        off the messages themselves rather than from here, so an implementation
        whose table and behavior disagree is caught rather than believed.
        """

    def quality_codes(self) -> frozenset[int]:
        """The codes this implementation can write into a `Quality` property.

        Needed because the quality assertion constrains a property the
        specification makes optional: an implementation that never emits it
        publishes nothing to check, and one that does emit it may emit a code
        on a path this harness's fixture never reaches. Return the empty set if
        the implementation writes no quality property; the check then says so
        in its observation rather than claiming to have measured something.
        """
