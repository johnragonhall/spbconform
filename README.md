# spbconform

[![CI](https://github.com/ragonxdragon/spbconform/actions/workflows/ci.yml/badge.svg)](https://github.com/ragonxdragon/spbconform/actions/workflows/ci.yml)

The Eclipse Sparkplug B v3.0.0 assertion table, and a runner that checks your
edge node against it. Zero dependencies, MIT, clean-room.

The specification anchors 299 assertions with a `tck-testable` role. This
library carries every one of them, each written as a requirement in its own
words, together with an executable check for the 143 an in-process harness can
observe and a recorded reason for each of the 156 it cannot.

```python
from spbconform import run_edge_node_conformance, format_report

report = run_edge_node_conformance(MyAdapter())
print(format_report(report))
raise SystemExit(0 if report.conformant else 1)
```

Or from the command line, against nothing at all:

```bash
python -m spbconform coverage
python -m spbconform list --profile edge-node --no-checked
python -m spbconform run myproject.spb_adapter:Adapter
```

## What this is not

**It is not the Eclipse Sparkplug Technology Compatibility Kit, and it does not
certify conformance.** The TCK is the arbiter; it is a Java suite under EPL-2.0,
it drives a real broker, and passing it is what conformance means. This library
measures a gap against a published list of assertion identifiers. A green run
here says the 143 checks it carries held. It says nothing about the other 156,
and it is not evidence you can hand to anyone as certification.

**It contains no EPL-2.0 code and no specification prose.** The identifiers are
facts: they are the anchors the specification publishes so that other documents
can cross-reference them. Each `statement` in the table is a technical
requirement written here from scratch, never copied. No line of the Eclipse TCK
was read while building this, and no normative sentence is reproduced. That
clean-room property is the library's whole legal value, and a test in the suite
guards the obvious regression.

## Install

```bash
pip install spbconform
```

Python 3.12 or newer. Nothing else, ever: `spbconform` has no dependencies at
runtime and none at test time. The table is a tuple of tuples, the runner is
dataclasses and callables, and the command line is `argparse` and `json`.

That is a deliberate constraint rather than an accident of scope. A conformance
harness is installed in order to decide whether something else is trustworthy,
so every dependency it carries becomes something your reviewers have to read
and your scanners have to clear.

## The honest numbers

| | Count |
| --- | --- |
| Assertions the specification anchors as `tck-testable` | 299 |
| Constraining the edge-node profile | 201 |
| Edge-node assertions this library checks | **133** |
| Edge-node assertions it cannot check | **68** |
| Checks in the library, across all profiles | **143** |

The extra ten are Host Application and MQTT Server assertions an edge node can
still be held to, because an edge node declares delivery flags for topic
classes it never publishes on.

Why the 68 are unchecked, and why the other 88 rows are out of reach:

| Missing capability | Assertions | Of which edge-node |
| --- | --- | --- |
| The behavior of a Host Application or an MQTT Server | 88 | 0 |
| Template, DataSet and PropertySet wire structures | 34 | 34 |
| Protobuf wire encoding | 12 | 12 |
| Primary Host coordination and multi-server failover | 11 | 11 |
| A live MQTT client and broker | 7 | 7 |
| Uniqueness across a whole infrastructure | 4 | 4 |

Those reasons stay in the output. `format_report` prints them under every run,
`coverage --json` carries them as counts, and `list --no-checked` names the
identifiers one by one. Pruning the denominator to what already passes would
turn a coverage number into a decoration, so the pruning is recorded instead of
performed.

## What it does

**Carries the whole published list.** 299 rows, each with the profile it
constrains, the requirement level its sentence takes, a statement of what it
asks, and either a check or a named missing capability. `python -m spbconform
list` prints it with no implementation involved, which makes the table useful
on its own as a reading of what v3.0.0 actually requires of an edge node.

**Checks what an edge node puts on the wire.** Every check reads a published
message or a refusal: a topic, a sequence number, an alias, a delivery flag, a
birth certificate's metric set, the will registered at CONNECT. None of them
reach into private state, because an assertion is about what a subscriber sees
and a check that read your attributes would pass for a node that publishes
something else entirely.

**Plays one session, then probes the orderings it did not take.** The main
trace runs CONNECT, NBIRTH, two DBIRTHs, NDATA, DDATA, DDEATH and a rebirth.
Around it, individual checks build fresh sessions to observe what your edge
node refuses: publishing before CONNECT, a DBIRTH before its NBIRTH, a metric
no birth certificate declared, a device topic with no device id.

**Reports an observation, not a verdict.** Every result carries the sentence
that decided it, passing or failing, so a failure tells you what was seen
rather than only which identifier went red:

```text
FAIL tck-id-payloads-alias-data-cmd-requirement
     a DDATA metric still carries the name 'read_rate'
```

**Survives a broken implementation.** An adapter that raises where the
specification expects a message is reported as failing the assertions that read
that message. An adapter that cannot be played at all fails all 143 with the
error that stopped it. Neither produces a traceback out of the runner, because
a stack trace with no assertion identifiers in it hides every other result
behind the first one.

**Proves its own checks can fail.** A conformance runner whose checks cannot
fail reports a pass for anything. The suite plants 42 documented breaks in a
reference edge node, one at a time, and fails if any check survives all of
them. The baseline is a full pass, so the sweep has to account for all 143
checks with no carve-out.

## Writing an adapter

Implement two protocols over your own Sparkplug code, translating its messages
into `spbconform.model` values as you go. Thirteen members in total, each
documented with the assertion that needs it:

| `EdgeNodeAdapter` | |
| --- | --- |
| `new_session(spec)` | Build an unconnected session for the node the harness describes |
| `validate_ids(...)` | Raise for an identifier holding `+`, `#` or `/` |
| `declared_delivery(type)` | The QoS and retain flag for a class you never publish |
| `quality_codes()` | The codes you can write into a `Quality` property |

| `EdgeNodeSession` | |
| --- | --- |
| `connect()` | Open, and hand back the will to register |
| `node_birth()` | Publish the NBIRTH, or refuse |
| `device_birth(id)` | Publish one DBIRTH, or refuse |
| `node_data(changed)` | Publish an NDATA, or refuse |
| `device_data(id, changed)` | Publish a DDATA, or refuse |
| `device_death(id)` | Publish a DDEATH for a device lost under a live node |
| `handle_node_command(cmd)` | Act on an NCMD and return what it published |
| `disconnect()` | Close deliberately, returning the NDEATH to publish |
| `topic_for(type, device_id=)` | Render a topic, or refuse an impossible pairing |

`tests/reference.py` is a complete worked example in about 500 lines. See
`API.md` for the full contract, including which exceptions count as a refusal
and what each check will conclude if a member returns `None`.

## What it deliberately does not do

- **No broker, no socket, no bytes.** The harness is in-process. The seven
  assertions that need a live MQTT connection are recorded as unchecked rather
  than approximated against a mock, because an assertion checked against a mock
  is an assertion about the mock.
- **No protobuf.** Twelve encoding assertions and 34 Template, DataSet and
  PropertySet assertions need a wire codec. They are in the table, they are
  counted, and they are not checked.
- **No Host Application and no MQTT Server profile.** 88 assertions constrain
  actors an edge node is not. They are carried so the denominator is the whole
  specification rather than the part this library answers.
- **No conformance certification.** That is the TCK's job, and this library
  says so wherever it prints a number.

## License

MIT. Copyright (c) 2026 John Hall.

Eclipse Sparkplug and the Sparkplug specification are the property of the
Eclipse Foundation. This project is not affiliated with or endorsed by it.
