"""Tests for the community skill's script: every command, every refusal, idempotence.

Run: ./test, or python -m pytest tests/test_community.py. The repository is built in tmp_path with
placeholder members (ana, ben); nothing touches the network or a real git config.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load():
    path = ROOT / ".agents" / "skills" / "community" / "community.py"
    spec = importlib.util.spec_from_file_location("community", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


com = load()

BOARD = """# what's on: 2026-W45

| rank | slug | when | room | where | link | why |
|---|---|---|---|---|---|---|
| 1 | agentic-ai-melbourne | Thu 2026-11-05 17:30 | Agentic AI Melbourne | address on the event page | https://example.test/agentic | high-bar |
| 2 | couch-conversations | Wed 2026-11-04 17:30 | Couch Conversations | Cremorne Digital Hub | https://example.test/couch | left-field |
"""
CONSENT = "# 2026-11-05\n\nConsent: names only, first name and role, nothing said in confidence.\n"
DAY = Path("days") / "2026-11-05"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    for name in ("ana", "ben"):
        (tmp_path / "people" / name).mkdir(parents=True)
    (tmp_path / "events").mkdir()
    (tmp_path / "events" / "2026-W44.md").write_text("# old board\n", encoding="utf-8")
    (tmp_path / "events" / "2026-W45.md").write_text(BOARD, encoding="utf-8")
    (tmp_path / DAY).mkdir(parents=True)
    (tmp_path / DAY / "README.md").write_text(CONSENT, encoding="utf-8")
    return tmp_path


def no_git(monkeypatch, stdout: str = "") -> None:
    monkeypatch.setattr(com.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=stdout))


# ---------------------------------------------------------------- slug and member

@pytest.mark.parametrize("text,expected", [
    ("Agentic AI Melbourne", "agentic-ai-melbourne"),
    ("  Couch: Conversations! (Nov) ", "couch-conversations-nov"),
    ("x" * 70, "x" * 60),
    ("???", ""),
])
def test_slug_is_lower_case_alnum_runs_joined_by_hyphens_capped_at_60(text, expected):
    assert com.slug(text) == expected


def test_slug_never_ends_in_a_hyphen_after_the_cut():
    s = com.slug("word " * 30)
    assert len(s) <= 60 and not s.endswith("-")


def test_member_from_the_as_flag_is_lower_cased_and_must_have_a_folder(repo):
    assert com.member(repo, "Ana") == "ana"
    with pytest.raises(com.Refuse, match="no folder people/zed/"):
        com.member(repo, "zed")


def test_member_falls_back_to_git_config(repo, monkeypatch):
    no_git(monkeypatch, "ben\n")
    assert com.member(repo, None) == "ben"


def test_member_is_unknown_when_git_config_is_empty_or_git_is_missing(repo, monkeypatch):
    no_git(monkeypatch)
    with pytest.raises(com.Refuse, match="who are you"):
        com.member(repo, None)

    def boom(*a, **k):
        raise FileNotFoundError("git")

    monkeypatch.setattr(com.subprocess, "run", boom)
    with pytest.raises(com.Refuse, match="who are you"):
        com.member(repo, "")


@pytest.mark.parametrize("bad", ["../ana", "readme", "Ana Smith", "-x"])
def test_member_rejects_a_name_that_is_not_a_folder_name(repo, bad):
    with pytest.raises(com.Refuse, match="not a member name"):
        com.member(repo, bad)


# ---------------------------------------------------------------- going

def test_going_writes_my_own_file_with_the_board_row_quoted_then_the_note(repo):
    out = com.going(repo, "ana", "Agentic AI Melbourne", "demo  at\n6")
    text = (repo / "going" / "agentic-ai-melbourne" / "ana.md").read_text(encoding="utf-8")
    assert text == ("# ana is going: agentic-ai-melbourne\n\n"
                    "> when: Thu 2026-11-05 17:30 | room: Agentic AI Melbourne | "
                    "where: address on the event page | link: https://example.test/agentic\n\n"
                    "demo at 6\n")
    assert out == "going/agentic-ai-melbourne/ana.md: demo at 6"
    assert not (repo / "going" / "agentic-ai-melbourne.md").exists(), "no per-room file any more"


def test_going_is_idempotent_and_a_second_member_gets_a_second_file(repo):
    assert com.going(repo, "ana", "couch-conversations") == "going/couch-conversations/ana.md"
    assert com.going(repo, "ana", "couch-conversations", "second time") == "ana is already going to couch-conversations"
    folder = repo / "going" / "couch-conversations"
    assert "second time" not in (folder / "ana.md").read_text(encoding="utf-8")
    com.going(repo, "ben", "couch-conversations", "  ")
    assert sorted(p.name for p in folder.iterdir()) == ["ana.md", "ben.md"]
    assert (folder / "ben.md").read_text(encoding="utf-8").startswith("# ben is going: couch-conversations\n\n> when: ")
    assert (folder / "ben.md").read_text(encoding="utf-8").endswith("link: https://example.test/couch\n")


def test_going_never_touches_another_members_file(repo):
    folder = repo / "going" / "couch-conversations"
    folder.mkdir(parents=True)
    ben = folder / "ben.md"
    ben.write_bytes(b"# ben is going: couch-conversations\n\nby hand\n")
    com.going(repo, "ana", "couch-conversations", "with ben")
    assert ben.read_bytes() == b"# ben is going: couch-conversations\n\nby hand\n"
    assert sorted(p.name for p in folder.iterdir()) == ["ana.md", "ben.md"]


def test_going_sees_my_hand_written_file_in_any_case(repo):
    folder = repo / "going" / "couch-conversations"
    folder.mkdir(parents=True)
    (folder / "Ana.md").write_text("# Ana is going: couch-conversations\n", encoding="utf-8")
    assert com.going(repo, "ana", "couch-conversations") == "ana is already going to couch-conversations"
    assert [p.name for p in folder.iterdir()] == ["Ana.md"]


BOARD2 = """# what's on: 2026-W46

| rank | slug | when | room | where | link | why |
|---|---|---|---|---|---|---|
| 1 | agentic-ai-melbourne-november-2026 | Thu 2026-11-12 17:30 | Agentic AI Melbourne | Cremorne | https://example.test/agentic | high-bar |
| 2 | clay-club-tuesday | Tue 2026-11-10 18:00 | Clay Club | 6 Adolph St | https://example.test/clay | left-field |
| 3 | clay-club-thursday | Thu 2026-11-12 18:00 | Clay Club | 6 Adolph St | https://example.test/clay2 | left-field |
"""


def test_board_slugs_are_the_slug_column_in_board_order(repo):
    assert com.board_slugs(repo / "events" / "2026-W45.md") == ["agentic-ai-melbourne", "couch-conversations"]
    assert com.board_slugs(None) == []


def test_going_resolves_a_short_slug_to_the_one_board_slug_that_contains_it(repo):
    (repo / "events" / "2026-W46.md").write_text(BOARD2, encoding="utf-8")
    assert com.going(repo, "ana", "Agentic AI Melbourne", "demo") == "going/agentic-ai-melbourne-november-2026/ana.md: demo"
    text = (repo / "going" / "agentic-ai-melbourne-november-2026" / "ana.md").read_text(encoding="utf-8")
    assert text.startswith("# ana is going: agentic-ai-melbourne-november-2026\n\n> when: Thu 2026-11-12 17:30 | ")
    assert not (repo / "going" / "agentic-ai-melbourne").exists()
    assert com.going(repo, "ana", "agentic ai melbourne") == "ana is already going to agentic-ai-melbourne-november-2026"
    (repo / "going" / "clay-club").mkdir()
    assert com.going(repo, "ben", "Clay Club") == "going/clay-club/ben.md", "an existing folder is the key as it is"


def test_going_refuses_a_short_slug_that_several_board_slugs_contain(repo):
    (repo / "events" / "2026-W46.md").write_text(BOARD2, encoding="utf-8")
    with pytest.raises(com.Refuse, match="'clay-club' is on the board more than once: clay-club-tuesday, clay-club-thursday"):
        com.going(repo, "ana", "Clay Club")
    assert not (repo / "going").exists()


def test_going_to_a_room_not_on_the_board_has_no_quoted_row(repo):
    com.going(repo, "ana", "Clay Club", "link https://example.test/clay")
    assert (repo / "going" / "clay-club" / "ana.md").read_text(encoding="utf-8") == (
        "# ana is going: clay-club\n\nlink https://example.test/clay\n")
    (repo / "events" / "2026-W45.md").unlink()
    (repo / "events" / "2026-W44.md").unlink()
    com.going(repo, "ana", "No Board")
    assert (repo / "going" / "no-board" / "ana.md").read_text(encoding="utf-8") == "# ana is going: no-board\n"


@pytest.mark.parametrize("note", ["mail me: ana@example.test", "call 0412 345 678", "0412-34-5678"])
def test_going_refuses_a_note_that_looks_like_an_email_or_a_phone_number(repo, note):
    with pytest.raises(com.Refuse) as e:
        com.going(repo, "ana", "couch-conversations", note)
    assert note in str(e.value)
    assert not (repo / "going").exists()


@pytest.mark.parametrize("bad", ["???", "README"])
def test_going_refuses_an_empty_or_reserved_slug(repo, bad):
    with pytest.raises(com.Refuse, match="not an event slug"):
        com.going(repo, "ana", bad)
    assert not (repo / "going").exists()


def test_board_row_is_found_by_header_name_whatever_the_column_order(tmp_path):
    b = tmp_path / "b.md"
    b.write_text("prose\n| link | slug |\n|---|---|\n| https://x | one |\n| short row |\n", encoding="utf-8")
    assert com.board_row(b, "one") == {"link": "https://x", "slug": "one"}
    assert com.board_row(b, "two") is None
    b.write_text("| room | when |\n|---|---|\n| no slug column | one |\n", encoding="utf-8")
    assert com.board_row(b, "one") is None
    assert com.board_row(None, "one") is None


# ---------------------------------------------------------------- whos-going and whats-on

def test_whos_going_reads_the_folders_members_sorted_notes_shown(repo):
    assert com.whos_going(repo) == "nobody is going anywhere yet"
    com.going(repo, "ben", "Agentic AI Melbourne")
    com.going(repo, "ana", "Agentic AI Melbourne", "demo")
    com.going(repo, "ben", "Clay Club", "with ana")
    (repo / "going" / "README.md").write_text("not a room\n", encoding="utf-8")
    (repo / "going" / "clay-club" / "README.md").write_text("not a member\n", encoding="utf-8")
    (repo / "going" / "empty-room").mkdir()
    assert com.whos_going(repo) == "agentic-ai-melbourne: ana (demo), ben\nclay-club: ben (with ana)\nempty-room: nobody yet"
    assert com.whos_going(repo, "Agentic AI Melbourne") == "agentic-ai-melbourne: ana (demo), ben"
    assert com.whos_going(repo, "nope") == "nope: nobody yet"


def test_whos_going_reads_a_file_the_app_wrote_by_hand(repo):
    folder = repo / "going" / "couch-conversations"
    folder.mkdir(parents=True)
    (folder / "cal.md").write_text("# cal is going: couch-conversations\n\n> when: x\n\nfirst time\nsay hi\n", encoding="utf-8")
    assert com.whos_going(repo) == "couch-conversations: cal (first time say hi)"


def test_whos_going_names_an_old_per_room_file_loudly(repo):
    (repo / "going").mkdir()
    (repo / "going" / "clay-club.md").write_text("# going: clay-club\n- ana: demo\n", encoding="utf-8")
    (repo / "going" / "notes.txt").write_text("not a room\n", encoding="utf-8")
    com.going(repo, "ben", "couch-conversations")
    assert com.whos_going(repo) == (
        "clay-club: old file going/clay-club.md, move each line to going/clay-club/<member>.md\n"
        "couch-conversations: ben")
    assert com.whos_going(repo, "Clay Club") == (
        "clay-club: old file going/clay-club.md, move each line to going/clay-club/<member>.md")


def test_whats_on_prints_the_newest_board_capped_at_40_lines(repo):
    assert com.whats_on(repo) == BOARD.rstrip("\n")
    (repo / "events" / "2026-W46.md").write_text("\n".join(f"line {i}" for i in range(50)), encoding="utf-8")
    assert com.whats_on(repo).splitlines() == [f"line {i}" for i in range(40)]


def test_whats_on_without_a_board_points_at_board_py(tmp_path):
    assert com.whats_on(tmp_path) == "no board yet: run board.py"


# ---------------------------------------------------------------- day

def test_day_writes_the_card_under_the_fixed_header_and_headings(repo):
    assert com.day(repo, "ana", "Learned that agents need a budget.\n", "2026-11-05") == "days/2026-11-05/ana.md written"
    assert (repo / DAY / "ana.md").read_text(encoding="utf-8") == (
        "# ana, 2026-11-05\n\n## what I learned\n\nLearned that agents need a budget.\n\n"
        "## who I met (first name and role only)\n\n## follow-ups\n")


def test_day_keeps_the_text_own_headings(repo):
    com.day(repo, "ana", "## who I met (first name and role only)\n\n- Sam (founder)\n", "2026-11-05")
    text = (repo / DAY / "ana.md").read_text(encoding="utf-8")
    assert text == "# ana, 2026-11-05\n\n## who I met (first name and role only)\n\n- Sam (founder)\n"


@pytest.mark.parametrize("line", ["mail sam at sam@example.test tomorrow", "call 0412345678", "ref 12345678 later",
                                  "call 0412 345 678", "or +61 (0) 412-345-678", "landline (03) 9123 4567",
                                  "0412-34-5678", "04123-45-678", "call 0412\u00a0345\u00a0678"])
def test_day_refuses_an_email_or_a_phone_number_and_quotes_the_line(repo, line):
    assert com.private(line)
    with pytest.raises(com.Refuse) as e:
        com.day(repo, "ana", f"fine line, 2026-11-05 at 17:30\n{line}\n", "2026-11-05")
    assert line in str(e.value)
    assert not (repo / DAY / "ana.md").exists()


def test_day_accepts_dates_times_and_small_numbers(repo):
    text = "2026-11-05 17:30 to 19:00 at 80 Balmain St, level 3; 40 people, 2 talks; ISO 2026-11-05T17:30+11:00; $1,200,000\n"
    assert com.day(repo, "ana", text, "2026-11-05") == "days/2026-11-05/ana.md written"


def test_day_refuses_without_the_consent_readme(repo):
    (repo / "days" / "2026-11-06").mkdir()
    with pytest.raises(com.Refuse, match="days/2026-11-06/README.md is missing"):
        com.day(repo, "ana", "x", "2026-11-06")
    with pytest.raises(com.Refuse, match="README.md is missing"):
        com.day(repo, "ana", "x", "2026-11-07")


def test_day_refuses_an_empty_consent_readme(repo):
    (repo / DAY / "README.md").write_text(" \n", encoding="utf-8")
    with pytest.raises(com.Refuse, match="days/2026-11-05/README.md is missing or empty"):
        com.day(repo, "ana", "x", "2026-11-05")
    assert not (repo / DAY / "ana.md").exists()


def test_day_never_overwrites_without_force(repo):
    com.day(repo, "ana", "first", "2026-11-05")
    with pytest.raises(com.Refuse, match="pass --force"):
        com.day(repo, "ana", "second", "2026-11-05")
    assert "first" in (repo / DAY / "ana.md").read_text(encoding="utf-8")
    com.day(repo, "ana", "second", "2026-11-05", force=True)
    assert "second" in (repo / DAY / "ana.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("bad", ["2026-13-45", "05/11/2026", "20261105"])
def test_day_refuses_a_bad_date(repo, bad):
    with pytest.raises(com.Refuse, match="not a date"):
        com.day(repo, "ana", "x", bad)


def test_day_refuses_empty_text(repo):
    with pytest.raises(com.Refuse, match="nothing to write"):
        com.day(repo, "ana", "  \n", "2026-11-05")


def test_day_defaults_to_today_in_melbourne(repo, monkeypatch):
    monkeypatch.setattr(com, "today", lambda: dt.date(2026, 11, 5))
    assert com.day(repo, "ben", "x") == "days/2026-11-05/ben.md written"


def test_today_is_melbourne_or_the_machine_date_without_tz_data(monkeypatch, capsys):
    assert isinstance(com.today(), dt.date)

    def no_tz(key):
        raise com.ZoneInfoNotFoundError(key)

    monkeypatch.setattr(com, "ZoneInfo", no_tz)
    assert com.today() == dt.date.today()
    assert capsys.readouterr().err == "community: no tz data; using the machine's date\n"


# ---------------------------------------------------------------- network and knows

MAP = """# network: 3 members, 2 links, names only

```mermaid
graph LR
  ana["ana"]
  ben["ben"]
  jo["jo"]
  ana ---|"Jo (designer)"| ben
  ben --- jo
```

| member | knows | shared names |
|---|---|---|
| [ana](../people/ana/) |  | Jo (designer) with [ben](../people/ben/) |
| [ben](../people/ben/) | [jo](../people/jo/) | Jo (designer) with [ana](../people/ana/) |
| [jo](../people/jo/) | [ben](../people/ben/) |  |
"""


def test_network_reads_without_creating_knows_md_and_says_there_is_no_map(repo):
    out = com.network(repo, "ana")
    assert not (repo / "people" / "ana" / "knows.md").exists(), "a read command writes nothing"
    assert out == "# knows: ana\n\n(nobody yet)\n\nno network/MAP.md yet: run connections.py"


def test_network_prints_the_map_lines_that_render_me_not_an_outside_jo(repo):
    (repo / "people" / "jo").mkdir()
    (repo / "network").mkdir()
    (repo / "network" / "MAP.md").write_text(MAP, encoding="utf-8")
    com.knows(repo, "jo", "ben")
    out = com.network(repo, "jo")
    assert out.startswith("# knows: jo\n") and "- ben\n" in out
    assert out.split("network/MAP.md:\n")[1] == (
        '  jo["jo"]\n  ben --- jo\n'
        "| [ben](../people/ben/) | [jo](../people/jo/) | Jo (designer) with [ana](../people/ana/) |\n"
        "| [jo](../people/jo/) | [ben](../people/ben/) |  |")
    assert com.network(repo, "ana").split("network/MAP.md:\n")[1].splitlines() == [
        '  ana["ana"]', '  ana ---|"Jo (designer)"| ben',
        "| [ana](../people/ana/) |  | Jo (designer) with [ben](../people/ben/) |",
        "| [ben](../people/ben/) | [jo](../people/jo/) | Jo (designer) with [ana](../people/ana/) |"]
    assert com.network(repo, "cal").endswith("nothing mentions cal yet")


def test_knows_adds_a_member_once(repo):
    assert com.knows(repo, "ana", "Ben") == "people/ana/knows.md: - ben"
    assert com.knows(repo, "ana", "ben") == "ana already knows ben"
    assert com.names_in(repo / "people" / "ana" / "knows.md") == ["ben"]
    assert not (repo / "people" / "ben" / "knows.md").exists(), "never another member's folder"


def test_knows_sees_a_hand_written_link_or_capital_as_the_same_member(repo):
    path = repo / "people" / "ana" / "knows.md"
    path.write_text("# knows: ana\n\n- [Ben](../ben/)\n", encoding="utf-8")
    assert com.knows(repo, "ana", "ben") == "ana already knows ben"
    assert path.read_text(encoding="utf-8") == "# knows: ana\n\n- [Ben](../ben/)\n"


@pytest.mark.parametrize("bad", ["zed", "Sam (founder)", "../ben"])
def test_knows_refuses_anyone_who_is_not_a_member(repo, bad):
    with pytest.raises(com.Refuse, match="not a member"):
        com.knows(repo, "ana", bad)
    assert not (repo / "people" / "ana" / "knows.md").exists()


def test_knows_refuses_yourself(repo):
    with pytest.raises(com.Refuse, match="that is you"):
        com.knows(repo, "ana", "Ana")


# ---------------------------------------------------------------- main

def run(repo: Path, *args: str) -> int:
    return com.main([*args, "--root", str(repo)])


def test_main_runs_every_command(repo, capsys, monkeypatch):
    assert run(repo, "whats-on") == 0
    assert "agentic-ai-melbourne" in capsys.readouterr().out
    assert run(repo, "going", "Agentic AI Melbourne", "--as", "ana", "--note", "demo") == 0
    assert capsys.readouterr().out == "going/agentic-ai-melbourne/ana.md: demo\n"
    assert run(repo, "whos-going") == 0
    assert capsys.readouterr().out == "agentic-ai-melbourne: ana (demo)\n"
    assert run(repo, "knows", "ben", "--as", "ana") == 0
    assert run(repo, "network", "--as", "ana") == 0
    assert "- ben" in capsys.readouterr().out
    src = repo / "dump.txt"
    src.write_text("learned a thing\n", encoding="utf-8")
    assert run(repo, "day", "--as", "ana", "--date", "2026-11-05", "--from", str(src)) == 0
    assert "learned a thing" in (repo / DAY / "ana.md").read_text(encoding="utf-8")
    monkeypatch.setattr(com.sys, "stdin", io.StringIO("from stdin\n"))
    assert run(repo, "day", "--as", "ben", "--date", "2026-11-05") == 0
    assert "from stdin" in (repo / DAY / "ben.md").read_text(encoding="utf-8")


def test_main_reports_a_refusal_on_stderr_with_exit_2(repo, capsys, monkeypatch):
    assert run(repo, "knows", "zed", "--as", "ana") == 2
    assert "community: not a member" in capsys.readouterr().err
    no_git(monkeypatch)
    assert run(repo, "going", "x") == 2
    assert "who are you" in capsys.readouterr().err
    assert run(repo, "day", "--as", "ana", "--date", "2026-11-05", "--from", str(repo / "missing.txt")) == 2
    assert "missing.txt" in capsys.readouterr().err
