"""Tests for scripts/check_visitor_pr.py, the CI check of a pull request's going/ and people/ files.

Run: ./test tests scripts/tests, or python -m pytest scripts/tests. Each test builds a real git repository in
tmp_path (a base commit with a board, then a head commit with the pull request's change) and runs the check over
the two commits; placeholder members ana and ben, owner pod-owner; nothing touches the network or a git config.
"""
from __future__ import annotations

import importlib.util
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


chk = load("check_visitor_pr", ROOT / "scripts" / "check_visitor_pr.py")

ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.test", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@example.test", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
SLUG = "agentic-ai-melbourne"
BOARD = f"""# rooms, Wed 4 Nov to Tue 10 Nov 2026

| when | room | where | link | community | slug |
|---|---|---|---|---|---|
| Thu 5 Nov 17:30 | Agentic AI Melbourne | address on the event page | https://example.test/events/317171446 | MLAI | {SLUG} |
| Wed 4 Nov 17:30 | Couch Conversations | Cremorne Digital Hub | https://example.test/couch | ANZ | couch-conversations |
"""
ROW = ("> when: Thu 5 Nov 17:30 | room: Agentic AI Melbourne | where: address on the event page"
       " | link: https://example.test/events/317171446")
OWNER = "pod-owner"


def going(member: str = "ana", slug: str = SLUG, note: str = "first time, keen") -> str:
    """A going file as community.py and the page write it: heading, blank, the quoted row, blank, the note."""
    return f"# {member} is going: {slug}\n\n{ROW}\n" + (f"\n{note}\n" if note else "")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
                          env=ENV).stdout.strip()


def write(repo: Path, path: str, content: str | bytes) -> None:
    p = repo / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """The base: a board, going/README.md, ben's folder and ben's going file, README.md; committed."""
    r = tmp_path / "pod"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    for path, text in {"events/2026-W45.md": BOARD, "events/README.md": "# events\n", "going/README.md": "# going\n",
                       f"going/{SLUG}/ben.md": going("ben"), "people/ben/README.md": "# ben\n",
                       "README.md": "# pod\n"}.items():
        write(r, path, text)
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "base")
    git(r, "tag", "base")
    return r


def head(repo: Path, files: dict[str, str | bytes | None] | None = None) -> str:
    """Commit the pull request's change (None deletes a path) and return its sha."""
    for path, content in (files or {}).items():
        if content is None:
            git(repo, "rm", "-q", path)
        else:
            write(repo, path, content)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", "pr")
    return git(repo, "rev-parse", "HEAD")


def run(repo: Path, capsys, author: str = "ana", owner: str = OWNER, base: str = "base",
        tip: str = "HEAD") -> tuple[int, str]:
    rc = chk.main(["--repo", str(repo), "--base", base, "--head", tip, "--author", author, "--owner", owner])
    out = capsys.readouterr()
    return rc, out.out + out.err


def fails(out: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith("FAIL")]


# ---------------------------------------------------------------- the passing shapes

def test_visitor_going_file_passes_with_one_pass_line(repo, capsys):
    head(repo, {f"going/{SLUG}/ana.md": going()})
    rc, out = run(repo, capsys)
    assert rc == 0
    assert out.strip().splitlines() == [out.strip()]
    assert out.startswith("PASS")


def test_visitor_own_folder_and_going_file_without_note_pass(repo, capsys):
    head(repo, {"people/ana/README.md": "# ana\n\n- who I am: builder, see https://example.test/ana\n",
                f"going/{SLUG}/ana.md": going(note="")})
    assert run(repo, capsys)[0] == 0


def test_visitor_login_case_is_ignored(repo, capsys):
    head(repo, {f"going/{SLUG}/ana.md": going()})
    assert run(repo, capsys, author="Ana", owner="Pod-Owner")[0] == 0


def test_visitor_may_delete_own_going_file(repo, capsys):
    git(repo, "checkout", "-q", "-b", "had")
    head(repo, {f"going/{SLUG}/ana.md": going()})
    git(repo, "tag", "-f", "base")
    head(repo, {f"going/{SLUG}/ana.md": None})
    assert run(repo, capsys)[0] == 0


def test_owner_may_change_anything_outside_going_and_people(repo, capsys):
    head(repo, {"README.md": "# pod, new\n", "scripts/x.py": "print(1)\n", f"going/{SLUG}/ben.md": None})
    assert run(repo, capsys, author="pod-owner")[0] == 0


def test_dates_and_times_are_not_phone_numbers(repo, capsys):
    head(repo, {"people/ana/rooms.md": "| 2026-11-05 | 17:30 | room | 18:00 |\n"})
    assert run(repo, capsys)[0] == 0


# ---------------------------------------------------------------- rule 1: a visitor's PR touches only their own files

@pytest.mark.parametrize("files", [
    {"README.md": "# pod, changed\n"},
    {"scripts/check_visitor_pr.py": "print('PASS')\n"},
    {".github/workflows/x.yml": "on: push\n"},
    {"people/ben/README.md": "# ben, edited by ana\n"},
    {"people/members.json": "[]\n"},
    {"people/ana": "a file, not a folder\n"},
    {f"going/{SLUG}/ben.md": None},
    {f"going/{SLUG}/ben.md": going("ben", note="edited by ana")},
    {f"going/{SLUG}/ana.txt": "x\n"},
    {f"going/{SLUG}/x/ana.md": going()},
    {"going/ana.md": "x\n"},
    {"Going/x/ana.md": going()},
])
def test_rule1_visitor_outside_own_files_fails(repo, capsys, files):
    head(repo, files)
    rc, out = run(repo, capsys)
    assert rc == 1
    path = next(iter(files))
    assert any("rule 1" in ln and path in ln for ln in fails(out)), out


def test_rule1_visitor_going_file_named_for_someone_else_fails(repo, capsys):
    head(repo, {f"going/{SLUG}/cal.md": going("cal")})
    rc, out = run(repo, capsys)
    assert rc == 1
    assert any("rule 1" in ln and f"going/{SLUG}/cal.md" in ln and "going/<slug>/ana.md" in ln for ln in fails(out))


def test_rule1_rename_of_anothers_file_fails(repo, capsys):
    git(repo, "mv", f"going/{SLUG}/ben.md", f"going/{SLUG}/ana.md")
    write(repo, f"going/{SLUG}/ana.md", going())
    head(repo)
    rc, out = run(repo, capsys)
    assert rc == 1
    assert any("rule 1" in ln and f"going/{SLUG}/ben.md" in ln and "deleted" in ln for ln in fails(out)), out


# ---------------------------------------------------------------- rule 2: plain, small, UTF-8, nothing private

def test_rule2_symlink_fails(repo, capsys):
    (repo / "people" / "ana").mkdir(parents=True)
    os.symlink("../ben/README.md", repo / "people" / "ana" / "README.md")
    head(repo)
    rc, out = run(repo, capsys)
    assert rc == 1
    assert any("rule 2" in ln and "people/ana/README.md" in ln and "120000" in ln for ln in fails(out)), out


def test_rule2_submodule_fails(repo, capsys):
    sha = git(repo, "rev-parse", "HEAD")
    git(repo, "update-index", "--add", "--cacheinfo", f"160000,{sha},people/ana/sub")
    git(repo, "commit", "-q", "-m", "pr")
    rc, out = run(repo, capsys)
    assert rc == 1
    assert any("rule 2" in ln and "people/ana/sub" in ln and "160000" in ln for ln in fails(out)), out


def test_rule2_executable_fails(repo, capsys):
    write(repo, "people/ana/README.md", "# ana\n")
    git(repo, "add", "people/ana/README.md")
    git(repo, "update-index", "--chmod=+x", "people/ana/README.md")
    git(repo, "commit", "-q", "-m", "pr")
    rc, out = run(repo, capsys)
    assert rc == 1
    assert any("rule 2" in ln and "100755" in ln for ln in fails(out)), out


def test_rule2_over_2kb_fails_and_2kb_passes(repo, capsys):
    head(repo, {"people/ana/README.md": "# ana\n" + "x" * (2048 - 6)})
    assert run(repo, capsys)[0] == 0
    head(repo, {"people/ana/README.md": "# ana\n" + "x" * (2049 - 6)})
    rc, out = run(repo, capsys)
    assert rc == 1
    assert any("rule 2" in ln and "2049 bytes" in ln for ln in fails(out)), out


def test_rule2_not_utf8_fails(repo, capsys):
    head(repo, {"people/ana/README.md": b"# ana\n\xff\xfe\n"})
    rc, out = run(repo, capsys)
    assert rc == 1
    assert any("rule 2" in ln and "UTF-8" in ln for ln in fails(out)), out


@pytest.mark.parametrize("line", [
    "mail me: ana@example.test",
    "mail me: ana\uff20example.test",  # fullwidth @
    "mail me: ana\ufe6bexample.test",  # small commercial at
    "call +61 400 000 000",
    "call (03) 9000-0000",
    "call 0400.000.000",
    "call 0400/000/000",  # the page's wider separators
    "call \uff10\uff14\uff10\uff10 \uff10\uff10\uff10 \uff10\uff10\uff10",  # fullwidth digits
    "call 0400 000 000 on 2026-11-05",
])
def test_rule2_email_or_phone_fails_in_people_and_going(repo, capsys, line):
    head(repo, {"people/ana/README.md": f"# ana\n\n- who I am: {line}\n"})
    rc, out = run(repo, capsys)
    assert rc == 1
    assert any("rule 2" in ln and "people/ana/README.md:3" in ln for ln in fails(out)), out
    head(repo, {"people/ana/README.md": "# ana\n", f"going/{SLUG}/ana.md": going(note=line)})
    rc, out = run(repo, capsys)
    assert rc == 1
    assert any("rule 2" in ln and f"going/{SLUG}/ana.md:5" in ln for ln in fails(out)), out


def test_rule2_login_with_digits_in_its_own_headings_passes(repo, capsys):
    head(repo, {"people/ana12345678/README.md": "# ana12345678\n",
                f"going/{SLUG}/ana12345678.md": going("ana12345678")})
    assert run(repo, capsys, author="ana12345678")[0] == 0
    head(repo, {"people/ana12345678/README.md": "# ana12345678\n\nana12345678\n"})
    rc, out = run(repo, capsys, author="ana12345678")
    assert rc == 1 and any("people/ana12345678/README.md:3" in ln for ln in fails(out)), out


def test_rule2_applies_to_the_owner_too(repo, capsys):
    head(repo, {"people/pod-owner/README.md": "# pod-owner\n\nana@example.test\n"})
    rc, out = run(repo, capsys, author="pod-owner")
    assert rc == 1
    assert any("rule 2" in ln for ln in fails(out)), out


def test_rule2_link_in_going_note_fails(repo, capsys):
    head(repo, {f"going/{SLUG}/ana.md": going(note="see HTTPS://example.test/me")})
    rc, out = run(repo, capsys)
    assert rc == 1
    assert any("rule 2" in ln and "link" in ln for ln in fails(out)), out


def test_rule2_private_covers_community_private(repo):
    """Every line community.py's private() refuses, this check refuses too (one rule, two copies)."""
    com = load("community", ROOT / ".agents" / "skills" / "community" / "community.py")
    lines = ["ana@example.test", "a.b@c.co", "+61 400 000 000", "(03) 9000 0000", "0400-000-000",
             "12345678", "1 2 3 4 5 6 7 8", "on 2026-11-05 at 17:30", "room 12", "2026-11-05 17:30 18:00"]
    for ln in lines:
        assert chk.private(ln) or not com.private(ln), ln


# ---------------------------------------------------------------- rule 3: the going file's slug and shape

@pytest.mark.parametrize("slug, why", [
    ("Agentic_AI", "not a slug"),
    ("not-on-the-board", "not on the board"),
])
def test_rule3_slug_fails(repo, capsys, slug, why):
    head(repo, {f"going/{slug}/ana.md": going(slug=slug)})
    rc, out = run(repo, capsys)
    assert rc == 1
    assert any("rule 3" in ln and f"going/{slug}/ana.md" in ln and why in ln for ln in fails(out)), out


@pytest.mark.parametrize("text, why", [
    ("", "first line"),
    (f"# ben is going: {SLUG}\n\n{ROW}\n", "first line"),
    (f"# ana is going to {SLUG}\n\n{ROW}\n", "first line"),
    (f"# ana is going: {SLUG}\n", "quoted"),
    (f"# ana is going: {SLUG}\n\nkeen\n", "quoted"),
    (f"# ana is going: {SLUG}\n\n{ROW.replace('example.test/events', 'example.test/evil')}\n", "quoted"),
    (going(note="x" * 121), "120"),
    (going(note="one\ntwo"), "one line"),
])
def test_rule3_shape_fails(repo, capsys, text, why):
    head(repo, {f"going/{SLUG}/ana.md": text})
    rc, out = run(repo, capsys)
    assert rc == 1
    assert any("rule 3" in ln and f"going/{SLUG}/ana.md" in ln and why in ln for ln in fails(out)), out


def test_rule3_note_of_120_passes(repo, capsys):
    head(repo, {f"going/{SLUG}/ana.md": going(note="x" * 120)})
    assert run(repo, capsys)[0] == 0


def test_rule3_reads_the_newest_board_on_head(repo, capsys):
    newer = BOARD.replace(SLUG, "next-week-room")
    head(repo, {"events/2026-W46.md": newer})  # as the owner, so the board may change
    git(repo, "tag", "-f", "base")
    head(repo, {f"going/{SLUG}/ana.md": going()})
    rc, out = run(repo, capsys)
    assert rc == 1
    assert any("rule 3" in ln and "events/2026-W46.md" in ln for ln in fails(out)), out


def test_rule3_no_board_fails(repo, capsys):
    head(repo, {"events/2026-W45.md": None})
    git(repo, "tag", "-f", "base")
    head(repo, {f"going/{SLUG}/ana.md": going()})
    rc, out = run(repo, capsys)
    assert rc == 1
    assert any("rule 3" in ln and "no board" in ln for ln in fails(out)), out


def test_rule3_owner_going_file_needs_a_member_name(repo, capsys):
    head(repo, {f"going/{SLUG}/Not_A_Name.md": going("Not_A_Name")})
    rc, out = run(repo, capsys, author="pod-owner")
    assert rc == 1
    assert any("rule 3" in ln and "member name" in ln for ln in fails(out)), out


# ---------------------------------------------------------------- rule 4: loud, fail closed

def test_rule4_every_failure_is_named_and_counted(repo, capsys):
    head(repo, {"README.md": "# x\n", "people/ana/README.md": "ana@example.test\n"})
    rc, out = run(repo, capsys)
    assert rc == 1
    assert len(fails(out)) == 2
    assert re.search(r"^check_visitor_pr: 2 failure\(s\)", out, re.M), out


@pytest.mark.parametrize("kw", [{"author": ""}, {"owner": " "}, {"author": "ana;rm"}, {"base": "no-such-commit"}])
def test_rule4_bad_input_fails_closed(repo, capsys, kw):
    head(repo, {f"going/{SLUG}/ana.md": going()})
    rc, out = run(repo, capsys, **kw)
    assert rc == 1
    assert fails(out), out


@pytest.mark.parametrize("arg", ["--base=--output=x", "--head=--output=x"])
def test_rule4_commit_that_is_a_git_option_fails_closed(repo, capsys, arg):
    argv = ["--repo", str(repo), "--base", "base", "--head", "HEAD", "--author", "ana", "--owner", OWNER, arg]
    assert chk.main(argv) == 1
    assert "is not a commit" in capsys.readouterr().out
    assert not (repo / "x").exists() and not Path("x").exists()


def test_rule4_empty_pr_passes(repo, capsys):
    head(repo)
    rc, out = run(repo, capsys)
    assert rc == 0 and out.startswith("PASS")


# ---------------------------------------------------------------- the workflow: pull_request, read-only, no injection

def test_workflow_runs_the_check_safely():
    text = (ROOT / ".github" / "workflows" / "harness-gates.yml").read_text(encoding="utf-8")
    wf = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))  # code, not comments
    assert "pull_request_target" not in wf
    assert "secrets." not in wf
    job = wf[wf.index("  visitor-pr:"):]
    assert re.search(r"^    permissions:\n      contents: read$", job, re.M)
    assert "check_visitor_pr.py" in job
    for ln in wf.splitlines():  # an expression from the event never lands in a shell line, only in env: or if:
        if "${{ github.event" in ln:
            assert re.match(r"^\s+([A-Z_]+|if):\s", ln), ln
