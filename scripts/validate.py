#!/usr/bin/env python3
"""
Context store validator. Zero dependencies (Python 3.9+ stdlib only).

This is the enforcement layer of CONTEXT_PROTOCOL.md. Every rule that the
protocol states in prose is checked here in code. If a rule is not checked
here, assume it will be violated -- prose does not survive contact with an
agent in a hurry.

Usage:
    python3 scripts/validate.py                 # validate whole repo
    python3 scripts/validate.py --agent-mode    # additionally enforce
                                                #   agent-write restrictions
                                                #   against git HEAD
    python3 scripts/validate.py --base main     # diff target for agent mode

Exit code 0 = clean, 1 = violations found.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent  # overridable via --root (see main)

# --- The contract -----------------------------------------------------------

# Directories that carry typed content, and the `type` each one must declare.
TYPED_DIRS = {
    "canon": "canon",
    "evidence": "evidence",
    "derived": "derived",
    "decisions": "decision",
    "entities": "entity",
}

# Provenance grammar. A source is machine-checkable or it is decoration.
#   kind:ref @ YYYY-MM-DD
SOURCE_KINDS = ["human", "interview", "doc", "url", "dataset", "metric", "agent"]
SOURCE_RE = re.compile(
    r"^(?P<kind>" + "|".join(SOURCE_KINDS) + r"):(?P<ref>\S+)\s+@\s+(?P<date>\d{4}-\d{2}-\d{2})$"
)

# Trust ordering. Higher wins when two sources disagree.
TRUST = {
    "human": 100,
    "interview": 80,
    "dataset": 70,
    "metric": 70,
    "doc": 60,
    "url": 40,
    "agent": 10,
}

STATUSES = {"draft", "active", "superseded", "accepted", "rejected", "proposed"}
CONFIDENCES = {"high", "medium", "low"}

REQUIRED_ALWAYS = ["id", "type", "title", "status", "updated", "sources"]
REQUIRED_BY_TYPE = {
    "derived": ["confidence", "derived_from"],
    "evidence": ["confidence"],
}

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#]+?)(?:#[^)]*)?\)")

# Frontmatter keys that hold a list of strings.
LIST_KEYS = {"sources", "derived_from", "supersedes", "tags", "related"}


# --- Minimal frontmatter parser ---------------------------------------------
# Deliberately supports only a flat subset of YAML: scalars and lists of
# scalars. Nested structures are REJECTED rather than silently mis-parsed.
# The narrow schema is a feature: it is what lets this file have zero
# dependencies, and it is what makes the store portable to a SQL table.


class FrontmatterError(Exception):
    pass


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        raise FrontmatterError("file does not begin with a '---' frontmatter block")
    end = text.find("\n---", 3)
    if end == -1:
        raise FrontmatterError("frontmatter block is never closed with '---'")
    block = text[4:end]

    data: dict = {}
    current_list_key = None

    for lineno, raw in enumerate(block.split("\n"), start=2):
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue

        if line.startswith("  - ") or line.startswith("- "):
            if current_list_key is None:
                raise FrontmatterError(f"line {lineno}: list item with no parent key")
            data[current_list_key].append(_scalar(line.split("- ", 1)[1].strip()))
            continue

        if line.startswith(" "):
            raise FrontmatterError(
                f"line {lineno}: nested mapping is not allowed -- "
                f"the schema is intentionally flat"
            )

        if ":" not in line:
            raise FrontmatterError(f"line {lineno}: expected 'key: value', got {line!r}")

        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        if value == "":
            data[key] = []
            current_list_key = key
        else:
            data[key] = _scalar(value)
            current_list_key = None

    return data


def _scalar(v: str):
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


# --- Checks -----------------------------------------------------------------


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, path, msg) -> None:
        self.errors.append(f"{path}: {msg}")

    def warn(self, path, msg) -> None:
        self.warnings.append(f"{path}: {msg}")


def content_files() -> list[Path]:
    out = []
    for d in TYPED_DIRS:
        root = REPO / d
        if root.is_dir():
            out.extend(sorted(p for p in root.rglob("*.md") if p.is_file()))
    return out


def validate_file(path: Path, rep: Report, seen_ids: dict) -> None:
    rel = path.relative_to(REPO)
    text = path.read_text(encoding="utf-8")

    try:
        fm = parse_frontmatter(text)
    except FrontmatterError as e:
        rep.error(rel, str(e))
        return

    # --- required keys
    top = rel.parts[0]
    expected_type = TYPED_DIRS[top]
    for key in REQUIRED_ALWAYS + REQUIRED_BY_TYPE.get(expected_type, []):
        if key not in fm or fm[key] in ("", []):
            rep.error(rel, f"missing required frontmatter key '{key}'")

    if "type" in fm and fm["type"] != expected_type:
        rep.error(rel, f"type is '{fm['type']}' but it lives under {top}/ (expected '{expected_type}')")

    # --- id: unique, well-formed, matches filename
    fid = fm.get("id")
    if isinstance(fid, str) and fid:
        if not ID_RE.match(fid):
            rep.error(rel, f"id '{fid}' must be lowercase kebab-case")
        if fid in seen_ids:
            rep.error(rel, f"duplicate id '{fid}' (also in {seen_ids[fid]})")
        else:
            seen_ids[fid] = rel
        if path.stem != fid:
            rep.error(rel, f"id '{fid}' must match filename stem '{path.stem}'")

    # --- status / confidence
    if fm.get("status") not in STATUSES and "status" in fm:
        rep.error(rel, f"status '{fm.get('status')}' not one of {sorted(STATUSES)}")
    if "confidence" in fm and fm["confidence"] not in CONFIDENCES:
        rep.error(rel, f"confidence '{fm['confidence']}' not one of {sorted(CONFIDENCES)}")

    # --- updated date
    upd = fm.get("updated", "")
    if isinstance(upd, str) and upd:
        if not DATE_RE.match(upd):
            rep.error(rel, f"updated '{upd}' must be ISO YYYY-MM-DD")
        else:
            try:
                if dt.date.fromisoformat(upd) > dt.date.today():
                    rep.error(rel, f"updated '{upd}' is in the future")
            except ValueError:
                rep.error(rel, f"updated '{upd}' is not a real date")

    # --- provenance: the core anti-hallucination check
    sources = fm.get("sources", [])
    if isinstance(sources, str):
        rep.error(rel, "sources must be a list, not a single scalar")
        sources = [sources]

    kinds = []
    for s in sources:
        m = SOURCE_RE.match(s)
        if not m:
            rep.error(
                rel,
                f"source {s!r} does not match required grammar "
                f"'<kind>:<ref> @ YYYY-MM-DD' with kind in {SOURCE_KINDS}",
            )
            continue
        kinds.append(m.group("kind"))
        if m.group("kind") == "doc":
            ref = m.group("ref")
            # doc: refs that look like in-repo paths must actually resolve.
            if ref.startswith(tuple(TYPED_DIRS)) and not (REPO / ref).exists():
                rep.error(rel, f"source doc:{ref} points at a path that does not exist")

    # canon may never rest on agent inference alone.
    if expected_type == "canon" and kinds and all(k == "agent" for k in kinds):
        rep.error(
            rel,
            "canon file is sourced only from 'agent:' -- ground truth requires "
            "a human, interview, doc, dataset or metric source",
        )

    # derived must declare and resolve its inputs.
    if expected_type == "derived":
        for dep in fm.get("derived_from", []):
            if not (REPO / dep).exists():
                rep.error(rel, f"derived_from '{dep}' does not exist")

    # low-confidence claims must not masquerade as canon.
    if expected_type == "canon" and fm.get("confidence") == "low":
        rep.error(rel, "canon file may not be confidence: low -- promote it or move it to derived/")

    # --- relative links resolve
    body = text[text.find("\n---", 3) + 4 :]
    for target in LINK_RE.findall(body):
        t = target.strip()
        if t.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (path.parent / t).resolve() if not t.startswith("/") else (REPO / t.lstrip("/"))
        if not resolved.exists():
            rep.error(rel, f"broken relative link -> {t}")


def validate_agent_mode(base: str, rep: Report) -> None:
    """Rules that only apply to a proposed change, not to the store at rest."""
    try:
        changed = subprocess.run(
            ["git", "diff", "--name-status", f"{base}...HEAD"],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError as e:
        rep.warn("<git>", f"could not diff against {base}: {e.stderr.strip()}")
        return

    if not changed:
        return

    rows = [ln.split("\t") for ln in changed.split("\n") if ln.strip()]

    # 1. Agents may not touch canon/ at all.
    for row in rows:
        status, path = row[0], row[-1]
        if path.startswith("canon/"):
            rep.error(path, "agent-authored change touches canon/ -- canon is human-only")

    # 2. Evidence is append-only: agents may add files, never modify or delete.
    for row in rows:
        status, path = row[0], row[-1]
        if path.startswith("evidence/") and status[0] in ("M", "D"):
            verb = "modify" if status[0] == "M" else "delete"
            rep.error(path, f"agent-authored change tries to {verb} existing evidence -- evidence is append-only")

    # 3. Accepted decisions are immutable.
    for row in rows:
        status, path = row[0], row[-1]
        if path.startswith("decisions/") and status[0] in ("M", "D"):
            prev = subprocess.run(
                ["git", "show", f"{base}:{path}"], cwd=REPO, capture_output=True, text=True
            )
            if prev.returncode == 0 and "status: accepted" in prev.stdout:
                rep.error(path, "accepted decision was modified -- supersede it with a new ADR instead")

    # 4. Diff budget: a huge agent PR is unreviewable, and unreviewable is
    #    where corruption lives.
    if len(rows) > 20:
        rep.error("<diff>", f"{len(rows)} files changed in one agent PR (budget 20) -- split it")


def main() -> int:
    global REPO
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent-mode", action="store_true")
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--root", default=None,
                    help="validate a different tree (used by the fixture tests)")
    args = ap.parse_args()

    if args.root:
        REPO = Path(args.root).resolve()

    rep = Report()
    seen_ids: dict = {}

    files = content_files()
    for f in files:
        validate_file(f, rep, seen_ids)

    if args.agent_mode:
        validate_agent_mode(args.base, rep)

    for w in rep.warnings:
        print(f"warn  {w}")
    for e in rep.errors:
        print(f"ERROR {e}")

    print(f"\n{len(files)} file(s) checked, {len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
