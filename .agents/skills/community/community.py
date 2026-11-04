#!/usr/bin/env python3
"""community.py: the club's agent interface, a few procedures over the repository's own files.

Run: python3 .agents/skills/community/community.py <command> [args] [--as <name>]
Commands: whats-on, whos-going [<event>], going <event> [--note ...], day [--date] [--from] [--force],
network, knows <name>. The member is --as <name> or `git config community.member`; a member has a
folder people/<name>/. The script writes only inside people/<me>/, going/<slug>/<me>.md and days/<date>/<me>.md:
never another member's folder, never a README.md. Exit 0 when done, 2 when refused (the reason is
printed to stderr). Python 3.11+, standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[3]
NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")  # one member-name rule, the same line in connections.py
EMAIL_RE = re.compile(r"[^\s@]+@[^\s@]+\.[a-z]{2,}", re.I)
# A whole ISO date or a whole clock time is not a phone number; one glued to more digits is part of one.
SAFE_RE = re.compile(r"(?<![\d-])\d{4}-\d{2}-\d{2}(?![\d-])|(?<![\d:])\d{1,2}:\d{2}(?![\d:])")
PHONE_RE = re.compile(r"(?:\d[\s().+-]*){8,}")  # eight or more digits; whitespace, dots, brackets, +, - between
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")  # a markdown link, kept as its text
QUOTED = ("when", "room", "where", "link")
HEADINGS = ("## what I learned", "## who I met (first name and role only)", "## follow-ups")


class Refuse(Exception):
    """The script will not do this and the message says why; main() prints it and exits 2."""


def slug(s: str) -> str:
    """The event key, one rule in board.py and community.py: lower-case [a-z0-9]+ runs joined by '-', cut at 60."""
    return "-".join(re.findall(r"[a-z0-9]+", s.lower()))[:60].rstrip("-")


def private(line: str) -> bool:
    """True when one line holds what the repository never does: an email address or a phone number."""
    return bool(EMAIL_RE.search(line) or PHONE_RE.search(SAFE_RE.sub(" ", line)))


def today() -> dt.date:
    """Today in Australia/Melbourne; without tz data on the machine, its own date and a note on stderr."""
    try:
        return dt.datetime.now(ZoneInfo("Australia/Melbourne")).date()
    except ZoneInfoNotFoundError:
        print("community: no tz data; using the machine's date", file=sys.stderr)
        return dt.date.today()


def member(root: Path, name: str | None) -> str:
    """The member the script works for: --as, else git config community.member; people/<name>/ must exist."""
    if not name:
        try:
            name = subprocess.run(["git", "config", "community.member"], cwd=root,
                                  capture_output=True, text=True).stdout
        except OSError:
            name = ""
    name = (name or "").strip().lower()
    if not name:
        raise Refuse("who are you? pass --as <name> or run: git config community.member <name>")
    if not NAME_RE.fullmatch(name) or name == "readme":
        raise Refuse(f"not a member name: {name!r} (lower-case letters, digits and hyphens)")
    if not (root / "people" / name).is_dir():
        raise Refuse(f"no folder people/{name}/: join first (README.md says how)")
    return name


def board_path(root: Path) -> Path | None:
    """The newest events/<week>.md by name (2026-W45 sorts after 2026-W44), or None when there is no board."""
    files = sorted(p for p in (root / "events").glob("*.md") if p.stem.lower() != "readme")
    return files[-1] if files else None


def board_rows(path: Path | None) -> list[dict[str, str]]:
    """The board's data rows as {column: cell}; the columns are the header row that names 'slug'."""
    if path is None:
        return []
    cols: list[str] = []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        row = [c.strip() for c in line.strip().strip("|").split("|")]
        if "slug" in [c.lower() for c in row]:
            cols = [c.lower() for c in row]
        elif cols and len(row) == len(cols) and not all(set(c) <= set("-: ") for c in row):
            rows.append(dict(zip(cols, row)))
    return rows


def board_row(path: Path | None, s: str) -> dict[str, str] | None:
    """The board row whose slug column equals s, or None."""
    return next((r for r in board_rows(path) if r["slug"] == s), None)


def board_slugs(path: Path | None) -> list[str]:
    """The slug column, top to bottom."""
    return [r["slug"] for r in board_rows(path)]


def names_in(path: Path) -> list[str]:
    """The names on a knows.md file, as written: each '- ' line before ':', link and bold off."""
    if not path.is_file():
        return []
    return [LINK_RE.sub(r"\1", ln[2:]).split(":", 1)[0].strip("* \t")
            for ln in path.read_text(encoding="utf-8").splitlines() if ln.startswith("- ")]


def going(root: Path, me: str, event: str, note: str | None = None) -> str:
    """Write going/<slug>/<me>.md: '# <me> is going: <slug>', the board's row quoted, then the note.

    One file per member per room, so the club app's prefilled new-file link can say it too. A file of mine
    already there (any case) stays as it is; another member's file is never opened. A slug that is neither a
    folder in going/ nor a board row resolves to the one board slug that contains it.
    """
    s = slug(event)
    if not s or s == "readme":
        raise Refuse(f"not an event slug: {event!r}")
    note = " ".join(note.split()) if note else ""
    if private(note):
        raise Refuse(f"that looks like an email address or a phone number, not written: {note}")
    board = board_path(root)
    if not (root / "going" / s).is_dir() and board_row(board, s) is None:
        hits = [b for b in board_slugs(board) if s in b]
        if len(hits) > 1:
            raise Refuse(f"{s!r} is on the board more than once: {', '.join(hits)}")
        if hits:
            s = hits[0]
    folder = root / "going" / s
    if folder.is_dir() and me in {p.stem.lower() for p in folder.glob("*.md")}:
        return f"{me} is already going to {s}"
    parts = [f"# {me} is going: {s}"]
    row = board_row(board, s) or {}
    quoted = " | ".join(f"{k}: {row[k]}" for k in QUOTED if row.get(k))
    if quoted:
        parts.append("> " + quoted)
    if note:
        parts.append(note)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / f"{me}.md").open("x", encoding="utf-8") as f:
        f.write("\n\n".join(parts) + "\n")
    return f"going/{s}/{me}.md: {note}" if note else f"going/{s}/{me}.md"


def going_note(path: Path) -> str:
    """The note in one going/<slug>/<member>.md: its lines that are not the heading or the quoted row."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return " ".join(ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith(("#", ">")))


def whos_going(root: Path, event: str | None = None) -> str:
    """One line per room folder in going/, '<slug>: ana (note), ben', members sorted; or the one asked for.

    An old per-room going/<slug>.md is named with where its lines go, never read as members.
    """
    folder = root / "going"
    if event:
        s = slug(event)
        old = folder / f"{s}.md"
        rooms = [old if old.is_file() and not (folder / s).is_dir() else folder / s]
    else:
        rooms = sorted((p for p in folder.glob("*") if (p.is_dir() or p.suffix == ".md") and p.stem.lower() != "readme"),
                       key=lambda p: p.stem)
    if not rooms:
        return "nobody is going anywhere yet"
    out = []
    for room in rooms:
        if room.is_file():
            out.append(f"{room.stem}: old file going/{room.name}, move each line to going/{room.stem}/<member>.md")
            continue
        files = sorted((p for p in room.glob("*.md") if p.stem.lower() != "readme"), key=lambda p: p.stem.lower())
        names = [f"{p.stem} ({n})" if (n := going_note(p)) else p.stem for p in files]
        out.append(f"{room.name}: {', '.join(names) or 'nobody yet'}")
    return "\n".join(out)


def whats_on(root: Path) -> str:
    """The newest board as it is, its first 40 lines; or a pointer to board.py."""
    path = board_path(root)
    if path is None:
        return "no board yet: run board.py"
    return "\n".join(path.read_text(encoding="utf-8").splitlines()[:40])


def day(root: Path, me: str, text: str, date: str | None = None, force: bool = False) -> str:
    """Write days/<date>/<me>.md from the text; refuse contact details, a missing consent README or an existing file."""
    date = date or today().isoformat()
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            raise ValueError
        dt.date.fromisoformat(date)
    except ValueError:
        raise Refuse(f"not a date: {date!r} (YYYY-MM-DD)") from None
    if not text.strip():
        raise Refuse("nothing to write")
    folder = root / "days" / date
    readme = folder / "README.md"
    if not readme.is_file() or not readme.read_text(encoding="utf-8").strip():
        raise Refuse(f"days/{date}/README.md is missing or empty: the consent line comes first")
    for ln in text.splitlines():
        if private(ln):
            raise Refuse(f"that looks like an email address or a phone number, not written: {ln.strip()}")
    path = folder / f"{me}.md"
    if path.exists() and not force:
        raise Refuse(f"days/{date}/{me}.md exists; pass --force to overwrite it")
    body = text.strip()
    if not any(ln.startswith("## ") for ln in body.splitlines()):
        body = "\n\n".join((f"{HEADINGS[0]}\n\n{body}", HEADINGS[1], HEADINGS[2]))
    path.write_text(f"# {me}, {date}\n\n{body}\n", encoding="utf-8")
    return f"days/{date}/{me}.md written"


def knows_path(root: Path, me: str) -> Path:
    """people/<me>/knows.md, created with its header on demand."""
    path = root / "people" / me / "knows.md"
    if not path.exists():
        path.write_text(f"# knows: {me}\n\nMembers I know, names only, one `- <name>` per line.\n\n", encoding="utf-8")
    return path


def renders(me: str, line: str) -> bool:
    """True when a network/MAP.md line carries me as connections.py writes members: my link, or my mermaid
    node id opening the line (`me["me"]`, `me --- x`) or closing an edge (`x --- me`, `x ---|"..."| me`)."""
    node = re.escape(re.sub(r"[^A-Za-z0-9_]", "_", me))
    s = line.strip()
    return (f"[{me}](" in s or re.match(rf"{node}(\[| ---)", s) is not None
            or re.search(rf"(---|\|) {node}$", s) is not None)


def network(root: Path, me: str) -> str:
    """My knows.md as it stands (never created here), then every line of network/MAP.md that renders me."""
    path = root / "people" / me / "knows.md"
    out = path.read_text(encoding="utf-8").rstrip() if path.is_file() else f"# knows: {me}\n\n(nobody yet)"
    map_file = root / "network" / "MAP.md"
    if not map_file.is_file():
        return out + "\n\nno network/MAP.md yet: run connections.py"
    hits = [ln for ln in map_file.read_text(encoding="utf-8").splitlines() if renders(me, ln)]
    return out + "\n\nnetwork/MAP.md:\n" + ("\n".join(hits) if hits else f"nothing mentions {me} yet")


def knows(root: Path, me: str, name: str) -> str:
    """Add '- <name>' to people/<me>/knows.md once; the name must be a member, so people/<name>/ exists."""
    name = name.strip().lower()
    if name == me:
        raise Refuse("that is you")
    if not NAME_RE.fullmatch(name) or not (root / "people" / name).is_dir():
        raise Refuse(f"not a member: {name!r} (no people/{name}/); names only, members only")
    path = knows_path(root, me)
    if name in {n.lower() for n in names_in(path)}:
        return f"{me} already knows {name}"
    with path.open("a", encoding="utf-8") as f:
        f.write(f"- {name}\n")
    return f"people/{me}/knows.md: - {name}"


def main(argv: list[str] | None = None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--as", dest="me", metavar="NAME", help="the member; default: git config community.member")
    common.add_argument("--root", type=Path, default=ROOT, help="the repository root (default: this checkout)")
    ap = argparse.ArgumentParser(prog="community.py", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("whats-on", parents=[common], help="the newest events board")
    p = sub.add_parser("whos-going", parents=[common], help="who is going where")
    p.add_argument("event", nargs="?")
    p = sub.add_parser("going", parents=[common], help="say I am going to <event>")
    p.add_argument("event")
    p.add_argument("--note", default=None, help="one line next to your name")
    p = sub.add_parser("day", parents=[common], help="write my day log from stdin or --from")
    p.add_argument("--date", help="YYYY-MM-DD, default today")
    p.add_argument("--from", dest="src", type=Path, help="read the text from this file instead of stdin")
    p.add_argument("--force", action="store_true", help="overwrite my existing log for that day")
    sub.add_parser("network", parents=[common], help="who I know and where the map links me")
    p = sub.add_parser("knows", parents=[common], help="add a member I know")
    p.add_argument("name")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "whats-on":
            out = whats_on(a.root)
        elif a.cmd == "whos-going":
            out = whos_going(a.root, a.event)
        else:
            me = member(a.root, a.me)
            if a.cmd == "going":
                out = going(a.root, me, a.event, a.note)
            elif a.cmd == "day":
                if a.src and not a.src.is_file():
                    raise Refuse(f"no such file: {a.src}")
                text = a.src.read_text(encoding="utf-8") if a.src else sys.stdin.read()
                out = day(a.root, me, text, a.date, a.force)
            elif a.cmd == "network":
                out = network(a.root, me)
            else:
                out = knows(a.root, me, a.name)
    except Refuse as e:
        print(f"community: {e}", file=sys.stderr)
        return 2
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
