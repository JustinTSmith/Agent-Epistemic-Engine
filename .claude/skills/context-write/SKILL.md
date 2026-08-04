---
name: context-write
description: Propose a change back into the a governed context store — new research findings, interview notes, metric snapshots, competitive updates, synthesis, or a decision record. Use whenever work produces an insight that should persist. Handles zone routing, provenance, validation, branching and PR creation.
---

# Writing back to the context store

Writes are governed. Getting the zone wrong is the most common and most
damaging mistake, so route first and write second.

## Step 1 — route by zone

| What you have | Zone | Notes |
|---|---|---|
| Something you *observed* (interview, data pull, metric, scan) | `evidence/<area>/` | **new file only** |
| Something you *concluded* by reasoning over other files | `derived/` | must list `derived_from` |
| A *choice* being made, with alternatives | `decisions/NNNN-<slug>.md` | open as `status: proposed` |
| A fact about a person/company | `entities/<kind>/<slug>.md` | reuse the existing `id` |
| A change to vision, strategy, positioning | **STOP** | canon is human-only — raise it in the PR body |

If you are unsure between `evidence/` and `derived/`, ask: *did I witness this,
or did I work it out?* Witnessed is evidence. Worked out is derived.

## Step 2 — never edit, add

- Existing `evidence/` file wrong? Add a **new** file that corrects it and set
  `supersedes:` on the new one. The original stays as it was recorded.
- Accepted decision wrong? Write a **new** ADR with `supersedes:`.
- Entity page: you may update it, but move any *new claim* into an
  `evidence/` file and cite it from the entity page.

## Step 3 — cite honestly

```
<kind>:<ref> @ <YYYY-MM-DD>
```

The date is **when the source said it**, not when you wrote the file. If a
2026-03 market scan is your input, the date is `2026-03-26`, not today.

Your own reasoning is `agent:<model> @ <today>`. Include it — it is not a
confession, it is metadata. But a `derived/` file whose *only* source is
`agent:` and which cites no `derived_from` is worthless; it means you made
something up.

Set `confidence` truthfully:
- `high` — directly observed or stated by a primary source
- `medium` — solid inference, or a primary source with known estimate inputs
- `low` — synthesis, extrapolation, anything you would not defend in a meeting

## Step 4 — validate, branch, PR

```bash
python3 scripts/validate.py            # must be clean
git checkout -b context/<short-slug>
git add -A && git commit -m "<zone>: <what>"
git push -u origin HEAD
gh pr create --fill
```

Never push to `main`. Keep it under 20 files.

## Step 5 — declare what you could not verify

The PR template has a "Things I could NOT verify" section. It is **required**
and "none" is only an acceptable answer if it is true. This section is the
highest-value thing you write, because it is the part a reviewer cannot
reconstruct on their own.
