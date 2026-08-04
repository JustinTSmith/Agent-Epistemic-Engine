# Portability — the pattern, independent of GitHub

This repo happens to use git. The pattern does not depend on git. If you take
one thing from this document, take this:

> **Guarantees must live in the store, not in the prompt.**
>
> A rule in a system prompt is *advice* — the model follows it when it is
> convenient and drops it under pressure, long context, or an ambiguous
> instruction. A rule in a validator, a database constraint, or a CI gate is
> *physics*. It holds whether the agent is Claude, GPT, a local Qwen, or a
> cron job with a bug.

Everything below is a corollary of that.

---

## The six mechanisms

Any store that will be written to by LLM agents needs these six. Name them
first, then choose a backend — never the other way round.

| # | Mechanism | Failure it prevents | How this repo does it |
|---|---|---|---|
| 1 | **Identity** | Duplicate entities (`Dr. Bill` / `drbill` / `dr-bill`) | Unique kebab `id`, must equal filename stem, collision-checked |
| 2 | **Provenance** | Fabrication | `sources:` required, grammar `<kind>:<ref> @ <date>`, in-repo refs must resolve |
| 3 | **Authority** | Agent inference overwriting human ground truth | Four zones + CODEOWNERS + `--agent-mode` blocking `canon/` |
| 4 | **Immutability** | Drift / telephone game | `evidence/` append-only; accepted decisions frozen; supersede, never edit |
| 5 | **Validation** | Silent corruption | `scripts/validate.py` in CI, exit 1 blocks the merge |
| 6 | **Review** | Plausible-but-false surviving | PR required, 20-file diff budget, mandatory "could not verify" section |

Mechanisms 1–5 are automatic. Mechanism 6 is the only one that costs human
time, which is exactly why the other five must be automatic — you want the
human spending attention on *is this true*, not on *is this well-formed*.

---

## Mapping to other backends

### Postgres

The flat frontmatter was chosen for this. It maps to a table with no
translation layer:

```sql
create table context_item (
  id          text primary key,                       -- 1. identity
  zone        text not null check (zone in ('canon','evidence','derived','decision','entity')),
  title       text not null,
  status      text not null,
  confidence  text check (confidence in ('high','medium','low')),
  body        text not null,
  updated     date not null check (updated <= current_date),
  valid_from  timestamptz not null default now(),     -- 4. immutability
  valid_to    timestamptz                             --    (temporal table)
);

create table context_source (                          -- 2. provenance
  item_id  text references context_item(id),
  kind     text not null check (kind in
             ('human','interview','doc','url','dataset','metric','agent')),
  ref      text not null,
  asserted date not null
);
```

| Mechanism | Postgres implementation |
|---|---|
| Identity | Primary key. Stronger than the filename convention here. |
| Provenance | `context_source` rows + a trigger rejecting inserts with zero sources, and canon rows whose sources are all `kind = 'agent'`. |
| Authority | Row-level security. The agent's DB role gets `SELECT` on canon, `INSERT`-only on evidence. **Stronger than git** — the agent physically cannot issue the write. |
| Immutability | Temporal/bitemporal table: `UPDATE` closes `valid_to` and inserts a new row. History is structural, not a convention. |
| Validation | `CHECK` constraints + triggers. Fires on every write, including ones that bypass your app. |
| Review | The weak spot. Postgres has no PR. You must build it: agents write to a `staging` schema, a human promotes to `main` schema. Do not skip this. |

**Net:** Postgres is *stronger* on authority and immutability, *weaker* on
review and diff-legibility. It becomes the right choice when you need
structured queries across hundreds of items, or when multiple agents write
concurrently and git conflicts start to hurt.

### Obsidian vault

Obsidian is the same file format with none of the enforcement — a vault is
`derived/` all the way down unless you add gates.

| Mechanism | Obsidian implementation |
|---|---|
| Identity | Frontmatter `id` + Dataview. Note the hazard you already hit in gbrain: wikilink resolution by basename/slug but **not title** silently breaks links. Prefer full-path links. |
| Provenance | Same `sources:` frontmatter. Dataview can list uncited notes as a live dashboard. |
| Authority | **Nothing native.** Simulate with a folder convention + git-backed vault + a pre-commit hook running this same validator. Without git behind it, you have no authority mechanism at all. |
| Immutability | Nothing native. Git-back the vault, or the telephone game is unmitigated. |
| Validation | Run `validate.py` as a pre-commit hook or a scheduled job. It is already zero-dependency for exactly this reason. |
| Review | Git-backed vault → PR. Vault-only → none. |

**Net:** Obsidian gives the best human read/write ergonomics and the worst
guarantees. The honest configuration is *Obsidian as the editing surface over
a git-backed folder* — humans get the graph view, CI still gates the writes.
An un-versioned vault edited by agents will corrupt, and you will not be able
to tell when it started.

### A different agent / harness (GPT, local Qwen, Codex, cron)

This is where the "guarantees in the store" rule pays off. What is portable
and what is not:

| Layer | Portable? | Notes |
|---|---|---|
| `validate.py` | ✅ Fully | Stdlib Python. Runs anywhere, called by anything. |
| CI gate | ✅ Fully | Any runner. GitHub Actions, a cron, a git hook. |
| Zone structure | ✅ Fully | Directories are universal. |
| Frontmatter contract | ✅ Fully | Flat text, no framework. |
| `CLAUDE.md` | ⚠️ Rename | → `AGENTS.md` (Codex, Cursor), `.github/copilot-instructions.md`, or a system prompt. Same content. |
| `.claude/skills/*` | ⚠️ Reshape | → a tool description, a prompt template, a LangGraph node, an OpenClaw skill. The *procedure* survives; the packaging does not. |

The test for whether you have built this correctly: **swap the agent for one
that has never seen your instructions, and check that it still cannot corrupt
the store.** If a naive agent with `write` access can damage your ground truth,
your guarantees were in the prompt. Mine that failure until they are not.

A local 7B model will ignore your protocol more often than Claude does. That is
not an argument for better prompting. It is an argument for the validator.

---

## Choosing a backend

| If you need… | Use |
|---|---|
| Review, diff, blame, and cheap rollback | **Git/GitHub** (this repo) |
| Structured queries, concurrent agent writes, hard authority | **Postgres** |
| Human browsing, backlinks, graph thinking | **Obsidian over git** |
| All three | Postgres as system of record → export markdown to git → sync a vault for reading. Pick **one** writable surface. Two writable surfaces means divergence, and divergence is unrecoverable once agents are writing to both. |

---

## The transferable lessons

1. **Separate authored from derived.** The highest-value structural decision
   available to you, in any backend. If you do only one thing, do this.
2. **Provenance must be machine-checkable.** `[Source: ...]` as prose is
   decoration. A grammar a script can parse is a control.
3. **Append beats overwrite.** Rewriting is where meaning erodes. Supersede.
4. **Make derived content disposable.** If you cannot delete your entire
   derived layer and regenerate it, something load-bearing has leaked into it.
5. **Budget the diff.** A 200-file agent PR is not reviewed; it is waved
   through. Cap it low enough that review is real.
6. **Reward "I don't know."** Build the store so that a reported gap is a
   first-class output. An agent that says "not in the store" is working
   correctly; one that always has an answer is fabricating and you cannot
   tell which answers.
7. **Test the guardrails.** `tests/test_validator.sh` exists because a
   validator you never saw fail is a validator you do not know works.
