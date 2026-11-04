#!/usr/bin/env python3
"""community/board: the week's events board from the rooms geojson, as events/<ISO week>.md.

Reads the features fetch.py wrote (properties title, start, end, url, community and venue or location),
keeps the rooms that start within the window (--from, default today in Australia/Melbourne, for --days,
default 7), sorts them by start and writes one page: a header line with the window, then the table
when, room, where, link, community, slug. The slug is the key of going/<slug>/, the same rule as the
community skill's: lower case, runs of [a-z0-9] joined by '-', at most 60 characters. Deterministic: the
same geojson and window give the same page. A feature whose start is not a date is named on stderr and
skipped. Python 3.11+, standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[3]
HEADER = "| when | room | where | link | community | slug |\n|---|---|---|---|---|---|\n"


def slug(s: str) -> str:
    """The event key, one rule in board.py and community.py: lower-case [a-z0-9]+ runs joined by '-', cut at 60."""
    return "-".join(re.findall(r"[a-z0-9]+", s.lower()))[:60].rstrip("-")


def cell(text: object) -> str:
    """One table cell: whitespace collapsed, a pipe turned into a slash so the row stays a row."""
    return re.sub(r"\s+", " ", str(text)).replace("|", "/").strip()


def day(d: dt.date) -> str:
    """'Thu 5 Nov' (no locale, no zero padding, no platform-specific strftime flag)."""
    return f"{d:%a} {d.day} {d:%b}"


def today() -> dt.date:
    """Today in Australia/Melbourne; without tz data on the machine, its own date and a note on stderr."""
    try:
        return dt.datetime.now(ZoneInfo("Australia/Melbourne")).date()
    except ZoneInfoNotFoundError:
        print("board: no tz data; using the machine's date", file=sys.stderr)
        return dt.date.today()


def week_file(d: dt.date) -> str:
    year, week, _ = d.isocalendar()
    return f"events/{year}-W{week:02d}.md"


def select(features: list[dict], start: dt.date, days: int) -> list[tuple[dt.datetime, dict]]:
    """The features starting on start .. start + days - 1 (the event's own local date), sorted by start."""
    end = start + dt.timedelta(days=days - 1)
    out = []
    for f in features:
        p = f.get("properties", {})
        try:
            s = dt.datetime.fromisoformat(str(p.get("start", "")))
        except ValueError:
            print(f"skipped  {p.get('title', '?')}: not a start: {p.get('start')}", file=sys.stderr)
            continue
        if s.tzinfo is None:  # a start without an offset is Melbourne time, so it sorts against the others
            s = s.replace(tzinfo=ZoneInfo("Australia/Melbourne"))
        if start <= s.date() <= end:
            out.append((s, p))
    return sorted(out, key=lambda r: (r[0], str(r[1].get("title", ""))))


def render(rows: list[tuple[dt.datetime, dict]], start: dt.date, days: int) -> str:
    end = start + dt.timedelta(days=days - 1)
    out = [f"# rooms, {day(start)} to {day(end)} {end.year}\n\n", HEADER]
    for s, p in rows:
        title = p.get("title", "")
        out.append("| " + " | ".join(cell(c) for c in (
            f"{day(s)} {s:%H:%M}", title, p.get("venue") or p.get("location") or "", p.get("url", ""),
            p.get("community", ""), slug(title))) + " |\n")
    return "".join(out)


def build(features: list[dict], start: dt.date, days: int) -> str:
    return render(select(features, start, days), start, days)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--geojson", default="rooms/melbourne.geojson", help="the rooms fetch.py wrote, relative to the repo root")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--from", dest="start", default=None, help="first day, YYYY-MM-DD; default today in Melbourne")
    ap.add_argument("--out", default=None, help="the page, relative to the repo root; default events/<ISO week>.md")
    a = ap.parse_args(argv)
    if a.days < 1:
        print(f"board: --days must be 1 or more, not {a.days}", file=sys.stderr)
        return 2
    try:
        start = dt.date.fromisoformat(a.start) if a.start else today()
    except ValueError:
        print(f"board: not a date: {a.start!r} (YYYY-MM-DD)", file=sys.stderr)
        return 2
    out = a.out or week_file(start)
    try:
        features = json.loads((ROOT / a.geojson).read_text(encoding="utf-8")).get("features", [])
    except (OSError, ValueError) as e:
        print(f"board: cannot read {a.geojson}: {e}", file=sys.stderr)
        return 2
    rows = select(features, start, a.days)
    path = ROOT / out
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(rows, start, a.days), encoding="utf-8")
    print(f"board: {len(rows)} rooms, {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
