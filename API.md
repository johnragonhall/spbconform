# spbconform API

Every public name, what it does, and what it will conclude about your
implementation if you get it wrong.

## The table

### `ASSERTIONS`

`Mapping[str, Assertion]`, keyed by the identifier the specification anchors,
in specification order. 299 entries.

```python
>>> spbconform.ASSERTIONS["tck-id-topics-nbirth-seq-num"]
Assertion(assertion_id='tck-id-topics-nbirth-seq-num', profile=<Profile.EDGE_NODE>,
          level=<Level.MUST>,
          statement='An NBIRTH payload carries a sequence number whose value is zero.',
          exclusion=None)
```

### `Assertion`

| Field | Meaning |
| --- | --- |
| `assertion_id` | The identifier, spelled as the specification anchors it |
| `profile` | The conformance profile the sentence constrains |
| `level` | `MUST`, `SHOULD` or `MAY`, read from the sentence |
| `statement` | What the assertion requires, written here rather than quoted |
| `exclusion` | `None` if this library checks it; otherwise the missing capability |
| `.in_scope` | `exclusion is None` |

`statement` is the load-bearing legal detail. It is a technical requirement
written from scratch, not a quotation. The specification's own prose appears
nowhere in this distribution.

### `Profile`

`EDGE_NODE` (201), `HOST_APPLICATION` (87), `MQTT_SERVER` (11).

v3.0.0 names four target applications and marks no assertion with the one it
belongs to, so the profile here is read from the actor each sentence
constrains. It is a reading, and it is open to correction.

### `Level`

`MUST` (281), `SHOULD` (10), `MAY` (8). Read from the sentence, not from the
compatibility kit's grouping.

### `Exclusion`

Why an assertion has no check. Every value names a capability the harness
lacks, never a judgement that the assertion does not matter.

| Member | Assertions | What is missing |
| --- | --- | --- |
| `OTHER_PROFILE` | 88 | The behavior of a Host Application or an MQTT Server |
| `TEMPLATES` | 34 | Template, DataSet and PropertySet wire structures |
| `ENCODING` | 12 | Protobuf wire encoding |
| `PRIMARY_HOST` | 11 | Primary Host coordination and multi-server failover |
| `TRANSPORT` | 7 | A live MQTT client and broker |
| `DEPLOYMENT` | 4 | Uniqueness across a whole infrastructure |

### Queries

| Function | Returns |
| --- | --- |
| `assertions_for(profile)` | Every assertion constraining one profile |
| `in_scope_assertions()` | Every assertion this library checks, all profiles |
| `exclusions_by_reason(profile)` | One profile's unchecked identifiers, grouped |

### `SPEC_VERSION`, `SPEC_ASSERTION_COUNT`

`"3.0.0"` and `299`. The table carries exactly `SPEC_ASSERTION_COUNT` rows,
which is what makes the denominator checkable rather than asserted.

## Running

### `run_edge_node_conformance(adapter)`

Plays one session through the adapter and rules on every check. Returns a
`ConformanceReport`. Never raises on account of the implementation under test:
a failing check becomes a failing result, an unexpected exception becomes a
failing result naming the exception, and a session that cannot be played at all
becomes 143 failing results carrying the error that stopped it.

### `ConformanceReport`

| Member | Meaning |
| --- | --- |
| `results` | One `AssertionResult` per check, sorted by identifier |
| `coverage` | The `Coverage` for this run |
| `.failures` | The results that did not hold |
| `.conformant` | True when every check held |

`conformant` is not a conformance claim. It says the in-scope subset held, and
that subset is smaller than the edge-node profile by exactly
`coverage.edge_node_out_of_scope` assertions.

### `AssertionResult`

`assertion_id`, `passed`, and `observation`: the sentence that decided it.
Present on a pass as well as a failure, because "sequence went 3 then 4" is
what makes a pass auditable rather than merely green.

### `Coverage`

| Field | Meaning |
| --- | --- |
| `spec_version` | `"3.0.0"` |
| `spec_total` | 299 |
| `edge_node_total` | 201 |
| `edge_node_in_scope` | 133 |
| `in_scope_total` | 143, across all profiles |
| `passed`, `failed` | This run's numbers, both zero without a run |
| `out_of_scope` | `Exclusion` to count, over the whole table |
| `.edge_node_out_of_scope` | 68 |

### `edge_node_coverage(results=())`

The coverage statement, with or without a run behind it. Call it with no
arguments to read the table's shape before implementing anything.

### `format_report(report)` and `format_coverage(coverage)`

Plain text. `format_report` prints the numbers, then each failure with its
observation, then the coverage. Both end with the sentence saying this is a gap
measurement rather than a certification, because a number pasted into a ticket
travels without its context otherwise.

### `play(adapter)` and `CHECKS`

The trace and the check table, both public, for running one assertion at a time
while chasing a failure:

```python
trace = spbconform.play(MyAdapter())
print(spbconform.CHECKS["tck-id-payloads-alias-uniqueness"](trace))
```

A check returns its observation or raises `CheckFailed`.

## The adapter

Two protocols, thirteen members. Neither is `runtime_checkable`: an object with
thirteen correctly named attributes is not an edge node, so the runner calls
them and reports what came back rather than asking `isinstance`.

### Refusals

Several assertions are about what an edge node declines to do. Raise
`spbconform.Refused`, `ValueError`, `RuntimeError` or `LookupError` and the
harness reads it as a deliberate refusal. `REFUSALS` is that tuple, published so
an adapter can check itself against it.

Anything else propagates and is reported as a failure. `TypeError` in
particular is *not* a refusal, because a harness that read every exception as
deliberate would score a broken implementation as a careful one.

### `EdgeNodeAdapter`

#### `new_session(spec: NodeSpec) -> EdgeNodeSession`

Build an unconnected session for the node described. Called many times in one
run: the main trace uses one, and individual checks build others to observe
orderings the trace does not take. Every session must start unconnected and
must not share sequence or bdSeq state with its siblings.

The spec is an argument rather than something you choose, because several
checks compare what reached the topic against the identifiers handed in, and
one check hands over a spec with two metric names differing only by case. You
may refuse that spec; refusing is one of the two ways to satisfy
`tck-id-case-sensitivity-metric-names`.

#### `validate_ids(*, group_id, edge_node_id, device_id="") -> None`

Raise if any identifier is one you will not address. Six assertions read this:
an identifier holding `+`, `#` or `/` would change the topic it is joined into,
so it has to be refused rather than rendered. Return `None` to accept.

#### `declared_delivery(message_type) -> tuple[int, bool]`

The QoS and retain flag you publish a class under. Six assertions read it,
covering NCMD, DCMD and STATE, which an edge node never publishes and whose
flags therefore cannot be read off a message. The classes you *do* publish are
read off the messages themselves, so an implementation whose table and behavior
disagree is caught rather than believed.

#### `quality_codes() -> frozenset[int]`

The codes you can write into a `Quality` property. Return the empty set if you
never write one. The check compares your set against `{0, 192, 500}` and also
scans the properties that reached the fixture's payloads.

**Known vacuity.** An adapter that returns the empty set and never emits a
`Quality` property passes `tck-id-payloads-propertyset-quality-value-value`
having measured nothing. The specification makes the property optional, so
failing such an implementation would be wrong; the observation says so in
words, and it is the one check in the library that can pass without an
observation behind it.

### `EdgeNodeSession`

#### `connect() -> Will | None`

Open the session and hand back the will to register with the CONNECT packet.
Four assertions read it: that it is an NDEATH, that it is registered at QoS 1
with retain clear, that it carries the session bdSeq and nothing else, and that
it exists. Returning `None` fails those four rather than skipping them.

bdSeq opens at 0 on the first connect and advances by one per session, wrapping
after 255. One check connects 258 times on one session to see that.

#### `node_birth() -> Message`

Publish the NBIRTH, or refuse if the session is not open. More assertions read
this one message than any other: the sequence opens at 0, every node metric
carries a name, a datatype and an alias, and the `bdSeq` and
`Node Control/Rebirth` control metrics are present.

The harness expects an edge node that **uses aliases**. Birth metrics must
carry one, the rebirth command metric must not (a Host Application writes it by
name, so it has no alias to be written by), and aliases must be unique across
the whole node and at least 1. An implementation that publishes no aliases at
all fails the three alias assertions rather than skipping them.

#### `device_birth(device_id) -> Message`

Publish one DBIRTH, or refuse if the NBIRTH has not gone out.

#### `node_data(changed)` and `device_data(device_id, changed)`

Publish carrying only the named metrics, by alias, with the name left out.
Refuse a name no birth certificate declared, and refuse while any device of the
node has yet to birth.

#### `device_death(device_id) -> Message`

A device lost below a node that is still connected. The one death the will
cannot cover.

#### `handle_node_command(command) -> tuple[Message, ...]`

Return everything the command caused to publish. A command holding
`Node Control/Rebirth` set to `True` republishes the NBIRTH and every DBIRTH,
keeps the session bdSeq, and carries no data message. Any other name, and any
other value, returns `()`.

#### `disconnect() -> Message | None`

Close deliberately and hand back the NDEATH to publish. A client that
disconnects cleanly sends no will, so an edge node shutting down on purpose has
to publish its own death first. Returning `None` fails the two intentional
disconnect assertions rather than skipping them.

#### `topic_for(message_type, *, device_id=None) -> str`

Render a topic, or refuse an impossible pairing. A device message type refuses
to render without a device id; a node message type refuses one it has no level
for; `STATE` is refused outright, being a Host Application topic.

## The model

Plain frozen dataclasses and enums. Translate your own types into these in the
adapter, in one place, so the harness's observations are about your wire format
rather than your class layout.

| Name | Fields |
| --- | --- |
| `Message` | `topic`, `message_type`, `payload`, `qos`, `retain` |
| `Payload` | `timestamp`, `metrics`, `seq` |
| `Metric` | `value`, `alias`, `name`, `datatype`, `timestamp`, `properties` |
| `Will` | `message`, `qos`, `retain` |
| `MetricSpec` | `name`, `datatype`, `unit`, `eng_low`, `eng_high`, `description` |
| `NodeSpec` | `group_id`, `edge_node_id`, `node_metrics`, `devices` |

| Enum | Members |
| --- | --- |
| `MessageType` | The nine topic classes, spelled as they appear in a topic |
| `DataType` | The payload datatype enumeration, with the fixed integer values |
| `Quality` | `BAD` 0, `GOOD` 192, `STALE` 500 |

| Constant | Value |
| --- | --- |
| `NAMESPACE` | `"spBv1.0"` |
| `SEQUENCE_MODULUS` | `256` |
| `BDSEQ_METRIC` | `"bdSeq"` |
| `REBIRTH_METRIC` | `"Node Control/Rebirth"` |
| `QUALITY_CODES` | `frozenset({0, 192, 500})` |
| `UTC_FLOOR_MS` | `1577836800000` |
| `REFUSALS` | `(Refused, ValueError, RuntimeError, LookupError)` |

## The fixture

`FIXTURE` is the `NodeSpec` every check is played against. Two devices, because
several assertions are about one device's stream relative to another's and a
single-device node satisfies them by accident.

| | Value |
| --- | --- |
| Group ID | `conformance-group` |
| Edge Node ID | `edge-node-01` |
| First device, birthed first and later lost | `device-a`, one `Double` |
| Second device, which publishes the data | `device-b`, one `Float` and one `UInt32` |
| Node metric | `node_uptime_s`, `UInt64` |

The play order is CONNECT, NBIRTH, DBIRTH `device-a`, DBIRTH `device-b`, NDATA,
DDATA on `device-b`, DDEATH on `device-a`, then a rebirth request.

## How the two UTC assertions are decided

`tck-id-payloads-timestamp-in-UTC` and
`tck-id-payloads-metric-timestamp-in-UTC` ask whether a timestamp is a UTC
reading. There is no second time source to compare against, so the check reads
the value against `UTC_FLOOR_MS`, epoch milliseconds at 2020-01-01T00:00:00Z. A
timestamp at or above it is a wall-clock instant; one below it is a counter, an
uptime, or a simulation instant.

That is a heuristic and it is written down as one. It cannot catch a clock that
is wrong by an hour, and it will fail an implementation deliberately publishing
pre-2020 historical timestamps.

## The command line

```text
python -m spbconform [coverage|list|run] ...
```

| Command | Needs an adapter | Does |
| --- | --- | --- |
| `coverage` (default) | no | Prints the counts and the missing capabilities |
| `list` | no | Prints every identifier, level, scope and requirement |
| `run MODULE:ATTR` | yes | Runs every check and exits 0, or 1 on a failure |

`list` takes `--profile`, `--checked` / `--no-checked`, and `--json`. `run`
takes `--json` and `--quiet`. `coverage` takes `--json`.

`run` resolves `MODULE:ATTRIBUTE` and calls the attribute if it is callable, so
a class or a factory both work.

| Exit code | Means |
| --- | --- |
| 0 | Every check that ran held |
| 1 | At least one check found something |
| 2 | The adapter could not be imported, so nothing was measured |

2 is separate from 1 on purpose. A harness that cannot import your code has
measured nothing and must not be read as a harness that measured a pass.

## Known limitations

Worth knowing before you rely on them:

- **A pass is not conformance.** 143 checks out of 299 assertions, 133 of 201
  in the edge-node profile. The Eclipse TCK remains the arbiter.
- **The profile column is a reading.** v3.0.0 does not mark each assertion with
  the target application it belongs to, so the profile is inferred from the
  actor the sentence constrains.
- **The quality check can be vacuous.** See `quality_codes()` above.
- **The UTC check is a floor, not a clock comparison.** See above.
- **Aliases are assumed.** The harness reads an edge node that uses them; three
  assertions fail for one that does not.
- **Anything needing bytes is unchecked.** No protobuf, no broker, no STATE
  round trip. 156 rows say so, each naming what is missing.
