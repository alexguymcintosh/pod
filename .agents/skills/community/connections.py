#!/usr/bin/env python3
"""community/connections: who knows whom across the members, names only, as network/MAP.md.

A member is a directory under people/ whose name is lower-case letters, digits and hyphens (the one
rule community.py applies; `_template`, `README` and a dotted or spaced name are not members); the
sorted list goes to people/members.json for the map page. Two members are linked when either lists the
other in knows.md ('- <name>' lines) or when the same outside 'First name (role)' is un-marked in both
their network.md tables ("if you know two people, it connects you"); that link carries the name only,
never the met-at, follow-up or knows cells. A row or line starting with '?' is a draft and is skipped; a
member is never an outside person, whatever role follows the first name. Deterministic: sorted
everywhere. Python 3.11+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")  # one member-name rule, the same line in community.py
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def clean(cell: str) -> str:
    """Bold, links, trailing punctuation and doubled spaces off: '**[Sam](x)**.' -> 'Sam'."""
    return re.sub(r"\s+", " ", LINK_RE.sub(r"\1", cell)).strip("* \t.,;:")


def norm(name: str) -> str:
    """'sam  (Founder)' -> 'sam (founder)': the key two members' spellings match on."""
    return re.sub(r"\s*\(", " (", name.lower()).strip()


def first(name: str) -> str:
    return name.split("(")[0].strip()


def members(people: Path) -> list[str]:
    if not people.is_dir():
        return []
    return sorted(d.name for d in people.iterdir() if d.is_dir() and NAME_RE.fullmatch(d.name))


def knows(path: Path) -> list[str]:
    """The '- <name>' lines of knows.md, cleaned and lower-cased; a '?' line is a draft and skipped."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines() if path.is_file() else []:
        n = clean(line[2:]) if line.startswith("- ") else ""
        if n and not n.startswith("?"):
            out.append(n.lower())
    return out


def first_cells(path: Path) -> list[str]:
    """The first cell of every data row of every table in the file; header and separator rows dropped."""
    out, header = [], None
    for line in path.read_text(encoding="utf-8").splitlines() if path.is_file() else []:
        s = line.strip()
        if not s.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = cells
        elif not all(set(c) <= set("-: ") for c in cells):
            out.append(cells[0])
    return out


def outside(path: Path, pod: set[str]) -> list[str]:
    """network.md's un-marked 'First name (role)' cells as written; a member's line is never outside."""
    out = []
    for c in first_cells(path):
        name = clean(c)
        if name and not name.startswith("?") and first(name.lower()) not in pod:
            out.append(name)
    return out


def links(people: Path, names: list[str]) -> tuple[set[tuple[str, str]], dict[tuple[str, str], set[str]]]:
    """(pairs linked by knows.md either way, pairs linked by a shared outside name -> those names)."""
    pod = {n.lower(): n for n in names}
    known: set[tuple[str, str]] = set()
    holders: dict[str, list[str]] = {}
    label: dict[str, str] = {}
    for m in names:
        for k in knows(people / m / "knows.md"):
            if k in pod and pod[k] != m:
                known.add((min(m, pod[k]), max(m, pod[k])))
        for name in outside(people / m / "network.md", set(pod)):
            key = norm(name)
            label.setdefault(key, name)
            if m not in holders.setdefault(key, []):
                holders[key].append(m)
    shared: dict[tuple[str, str], set[str]] = {}
    for key, ms in holders.items():
        for i, a in enumerate(ms):
            for b in ms[i + 1:]:
                shared.setdefault((a, b), set()).add(label[key])
    return known, shared


def node(name: str) -> str:
    """A mermaid node id: letters, digits and underscores only."""
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def link(name: str) -> str:
    return f"[{name}](../people/{name}/)"


def render(names: list[str], known: set[tuple[str, str]], shared: dict[tuple[str, str], set[str]]) -> str:
    pairs = sorted(known | set(shared))
    out = [f"# network: {len(names)} members, {len(pairs)} links, names only\n\n```mermaid\ngraph LR\n"]
    out += [f'  {node(n)}["{n}"]\n' for n in names]
    for a, b in pairs:
        via = f'|"{", ".join(sorted(shared[(a, b)]))}"|' if (a, b) in shared else ""
        out.append(f"  {node(a)} ---{via} {node(b)}\n")
    out.append("```\n\n| member | knows | shared names |\n|---|---|---|\n")
    for n in names:
        ks = [b if a == n else a for a, b in sorted(known) if n in (a, b)]
        sh = sorted((s, b if a == n else a) for (a, b), ss in shared.items() if n in (a, b) for s in ss)
        out.append(f"| {link(n)} | {'; '.join(link(k) for k in ks)} | "
                   f"{'; '.join(f'{s} with {link(o)}' for s, o in sh)} |\n")
    return "".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--people", default="people", help="members' directory, relative to the repo root")
    ap.add_argument("--out", default="network/MAP.md", help="the map page, relative to the repo root")
    ap.add_argument("--members", default="people/members.json", help="the member list the map page reads")
    a = ap.parse_args(argv)
    names = members(ROOT / a.people)
    known, shared = links(ROOT / a.people, names)
    for path, text in ((ROOT / a.members, json.dumps(names, indent=2) + "\n"),
                       (ROOT / a.out, render(names, known, shared))):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(f"connections: {len(names)} members, {len(known | set(shared))} links, {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
