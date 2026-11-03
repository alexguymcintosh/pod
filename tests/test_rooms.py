"""Tests for the rooms scripts: score.py (the count) and fetch.py (placing a feed event).

Run: ./test, or python -m pytest tests/test_rooms.py. Fixtures in tests/fixtures/ use placeholder people
(Ana, Ben, Cal) so no real person's name is in the repository twice.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"
END = dt.date(2026, 11, 5)
HEADER = "| date | room | venue | why | status | who I met | what came of it |\n|---|---|---|---|---|---|---|\n"


def load(name: str):
    path = ROOT / ".agents" / "skills" / "rooms" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


score = load("score")
fetch = load("fetch")


# ---------------------------------------------------------------- rooms.md rows

def test_rows_read_the_venue_column_and_skip_a_draft_row():
    rs = score.rows(FIX / "people" / "ana" / "rooms.md")
    assert [r["date"] for r in rs] == ["2026-11-04", "2026-11-05", "2026-11-06"], "the ? draft row is not a row"
    assert rs[0]["venue"] == "Cremorne Digital Hub"
    assert rs[1]["venue"] == "6 Adolph St", "a draft row does not break the rows after it"


def test_rows_name_a_bad_first_cell_on_stderr_and_keep_reading(tmp_path, capsys):
    f = tmp_path / "rooms.md"
    f.write_text(HEADER + "| 2026-13-45 | bad month | x | | went | Sam (founder) | |\n"
                 "| 2026-11-04 17:30 | time in the date cell | x | | went | Sam (founder) | |\n"
                 "| 2026-11-04 | fine | x | | went | Sam (founder) | |\n", encoding="utf-8")
    assert [r["date"] for r in score.rows(f)] == ["2026-11-04"]
    err = capsys.readouterr().err
    assert "not a date: 2026-13-45" in err and "not a date: 2026-11-04 17:30" in err


def test_rows_with_no_table_or_a_pasted_header_do_not_break(tmp_path):
    assert score.rows(tmp_path / "missing.md") == []
    f = tmp_path / "rooms.md"
    f.write_text("just prose\n" + HEADER + HEADER.splitlines()[0] + "\n"
                 "| 2026-11-04 | fine | x | | went | Sam (founder) | |\n", encoding="utf-8")
    assert len(score.rows(f)) == 1


# ---------------------------------------------------------------- members

def test_members_are_the_who_we_are_table_union_the_folders(tmp_path):
    people = tmp_path / "people"
    (people / "ana").mkdir(parents=True)
    (people / "Dee").mkdir()
    assert score.members(people, FIX / "POD.md") == ["ana", "ben", "cal", "dee"]
    assert score.folder(people, "dee") == people / "Dee"


def test_members_ignore_other_tables_bold_links_and_drafts(tmp_path):
    pod = tmp_path / "POD.md"
    pod.write_text("## Who we are\n| member | GitHub |\n|---|---|\n| **Ana** | |\n| [Ben](people/ben/) | |\n"
                   "| ? Dee | |\n\n## Posts\n| member | post |\n|---|---|\n| Zed | a post |\n", encoding="utf-8")
    assert score.members(tmp_path / "nobody", pod) == ["ana", "ben"]


def test_members_without_a_pod_file_are_the_folders(tmp_path):
    people = tmp_path / "people"
    (people / "zed").mkdir(parents=True)
    assert score.members(people, tmp_path / "missing-POD.md") == ["zed"]


# ---------------------------------------------------------------- the count

def board():
    return {r[0]: r[1:] for r in score.board(FIX / "people", END, 7, FIX / "POD.md")}


def test_score_dedups_on_name_and_role():
    """Today's score.py counts one Sam for 'Sam (founder); Sam (PhD)'; two people were met."""
    went, met, new, *_ = board()["ana"]
    assert (went, met) == (2, 4)
    assert new == 3, "Sam (founder), Sam (PhD), Kim (ops); Sam (founder) at the second room is not new"


def test_a_member_is_dropped_on_the_first_name_alone():
    """'Ben (robotics)' is the member Ben, whatever role follows; never an outside person."""
    assert board()["ana"][1] == 4
    assert board()["ben"][1] == 1, "'Ana (founder)' is the member Ana"


def test_a_member_with_no_folder_counts_zero():
    assert board()["cal"] == (0, 0, 0, 0, 0)


def test_a_going_row_does_not_feed_seen(tmp_path):
    people = tmp_path / "people"
    (people / "ana").mkdir(parents=True)
    (people / "ana" / "rooms.md").write_text(
        HEADER + "| 2026-11-03 | planned | x | | going | Sam (founder) | |\n"
        "| 2026-11-04 | went | x | | went | Sam (founder) | |\n", encoding="utf-8")
    assert score.board(people, END, 7, tmp_path / "no-POD.md") == [("ana", 1, 1, 1, 0, 0)]


def test_people_known_ignores_draft_lines_and_counts_dated_follow_ups():
    assert score.people_known(FIX / "people" / "ana" / "network.md") == 2
    assert score.followups_queued(FIX / "people" / "ana" / "network.md") == 1, "the ? line's date is not queued"
    assert score.people_known(FIX / "people" / "ben" / "network.md") == 0, "no file, no people"


def test_a_member_line_in_network_is_never_a_person_known(tmp_path):
    net = tmp_path / "network.md"
    net.write_text("| person | met at | follow-up | knows |\n|---|---|---|---|\n"
                   "| Ben (robotics) | a room, 2026-11-04 | 2026-11-06 | |\n"
                   "| Sam (founder) | a room, 2026-11-04 | 2026-13-45 | |\n", encoding="utf-8")
    assert score.people_known(net, ["ana", "ben"]) == 1
    assert score.followups_queued(net, ["ana", "ben"]) == 0, "a bad date is not a queued follow-up"
    assert score.people_known(net) == 2, "with no pod given, every un-marked line counts"


def test_names_are_normalised_first_name_and_role():
    assert score.names("Sam  (founder);  sam(PhD) ; **Jo**. ; ? Lee (design)") == ["sam (founder)", "sam (phd)", "jo"]
    assert score.first("sam (founder)") == "sam"


@pytest.mark.parametrize("cell,expected", [("Sam (founder); Sam (PhD)", ["sam (founder)", "sam (phd)"]),
                                           ("", []), ("; ;", [])])
def test_names_list(cell, expected):
    assert score.names(cell) == expected


def test_main_prints_the_count_for_every_member(capsys):
    rc = score.main(["--people", "tests/fixtures/people", "--pod", "tests/fixtures/POD.md", "--end", "2026-11-05"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "| ana | 2 | 4 | 3 | 2 | 1 |" in out
    assert "| ben | 1 | 1 | 1 | 0 | 0 |" in out
    assert "| cal | 0 | 0 | 0 | 0 | 0 |" in out
    assert "| **pod** | 3 | 5 | 4 | 2 | 1 |" in out


def test_main_with_no_members_says_so(tmp_path, capsys):
    rc = score.main(["--people", str(tmp_path / "nobody"), "--pod", str(tmp_path / "no-POD.md"), "--end", "2026-11-05"])
    assert rc == 0
    assert "no members" in capsys.readouterr().out


# ---------------------------------------------------------------- fetch.py placing

VENUES = [{"name": "Cremorne Digital Hub, 80 Balmain St", "match": ["Cremorne Digital Hub", "80 Balmain"],
           "lat": -37.8304, "lon": 144.9945}]


def test_fetch_places_a_fixture_event_by_venue_and_by_geo():
    events = fetch.parse_ics((FIX / "rooms.ics").read_text(encoding="utf-8"))
    assert len(events) == 2
    by_venue, by_geo = events
    assert fetch.place(by_venue, VENUES) == (-37.8304, 144.9945, "Cremorne Digital Hub, 80 Balmain St")
    assert fetch.place(by_geo, VENUES) == (-37.81, 144.96, "Nowhere Hall")
    assert "folded over a second line" in fetch.unescape(by_venue["DESCRIPTION"][1])
    assert fetch.place({"LOCATION": ({}, "Unknown Place")}, VENUES) is None
