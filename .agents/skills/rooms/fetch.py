#!/usr/bin/env python3
"""rooms/fetch: public ICS feeds -> one GeoJSON of the rooms in the next N days near one city.

Run from anywhere: python3 .agents/skills/rooms/fetch.py
Defaults are Melbourne; London from Jan 2027 is the same script with flags, e.g.
  --feeds rooms/london-feeds.txt --out rooms/london.geojson --center 51.5072,-0.1276
  --tz Europe/London --city-words London
Paths are relative to the repository root. Python 3.11+, standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sys
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
UA = "pod-rooms/0 (+python urllib)"
VIRTUAL_RE = re.compile(r"\b(virtual|online|webinar|livestream)\b", re.I)  # tested on title + location
VIRTUAL_DESC_RE = re.compile(r"virtual event|online event|join from anywhere|webinar", re.I)  # description: phrases only
URL_RE = re.compile(r"https?://[^\s\\)\]>\"]+")


def parse_feeds(path: Path) -> list[tuple[str, str]]:
    """Each URL line is labelled by the nearest '# ' comment line above it."""
    feeds, label = [], ""
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("#"):
            label = s.lstrip("#").strip()
        elif s:
            feeds.append((label or s, s))
    return feeds


def unescape(v: str) -> str:
    return re.sub(r"\\([nN,;\\])", lambda m: "\n" if m.group(1) in "nN" else m.group(1), v)


def parse_ics(text: str) -> list[dict]:
    """VEVENTs as {NAME: (params, value)}; continuation lines unfolded (RFC 5545 3.1)."""
    text = re.sub(r"\r?\n[ \t]", "", text)
    events, cur = [], None
    for line in text.splitlines():
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT" and cur is not None:
            events.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            head, value = line.split(":", 1)
            name, *params = head.split(";")
            cur.setdefault(name.upper(), (dict(p.split("=", 1) for p in params if "=" in p), value))
    return events


def to_dt(prop: tuple[dict, str] | None, tz: ZoneInfo) -> dt.datetime | None:
    if not prop:
        return None
    params, v = prop
    v = v.strip()
    try:
        if len(v) == 8:  # all-day DATE
            return dt.datetime.strptime(v, "%Y%m%d").replace(tzinfo=tz)
        if v.endswith("Z"):
            return dt.datetime.strptime(v, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc).astimezone(tz)
        zone = ZoneInfo(params["TZID"]) if "TZID" in params else tz
        return dt.datetime.strptime(v, "%Y%m%dT%H%M%S").replace(tzinfo=zone).astimezone(tz)
    except (ValueError, KeyError):
        return None


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def place(ev: dict, venues: list[dict]) -> tuple[float, float, str] | None:
    """GEO first, then the first venues.json entry whose match string appears in the event text."""
    loc = unescape(ev.get("LOCATION", ({}, ""))[1])
    if "GEO" in ev:
        try:
            lat, lon = (float(x) for x in ev["GEO"][1].split(";"))
            return lat, lon, loc.split(",")[0].strip()
        except ValueError:
            pass
    for hay in (loc, unescape(ev.get("SUMMARY", ({}, ""))[1] + "\n" + ev.get("DESCRIPTION", ({}, ""))[1])):
        for v in venues:
            if any(m.lower() in hay.lower() for m in v["match"]):
                return v["lat"], v["lon"], v["name"]
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--feeds", default="rooms/feeds.txt")
    ap.add_argument("--venues", default="rooms/venues.json")
    ap.add_argument("--out", default="rooms/melbourne.geojson")
    ap.add_argument("--center", default="-37.8136,144.9631", help="lat,lon of the CBD")
    ap.add_argument("--radius-km", type=float, default=30)
    ap.add_argument("--days", type=int, default=21)
    ap.add_argument("--tz", default="Australia/Melbourne")
    ap.add_argument("--city-words", default="Melbourne,VIC", help="LOCATION words that mean in-city when unplaced")
    a = ap.parse_args(argv)

    tz = ZoneInfo(a.tz)
    center = tuple(float(x) for x in a.center.split(","))
    words = [w.strip().lower() for w in a.city_words.split(",") if w.strip()]
    venues = json.loads((ROOT / a.venues).read_text(encoding="utf-8"))["venues"]
    now = dt.datetime.now(tz)
    horizon = now + dt.timedelta(days=a.days)

    rooms, unplaced, failed, n_seen = {}, {}, 0, 0
    feeds = parse_feeds(ROOT / a.feeds)
    for community, url in feeds:
        try:
            events = parse_ics(fetch(url))
        except Exception as e:  # one dead feed must not sink the run; it is reported and counted
            print(f"FAIL  {community}: {type(e).__name__}: {e}", file=sys.stderr)
            failed += 1
            continue
        kept = 0
        for ev in events:
            n_seen += 1
            start, end = to_dt(ev.get("DTSTART"), tz), to_dt(ev.get("DTEND"), tz)
            if start is None or (end or start) < now or start > horizon:
                continue
            desc = unescape(ev.get("DESCRIPTION", ({}, ""))[1])
            loc = unescape(ev.get("LOCATION", ({}, ""))[1])
            # Luma ICS has no URL. An external listing (UID calev-...) carries its real link in LOCATION and
            # only the calendar's page in DESCRIPTION; a Luma event's LOCATION link is a bare evt- id.
            ext = loc if loc.startswith("http") and "luma.com/event/" not in loc else ""
            link = ev.get("URL", ({}, ""))[1].strip() or ext or next(iter(URL_RE.findall(desc)), "")
            props = {
                "title": unescape(ev.get("SUMMARY", ({}, ""))[1]).strip(),
                "start": start.isoformat(timespec="minutes"),
                "end": end.isoformat(timespec="minutes") if end else "",
                "url": link,
                "community": community,
                "venue": loc.split(",")[0].strip(),
            }
            # UID first: Luma keeps one UID per event across calendars, while several external
            # listings on one calendar can share a link (the calendar's own page).
            key = ev.get("UID", ({}, ""))[1].strip() or link or props["title"] + props["start"]
            if key in rooms or key in unplaced:  # same event on two calendars: credit both communities
                tgt = rooms[key]["properties"] if key in rooms else unplaced[key]
                if community not in tgt["community"].split(" / "):
                    tgt["community"] += " / " + community
                continue
            title_loc = props["title"] + " " + loc
            if VIRTUAL_RE.search(title_loc) or (not loc and VIRTUAL_DESC_RE.search(desc)):
                continue
            if loc.startswith("http"):  # Luma hides the address until you register
                props["venue"] = "address on the event page"
            spot = place(ev, venues)
            if spot:
                lat, lon, venue = spot
                if km(center, (lat, lon)) > a.radius_km:
                    continue
                props["venue"] = props["venue"] or venue
                rooms[key] = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                              "properties": props}
            elif loc and any(w in loc.lower() for w in words):
                unplaced[key] = props
            elif not loc:
                unplaced[key] = props  # a city group with no address: a human pins it
            else:
                continue
            kept += 1
        print(f"ok    {community}: {len(events)} events, {kept} kept")

    if failed == len(feeds):
        print("every feed failed; output not written", file=sys.stderr)
        return 1
    feats = sorted(rooms.values(), key=lambda f: f["properties"]["start"])
    out = {"type": "FeatureCollection", "generated": now.isoformat(timespec="minutes"),
           "window_days": a.days, "features": feats,
           "unplaced": sorted(unplaced.values(), key=lambda p: p["start"])}
    (ROOT / a.out).write_text(json.dumps(out, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
    for p in out["unplaced"]:
        print(f"unplaced  {p['start'][:16]}  {p['title']}  {p['url']}")
    print(f"rooms: {len(feats)} placed, {len(unplaced)} unplaced, {failed} feed(s) failed -> {a.out}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
