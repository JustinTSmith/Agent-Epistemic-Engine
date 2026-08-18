# Agent-Epistemic-Engine

A reusable engine for building governed, agent-writable knowledge stores that
resist fabrication, drift, and silent corruption — extracted from the first
store built on it (a product-management context store for a specific
product), once the pattern proved out.

This is **not** a place to put content. It's the template: the protocol, the
validator, the CI gate, and the agent-facing instructions. Actual knowledge
stores (PM context, research notes, an ops runbook, anything an agent reads
and writes) are separate downstream repos that copy this engine in and add
their own `canon/`, `evidence/`, `derived/`, `decisions/`, `entities/`.

```
canon/      human ground truth        agents: READ ONLY
evidence/   observed facts            agents: APPEND ONLY
derived/    agent synthesis           agents: read/write, disposable
decisions/  ADRs                      immutable once accepted
entities/   people, companies, etc.   stable IDs
```

None of those directories exist in *this* repo — they're created per
downstream store. What's here is what every downstream store needs and
should not have to reinvent.

## What's in this repo

| File | Purpose |
|---|---|
| [`CONTEXT_PROTOCOL.md`](CONTEXT_PROTOCOL.md) | The rules, and the six agent failure modes each one defends against. Copy verbatim into every downstream store. |
| [`scripts/validate.py`](scripts/validate.py) | Zero-dependency validator enforcing the protocol. Stdlib only — must run from a git hook, CI, a cron, or any agent harness. |
| [`tests/test_validator.sh`](tests/test_validator.sh) + `tests/fixtures/invalid/` | Proof the guardrails actually reject bad writes, not just accept good ones. |
| [`.github/workflows/validate.yml`](.github/workflows/validate.yml) | CI gate: schema validation on every push, authority + immutability rules on every PR. |
| [`.github/pull_request_template.md`](.github/pull_request_template.md) | Forces a zone check, provenance list, and a mandatory "what I could not verify" section. |
| [`CLAUDE.md`](CLAUDE.md) | Agent entry point template (rename to `AGENTS.md` for Codex/Cursor — content is harness-neutral). |
| [`.claude/skills/context-read/`](.claude/skills/context-read/SKILL.md), [`.claude/skills/context-write/`](.claude/skills/context-write/SKILL.md) | Read/write procedures for Claude Code. Reshape for other harnesses; the procedure is what matters. |
| [`PORTABILITY.md`](PORTABILITY.md) | The same six mechanisms mapped onto Postgres, Obsidian, and other agents — for when the store needs a different backend. |

See [`QUICKSTART.md`](QUICKSTART.md) to spin up a new downstream store.

## The core idea

> Guarantees must live in the store, not in the prompt.

A rule in a system prompt is advice — a model follows it when convenient and
drops it under pressure or long context. A rule in a validator, a database
constraint, or a CI gate is physics. It holds regardless of which model or
harness is writing.

Every claim in a downstream store carries a machine-checked source:

```
<kind>:<ref> @ <YYYY-MM-DD>
```

with a trust order that puts the agent last:

```
human > interview > dataset = metric > doc > url > agent
```

An agent's own output is the least trustworthy thing in the store. It is
permanently marked as synthesis and can never be laundered into ground truth.

## Test it yourself

```bash
python3 scripts/validate.py       # zero files, zero errors — this repo has no content
./tests/test_validator.sh         # proves the fixtures are correctly rejected
```
