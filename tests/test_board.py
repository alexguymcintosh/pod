"""Tests for the community skill's board.py: the week's events board from the rooms geojson.

Run: ./test, or python -m pytest tests/test_board.py. The fixture geojson in tests/fixtures/board/ holds
made-up rooms; no network.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import inspect
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "board" / "rooms.geojson"
START = dt.date(2026, 11, 4)


def load(name: str):
    path = ROOT / ".agents" / "skills" / "community" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


board = load("board")


def features() -> list[dict]:
    return json.loads(FIX.read_text(encoding="utf-8"))["features"]


# ---------------------------------------------------------------- slug

def test_slug_is_lower_case_runs_of_letters_and_digits_joined_by_hyphens():
    assert board.slug("Couch Conversations: The Community View") == "couch-conversations-the-community-view"
    assert board.slug("Melbourne | AI Founder Co-working Day x StartSpace") == "melbourne-ai-founder-co-working-day-x-startspace"
    assert board.slug("Women's Day 2026") == "women-s-day-2026"


def test_slug_is_cut_at_sixty_characters_and_never_ends_in_a_hyphen():
    s = board.slug("word " * 30)
    assert len(s) <= 60 and not s.endswith("-")
    assert board.slug("") == ""


def test_slug_is_byte_identical_to_the_community_script_s():
    assert inspect.getsource(board.slug) == inspect.getsource(load("community").slug)


# ---------------------------------------------------------------- build

def test_build_keeps_the_window_and_sorts_by_start(capsys):
    page = board.build(features(), START, 7)
    lines = page.splitlines()
    assert lines[0] == "# rooms, Wed 4 Nov to Tue 10 Nov 2026"
    assert lines[2] == "| when | room | where | link | community | slug |"
    rows = lines[4:]
    assert [r.split(" | ")[0] for r in rows] == ["| Wed 4 Nov 17:30", "| Thu 5 Nov 09:00", "| Thu 5 Nov 17:30",
                                                 "| Tue 10 Nov 09:00"], "the last day of the window is in"
    assert "Before the window" not in page and "After the window" not in page
    assert "skipped  Bad start (fixture): not a start: soon" in capsys.readouterr().err


def test_build_writes_where_link_community_and_slug():
    page = board.build(features(), START, 7)
    assert ("| Thu 5 Nov 17:30 | Robots Night (fixture) | 6 Adolph St | https://example.test/robots "
            "| Robots Club (fixture) | robots-night-fixture |") in page
    assert "| Melbourne / Founder Co-working Day (fixture) | State Library (fixture) |" in page, \
        "a pipe in the title cannot break the table; location is the fallback for venue"
    assert "| the-very-long-title-of-a-room-whose-slug-must-be-cut-at-sixt |" in page


def test_select_gives_a_naive_start_melbourne_time_before_sorting():
    naive = {"properties": {"title": "Naive", "start": "2026-11-05T17:30"}}
    aware = {"properties": {"title": "Aware", "start": "2026-11-05T09:00+11:00"}}
    rows = board.select([naive, aware], START, 7)
    assert [p["title"] for _, p in rows] == ["Aware", "Naive"]
    assert rows[1][0].utcoffset() == dt.timedelta(hours=11)


def test_build_with_no_rooms_is_the_header_and_an_empty_table():
    assert board.build(features(), dt.date(2027, 1, 1), 7).count("\n") == 4


def test_week_file_is_the_iso_week_of_the_first_day():
    assert board.week_file(START) == "events/2026-W45.md"
    assert board.week_file(dt.date(2027, 1, 3)) == "events/2026-W53.md"


def test_today_is_melbourne_or_the_machine_date_without_tz_data(monkeypatch, capsys):
    assert isinstance(board.today(), dt.date)

    def no_tz(key):
        raise board.ZoneInfoNotFoundError(key)

    monkeypatch.setattr(board, "ZoneInfo", no_tz)
    assert board.today() == dt.date.today()
    assert capsys.readouterr().err == "board: no tz data; using the machine's date\n"


# ---------------------------------------------------------------- main

def test_main_writes_the_page_and_prints_the_summary(tmp_path, capsys):
    out = tmp_path / "events" / "week.md"
    rc = board.main(["--geojson", str(FIX), "--from", "2026-11-04", "--days", "2", "--out", str(out)])
    assert rc == 0
    assert capsys.readouterr().out == f"board: 3 rooms, {out}\n"
    assert out.read_text(encoding="utf-8").startswith("# rooms, Wed 4 Nov to Thu 5 Nov 2026\n")


def test_main_reports_a_bad_from_or_days_on_stderr_with_exit_2(tmp_path, capsys):
    out = tmp_path / "w.md"
    assert board.main(["--geojson", str(FIX), "--from", "2026-13-45", "--out", str(out)]) == 2
    assert capsys.readouterr().err == "board: not a date: '2026-13-45' (YYYY-MM-DD)\n"
    assert board.main(["--geojson", str(FIX), "--from", "2026-11-04", "--days", "0", "--out", str(out)]) == 2
    assert capsys.readouterr().err == "board: --days must be 1 or more, not 0\n"
    assert not out.exists()


def test_main_reports_a_missing_geojson_on_stderr_with_exit_2(tmp_path, capsys):
    missing = tmp_path / "nope.geojson"
    assert board.main(["--geojson", str(missing), "--from", "2026-11-04", "--out", str(tmp_path / "w.md")]) == 2
    err = capsys.readouterr().err
    assert err.startswith("board: cannot read ") and str(missing) in err and "Traceback" not in err
    assert not (tmp_path / "w.md").exists()


def test_main_defaults_to_the_repo_geojson_today_in_melbourne_and_the_iso_week_file(tmp_path, monkeypatch, capsys):
    (tmp_path / "rooms").mkdir()
    shutil.copy(FIX, tmp_path / "rooms" / "melbourne.geojson")
    monkeypatch.setattr(board, "ROOT", tmp_path)
    monkeypatch.setattr(board, "today", lambda: START)
    assert board.main([]) == 0
    assert capsys.readouterr().out == "board: 4 rooms, events/2026-W45.md\n"
    assert (tmp_path / "events" / "2026-W45.md").is_file()
