# Governed Context Store — agent instructions (template)

This file is the agent entry point. Downstream stores copy it into their own
repo root (rename to `AGENTS.md` for Codex/Cursor — content is harness-neutral)
and fill in the `<PRODUCT>` / `<DOMAIN>` placeholders.

You are operating on a governed knowledge store. Read this before touching
anything. Full rules: [CONTEXT_PROTOCOL.md](CONTEXT_PROTOCOL.md).

## The one-paragraph version

Four zones, distinguished by who may write to them. `canon/` is human ground
truth and you may **never** write to it. `evidence/` is append-only — add new
files, never edit existing ones. `derived/` is your synthesis, disposable by
design. `decisions/` are immutable once accepted. Every file carries
machine-checked provenance. You branch and open a PR; you never push to `main`.

## Before you write anything

```bash
python3 scripts/validate.py     # must be clean before AND after your change
```

## Hard rules

1. **Never write to `canon/`.** If canon looks wrong, say so in the PR body or
   write a `derived/` note arguing the case. Do not edit it.
2. **Never modify or delete an existing `evidence/` file.** Add a new one.
3. **Never edit a decision with `status: accepted`.** Write a new ADR that
   `supersedes:` it.
4. **Cite everything**, in the grammar `<kind>:<ref> @ YYYY-MM-DD`. Your own
   inference is `agent:<model> @ <date>` and carries the lowest trust of any
   source in the system.
5. **Report gaps instead of filling them.** "There is no evidence in the store
   for X" is a correct, valuable answer. A plausible invention is the single
   worst thing you can do here — it is the failure this whole system exists to
   prevent.
6. **≤ 20 files per PR.** Unreviewable diffs are where corruption hides.
7. **Never push to `main`.** Branch → PR → human review.

## Where things go

| You produced | It goes in | Required frontmatter |
|---|---|---|
| An observation, interview, data pull | `evidence/<area>/<slug>.md` | `confidence` |
| A summary, rollup, cross-cut, analysis | `derived/<slug>.md` | `confidence`, `derived_from` |
| A choice with alternatives and consequences | `decisions/NNNN-<slug>.md` (`status: proposed`) | — |
| A fact about a person, company, or other durable entity | `entities/<kind>/<slug>.md` | — |
| A change to vision, strategy, positioning, or other ground truth | **nowhere — ask the human** | — |

## Frontmatter template

```yaml
---
id: <kebab-case, must equal the filename stem>
type: <canon|evidence|derived|decision|entity>   # must match the directory
title: <human readable>
status: <draft|active|superseded|accepted|rejected|proposed>
updated: <YYYY-MM-DD, never in the future>
confidence: <high|medium|low>
sources:
  - human:<name> @ 2026-08-04
  - doc:evidence/<area>/<file>.md @ 2026-03-26
derived_from:            # type: derived only; paths must exist
  - evidence/<area>/<file>.md
---
```

Frontmatter is **flat**. Nested YAML is rejected by the parser, not silently
mis-read.

## Trust order

`human` > `interview` > `dataset` = `metric` > `doc` > `url` > `agent`

When two sources disagree, the higher tier wins regardless of how confident
the lower one sounds. Your own output is bottom of the list. That is
deliberate.

## Skills

- `.claude/skills/context-read/` — answering questions from the store
- `.claude/skills/context-write/` — proposing changes back into it
