# Starting a new store from this engine

## 1. Create the downstream repo

```bash
mkdir ~/Workspace/projects/<name>-context && cd ~/Workspace/projects/<name>-context
git init
mkdir -p canon evidence derived decisions entities
```

## 2. Copy the engine in

```bash
ENGINE=~/Workspace/projects/Agent-Epistemic-Engine
cp "$ENGINE/CONTEXT_PROTOCOL.md" .
cp "$ENGINE/PORTABILITY.md" .
cp "$ENGINE/CLAUDE.md" .
cp -r "$ENGINE/scripts" .
cp -r "$ENGINE/tests" .
cp -r "$ENGINE/.github" .
cp -r "$ENGINE/.claude" .
```

## 3. Fill in the placeholders

- `CLAUDE.md` — replace `<PRODUCT>` / `<DOMAIN>` with the real subject matter.
- `.claude/skills/context-read/SKILL.md`, `context-write/SKILL.md` — same.
- `.github/CODEOWNERS` — protect **this store's** `canon/`, `decisions/`,
  `schema/` (if you add one) with the actual reviewer's GitHub handle. The
  engine's own CODEOWNERS only protects the engine repo — it does not carry
  over.
- `README.md` — write one describing what this specific store holds. Do not
  reuse the engine's README; it describes the engine, not the content.

## 4. Seed real content — never invented content

Every file under `canon/`, `evidence/`, `entities/` needs a real `sources:`
entry. If you're migrating from an existing knowledge base (a vault, a wiki,
a set of docs), cite the original as `doc:<path> @ <date-it-was-written>` —
not the date you happened to copy it. Do not backfill plausible-sounding
numbers to fill gaps; leave the gap and note it explicitly. See
`CONTEXT_PROTOCOL.md` §6, rule 6.

## 5. Validate before the first commit

```bash
python3 scripts/validate.py
./tests/test_validator.sh
```

## 6. Push and wire up branch protection

```bash
gh repo create <name>-context --private --source=. --remote=origin --push
```

On GitHub: require the `validate` check to pass before merge, and require
review from the CODEOWNERS entry on any PR touching `canon/`.

## 7. Point agents at it

Drop `CLAUDE.md` at the repo root (already done in step 2) — Claude Code picks
it up automatically. For other harnesses, copy its content into `AGENTS.md`,
a system prompt, or your framework's equivalent. The content is
harness-neutral by design; only the packaging changes.

## Keeping the engine and downstream stores in sync

The engine (`CONTEXT_PROTOCOL.md`, `scripts/validate.py`, `CLAUDE.md`,
skills) will improve over time as new failure modes surface. When it does,
diff it against each downstream store and pull in the parts that changed —
there's no automatic sync (no submodule, no package). This is deliberate: a
silent auto-update to a validator that gates writes is itself a governance
risk. Update deliberately, re-run `tests/test_validator.sh` in the downstream
repo, and commit the change like any other.
