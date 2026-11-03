#!/usr/bin/env python3
"""rooms/score: the Sunday count from people/<name>/rooms.md and people/<name>/network.md.

Per member, for the last N days (default 7, ending today): rooms with status 'went', people met, new
outside people met (a 'First name (role)' in 'who I met' that is not a pod member and that this member
has not logged at an earlier room), people known (lines in network.md the member has un-marked) and
follow-ups queued (people-known lines with a date in 'follow-up'). A pod member is a row in POD.md's
"Who we are" table or a directory under people/; a member is never an outside person, whatever role
follows the first name. A row whose first cell starts with '?' is a draft and is not counted; so is a
name starting with '?'. Python 3.11+, standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def clean(cell: str) -> str:
    """Bold, links and trailing punctuation off a cell: '**[Sam](x)**.' -> 'Sam'."""
    return LINK_RE.sub(r"\1", cell).strip("* \t.,;:")


def table_text(text: str) -> list[dict]:
    """Every table row as a dict keyed by the lower-case header; separator rows and a pasted header dropped."""
    out, header = [], None
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
        elif all(set(c) <= set("-: ") for c in cells) or [c.lower() for c in cells] == header:
            continue
        else:
            out.append(dict(zip(header, cells)))
    return out


def table(path: Path) -> list[dict]:
    return table_text(path.read_text(encoding="utf-8")) if path.is_file() else []


def draft(row: dict) -> bool:
    return next(iter(row.values()), "").startswith("?")


def valid_date(s: str) -> bool:
    if not DATE_RE.match(s):
        return False
    try:
        dt.date.fromisoformat(s)
    except ValueError:
        return False
    return True


def rows(path: Path) -> list[dict]:
    """rooms.md rows with a YYYY-MM-DD first cell, under key 'date'; a '?' draft is skipped silently, any
    other first cell that is not a date is named on stderr and skipped, and the rows after it still read."""
    out = []
    for r in table(path):
        if draft(r):
            continue
        d = next(iter(r.values()), "")
        if not valid_date(d):  # one member's typo must not sink the pod's count; name it and skip
            print(f"skipped  {path.parent.name}/{path.name}: not a date: {d}", file=sys.stderr)
            continue
        r["date"] = d
        out.append(r)
    return out


def names(cell: str) -> list[str]:
    """'Sam  (founder); sam(PhD); ? Jo' -> ['sam (founder)', 'sam (phd)']: one person per 'First name (role)'."""
    out = []
    for n in cell.split(";"):
        n = re.sub(r"\s*\(", " (", re.sub(r"\s+", " ", clean(n).lower()))
        if n and not n.startswith("?"):
            out.append(n)
    return out


def first(name: str) -> str:
    return name.split("(")[0].strip()


def members(people_dir: Path, pod_md: Path) -> list[str]:
    """POD.md's "Who we are" table union the directories under people/, lower-case, sorted."""
    found = {d.name.lower() for d in people_dir.iterdir() if d.is_dir()} if people_dir.is_dir() else set()
    if pod_md.is_file():
        text = pod_md.read_text(encoding="utf-8")
        m = re.search(r"^## Who we are\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
        for r in table_text(m.group(1) if m else ""):
            name = clean(r.get("member", ""))
            if name and not draft(r):
                found.add(name.lower())
    return sorted(found)


def folder(people_dir: Path, member: str) -> Path:
    """The member's directory whatever its case; a member with no directory gets the lower-case path."""
    if people_dir.is_dir():
        for d in people_dir.iterdir():
            if d.is_dir() and d.name.lower() == member:
                return d
    return people_dir / member


def known(path: Path, pod: list[str] | tuple[str, ...] = ()) -> list[dict]:
    """network.md lines the member has un-marked; a pod member's line is never a person known."""
    return [r for r in table(path) if not draft(r) and first(clean(r.get("person", "")).lower()) not in pod]


def people_known(path: Path, pod: list[str] | tuple[str, ...] = ()) -> int:
    return len(known(path, pod))


def followups_queued(path: Path, pod: list[str] | tuple[str, ...] = ()) -> int:
    return sum(1 for r in known(path, pod) if valid_date(r.get("follow-up", "")))


def board(people_dir: Path, end: dt.date, days: int, pod_md: Path) -> list[tuple[str, int, int, int, int, int]]:
    start = end - dt.timedelta(days=days - 1)
    pod = members(people_dir, pod_md)
    result = []
    for m in pod:
        home = folder(people_dir, m)
        log = sorted(rows(home / "rooms.md"), key=lambda r: r["date"])
        seen: set[str] = set()
        went = met = new = 0
        for r in log:
            d = dt.date.fromisoformat(r["date"])
            if d > end or r.get("status", "").lower() != "went":
                continue
            who = [n for n in names(r.get("who i met", "")) if first(n) not in pod]
            if start <= d:
                went += 1
                met += len(who)
                new += len({n for n in who if n not in seen})
            seen.update(who)
        net = home / "network.md"
        result.append((m, went, met, new, people_known(net, pod), followups_queued(net, pod)))
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--people", default="people", help="members' directory, relative to the repo root")
    ap.add_argument("--pod", default="POD.md", help="the group's document, relative to the repo root")
    ap.add_argument("--end", default=dt.date.today().isoformat(), help="last day of the week, YYYY-MM-DD")
    ap.add_argument("--days", type=int, default=7)
    a = ap.parse_args(argv)
    end = dt.date.fromisoformat(a.end)
    rs = board(ROOT / a.people, end, a.days, ROOT / a.pod)
    if not rs:
        print(f"no members under {a.people}/ or in {a.pod} yet")
        return 0
    print(f"rooms count, {end - dt.timedelta(days=a.days - 1)} to {end}\n")
    print("| member | rooms went | people met | new outside people | people known | follow-ups queued |")
    print("|---|---|---|---|---|---|")
    for m, *n in rs:
        print(f"| {m} | " + " | ".join(str(x) for x in n) + " |")
    print("| **pod** | " + " | ".join(str(sum(r[i] for r in rs)) for i in range(1, 6)) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
