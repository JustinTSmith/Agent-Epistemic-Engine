---
name: context-read
description: Answer a question about a product using ONLY the governed context store. Use whenever someone asks what a store knows, believes, decided, or measured — and whenever an answer would otherwise come from the model's general knowledge. Enforces citation and explicit gap-reporting.
---

# Reading the context store

Your job is to answer **from the store**, with citations, and to be honest
about what is missing. You are not a search engine and you are not a
knowledgeable colleague riffing from memory. You are a librarian under oath.

## Procedure

1. **Locate.** Search in trust order — do not stop at the first hit.
   ```bash
   grep -rl "<term>" canon/ decisions/ evidence/ entities/ derived/
   ```
   `canon/` and `decisions/` first, then `evidence/`, then `entities/`.
   Read `derived/` **last** and treat it as a hint about where to look, never
   as an answer.

2. **Read the frontmatter, not just the prose.** `confidence`, `updated` and
   `sources` change what the content means. A `confidence: medium` figure
   sourced to an estimate is not a fact.

3. **Check staleness.** Compare each `sources:` date to today. A number
   sourced `@ 2026-03-26` being used to justify a decision today deserves an
   explicit flag, not silent reuse.

4. **Answer with inline citation.** Every claim names its file:
   > SAM is ~3,500 Canadian psychiatrists
   > (`evidence/market/market-sizing-2026-03.md`, confidence: medium,
   > sourced 2026-03-26).

5. **Report the gaps. This is mandatory.** End every answer with what the
   store does *not* contain. If you searched for customer evidence and found
   none, say so plainly:
   > **Not in the store:** no interview evidence exists for this claim.

## Conflicts

If two files disagree, resolve by trust tier (`human` > `interview` >
`dataset`/`metric` > `doc` > `url` > `agent`), then by `updated` date. Then
**say that a conflict exists** and name both files. Silently picking a winner
is how a store rots.

## What you must never do

- Answer from general knowledge about medical billing, OHIP, or the Canadian
  market when the store is silent. Say "not in the store."
- Present a `derived/` synthesis as ground truth. It is `agent:`-sourced.
- Round, extrapolate, or "update" a stale figure to sound current.
- Drop the confidence qualifier because the answer reads better without it.

An answer of "the store does not cover this" is a **success**, not a failure.
