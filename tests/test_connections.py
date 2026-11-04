"""Tests for the community skill's connections.py: who knows whom, names only, as network/MAP.md.

Run: ./test, or python -m pytest tests/test_connections.py. The fixture members under
tests/fixtures/connections/people/ are placeholders (Ana, Ben, Cal) with made-up outside names.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PEOPLE = ROOT / "tests" / "fixtures" / "connections" / "people"


def load(name: str):
    path = ROOT / ".agents" / "skills" / "community" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


connections = load("connections")


# ---------------------------------------------------------------- reading

def test_members_are_the_folders_sorted_without_the_template(tmp_path):
    assert connections.members(PEOPLE) == ["ana", "ben", "cal"], "_template and README.md are not members"
    assert connections.members(tmp_path / "nobody") == []


def test_members_follow_the_one_name_rule_shared_with_the_community_script(tmp_path):
    people = tmp_path / "people"
    for d in ("ana", "b2-c", ".hidden", "README", "Zed Q", "Alex", "_template"):
        (people / d).mkdir(parents=True)
    (people / "jo").write_text("a file, not a folder\n", encoding="utf-8")
    assert connections.members(people) == ["ana", "b2-c"]
    assert connections.NAME_RE.pattern == load("community").NAME_RE.pattern


def test_knows_lines_are_cleaned_and_a_draft_is_skipped():
    assert connections.knows(PEOPLE / "ana" / "knows.md") == ["ben", "zed"], "the ? line is a draft"
    assert connections.knows(PEOPLE / "cal" / "knows.md") == ["ben"], "a link and a capital are the same name"
    assert connections.knows(PEOPLE / "ben" / "knows.md") == [], "no file, nobody"


def test_outside_people_skip_drafts_and_members():
    pod = {"ana", "ben", "cal"}
    assert connections.outside(PEOPLE / "ana" / "network.md", pod) == ["Sam (founder)", "Jo (designer)"], \
        "? Priya is a draft; Ben (robotics) is the member Ben"
    assert connections.outside(PEOPLE / "ben" / "network.md", pod) == ["sam (Founder)", "Priya (PhD)"]
    assert connections.outside(PEOPLE / "ben" / "knows.md", pod) == [], "no file, nobody"


# ---------------------------------------------------------------- links

def test_links_knows_either_way_and_shared_outside_names():
    known, shared = connections.links(PEOPLE, ["ana", "ben", "cal"])
    assert known == {("ana", "ben"), ("ben", "cal")}, "ana lists ben (one way); cal lists Ben; ? cal is a draft"
    assert shared == {("ana", "ben"): {"Sam (founder)"}, ("ana", "cal"): {"Jo (designer)"}}, \
        "sam (Founder) is Sam (founder); Priya is a draft for ana; Ben (robotics) is a member, never a shared name"


# ---------------------------------------------------------------- the page

def test_render_draws_the_mermaid_graph_and_the_table():
    page = connections.render(["ana", "ben", "cal"], *connections.links(PEOPLE, ["ana", "ben", "cal"]))
    assert page.startswith("# network: 3 members, 3 links, names only\n\n```mermaid\ngraph LR\n")
    assert '  ana["ana"]\n  ben["ben"]\n  cal["cal"]\n' in page
    assert '  ana ---|"Sam (founder)"| ben\n  ana ---|"Jo (designer)"| cal\n  ben --- cal\n```\n' in page
    assert "| [ana](../people/ana/) | [ben](../people/ben/) | Jo (designer) with [cal](../people/cal/); " \
           "Sam (founder) with [ben](../people/ben/) |" in page
    assert "| [ben](../people/ben/) | [ana](../people/ana/); [cal](../people/cal/) | Sam (founder) with [ana](../people/ana/) |" in page
    assert "| [cal](../people/cal/) | [ben](../people/ben/) | Jo (designer) with [ana](../people/ana/) |" in page


def test_render_carries_names_only():
    page = connections.render(["ana", "ben", "cal"], *connections.links(PEOPLE, ["ana", "ben", "cal"]))
    for private in ("Couch Conversations", "Clay Club", "2026-11-06", "2026-11-08", "Priya", "zed"):
        assert private not in page


def test_node_ids_are_mermaid_safe():
    assert connections.node("jo-ann.b") == "jo_ann_b"


# ---------------------------------------------------------------- main

def test_main_writes_the_map_and_the_member_list_and_prints_the_summary(tmp_path, capsys):
    out, members = tmp_path / "MAP.md", tmp_path / "members.json"
    rc = connections.main(["--people", str(PEOPLE), "--out", str(out), "--members", str(members)])
    assert rc == 0
    assert capsys.readouterr().out == f"connections: 3 members, 3 links, {out}\n"
    assert json.loads(members.read_text(encoding="utf-8")) == ["ana", "ben", "cal"]
    assert out.read_text(encoding="utf-8").startswith("# network: 3 members, 3 links")


def test_main_defaults_are_people_members_json_and_network_map(tmp_path, monkeypatch, capsys):
    shutil.copytree(PEOPLE, tmp_path / "people")
    monkeypatch.setattr(connections, "ROOT", tmp_path)
    assert connections.main([]) == 0
    assert capsys.readouterr().out == "connections: 3 members, 3 links, network/MAP.md\n"
    assert (tmp_path / "network" / "MAP.md").is_file()
    assert json.loads((tmp_path / "people" / "members.json").read_text(encoding="utf-8")) == ["ana", "ben", "cal"]


def test_main_with_no_members_still_writes_the_files(tmp_path, capsys):
    out, members = tmp_path / "MAP.md", tmp_path / "members.json"
    assert connections.main(["--people", str(tmp_path / "nobody"), "--out", str(out), "--members", str(members)]) == 0
    assert capsys.readouterr().out == f"connections: 0 members, 0 links, {out}\n"
    assert json.loads(members.read_text(encoding="utf-8")) == []
