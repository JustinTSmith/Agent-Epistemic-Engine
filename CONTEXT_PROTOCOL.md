# Context Protocol

The rules governing any store built on this engine. Every rule here is
enforced by `scripts/validate.py` and CI. A rule that lives only in prose is
a rule that will be broken by the first agent in a hurry.

This document is product-agnostic. It was extracted from the first store
built on it — a PM context store for a specific product — once the pattern
proved out. Downstream stores copy this file verbatim; they should not need
to edit it.

---

## 1. Why this exists

An LLM agent working over a knowledge base fails in six specific ways. This
engine is designed around those six failures, not around "storing documents."

| Failure | What it looks like | Defence |
|---|---|---|
| **Fabrication** | Agent asserts a fact nobody actually established | Every claim carries a machine-checked `sources:` entry |
| **Authority inversion** | Agent's inference overwrites what a human actually said | Trust tiers; `canon/` is human-only and CI-enforced |
| **Drift / telephone game** | Each rewrite subtly shifts meaning until the original is gone | `evidence/` is append-only; `derived/` is regenerated, never edited |
| **Silent corruption** | A bad edit lands unreviewed among dozens of other files | Diff budget (20 files) + PR-only writes + human review |
| **Duplication** | The same entity gets three different IDs across three files | Stable unique `id`, checked for collisions |
| **Provenance loss** | A claim is in the doc; nobody knows where it came from | `sources:` required, grammar-checked, `doc:` refs must resolve |

---

## 2. The trust hierarchy

The single most important idea in this engine. When two statements conflict,
the higher tier wins — always, without exception, regardless of how confident
the lower tier sounds.

```
human      100   A human said it directly. Outranks everything.
interview   80   A customer, user, or stakeholder said it, on the record.
dataset     70   A structured export (a database dump, an analytics pull).
metric      70   An instrumented measurement.
doc         60   A written source: a PRD, a report, an external filing.
url         40   A public web page.
agent       10   An LLM inferred, summarised, or synthesised it.
```

**An agent's own output is the least trustworthy thing in the building.**
That is the whole point of the tiering. `agent:` sourcing is legal — synthesis
is useful — but it is permanently marked as synthesis and can never be
laundered into ground truth.

---

## 3. The four zones

Writes are governed by *where* content lives, not by who is asking.

### `canon/` — human-authored ground truth
Vision, strategy, positioning, hard constraints — whatever counts as ground
truth for this domain. **Agents may read. Agents may never write.** Enforced
two ways: CODEOWNERS requires human review, and `validate.py --agent-mode`
fails any PR touching `canon/`.

If an agent believes canon is wrong, the correct move is to open an issue or
write a `derived/` note arguing the case. Not to edit canon.

### `evidence/` — append-only observation
Interviews, data pulls, metric snapshots, scans. Agents **may add new files**.
Agents may **never modify or delete** an existing one. An observation made on
a given date stays exactly as it was recorded; if it turns out to be wrong,
you add a new file that supersedes it. This is what kills the telephone game.

### `derived/` — agent synthesis, disposable by design
Summaries, rollups, matrices, cross-cuts. Every file declares `derived_from:`
listing the real paths it was built from, and CI verifies those paths exist.
**If you deleted this whole directory, you would lose nothing you could not
regenerate.** That property is the safety valve: derived content can never be
load-bearing.

### `decisions/` — ADRs, immutable once accepted
A decision with `status: accepted` can never be edited. To change your mind,
write a new ADR that `supersedes:` the old one. The record of *what you
believed when you chose* is preserved, which is the only thing that makes a
decision log worth keeping.

---

## 4. The entity registry

`entities/` is **not** a trust zone. The four zones above are defined by *write
authority* — who may write, and under what constraint. `entities/` is defined by
*identity*: it is the registry that gives durable things a stable handle so the
same person, company, or persona is not re-created under three different names
across the store.

### `entities/` — stable-ID pages
People, organisations, competitors, personas, anything with a durable
identity. Stable `id` prevents the duplication failure.

Entity pages still obey the frontmatter contract and the source grammar below;
they simply are not governed by a zone-specific write rule the way `canon/`,
`evidence/`, `derived/`, and `decisions/` are.

---

## 5. The frontmatter contract

Deliberately **flat** — scalars and lists of scalars only. Nested YAML is
rejected by the parser rather than silently mis-read. Three reasons: it needs
no dependencies, it maps 1:1 onto a SQL table, and it is hard to get subtly
wrong.

```yaml
---
id: some-stable-slug               # unique, kebab-case, == filename stem
type: canon                        # must match the directory
title: Human Readable Title
status: active                     # draft|active|superseded|accepted|rejected|proposed
updated: 2026-08-04                # ISO, never in the future
confidence: high                   # required for evidence/ and derived/
sources:
  - human:you @ 2026-08-04
  - doc:evidence/some-area/some-file.md @ 2026-03-26
derived_from:                      # required for type: derived
  - evidence/some-area/some-file.md
---
```

### Source grammar
```
<kind>:<ref> @ <YYYY-MM-DD>
```
`kind` ∈ `human | interview | doc | url | dataset | metric | agent`.

The `@ date` is *when the source said it*, not when you wrote the file. That
distinction is what lets you spot a claim resting on a stale number.

---

## 6. Rules an agent must follow

1. **Read before you write.** Never assert into the store what you have not
   read out of it.
2. **Never write to `canon/`.**
3. **Never edit an existing `evidence/` file.** Add a new one.
4. **Never edit an accepted decision.** Supersede it.
5. **Cite everything.** If you cannot name a source, you do not have a fact —
   you have a guess. Mark it `agent:` and `confidence: low`, or omit it.
6. **Say "not in the store."** A gap reported honestly is worth more than a
   plausible invention. This is the single most valuable agent behaviour here.
7. **Small PRs.** 20 files maximum. Unreviewable diffs are where corruption
   hides.
8. **Never push to `main`.** Branch, PR, wait for a human.
9. **Run the validator before opening a PR:** `python3 scripts/validate.py`

---

## 7. What CI enforces

`python3 scripts/validate.py` (every push):
- frontmatter parses, is flat, has required keys for its type
- `id` unique, kebab-case, matches filename
- `sources` present and grammar-valid; in-repo `doc:` refs resolve
- canon is not sourced from `agent:` alone, and is never `confidence: low`
- `derived_from` paths exist
- `updated` is a real ISO date, not in the future
- relative links resolve

`--agent-mode` (pull requests only, diffed against the base branch):
- no change touches `canon/`
- no modification or deletion under `evidence/`
- no modification of an accepted decision
- diff budget: ≤ 20 files

---

## 8. The write loop

```
  read canon/ + relevant evidence/
        │
        ▼
  do the work (tools, connectors, analysis)
        │
        ▼
  new observation? ──► evidence/<area>/<slug>.md   (new file, cited)
  new synthesis?   ──► derived/<slug>.md           (derived_from: [...])
  new choice?      ──► decisions/NNNN-<slug>.md    (status: proposed)
  canon is wrong?  ──► say so in the PR body. Do not edit canon.
        │
        ▼
  python3 scripts/validate.py   ──► fix violations
        │
        ▼
  branch ──► PR ──► human review ──► merge
```

The human review step is not ceremony. It is the only place in the loop where
something that is *plausible but false* can be caught.
