#!/usr/bin/env python3
"""check_visitor_pr.py: the CI check of a pull request's going/ and people/ files.

A visitor says "I'm going" through GitHub's prefilled new-file link, which writes going/<slug>/<login>.md directly
and skips community.py's refusals. This check holds every pull request to them, over the two commits only:
  rule 1  a PR whose author is not the repository owner changes only going/<slug>/<author>.md and files under
          people/<author>/; any other path fails, a deletion or a rename of another member's file included.
  rule 2  every added or changed file under going/ or people/ (any author) is a regular file (git mode 100644),
          named as going/ and people/ allow (going/<slug>/<member>.md; people/<member>/ README.md, knows.md,
          network.md, rooms.md; people/members.json), at most 2 KB, UTF-8, with no line private() refuses (an
          email address or a phone number, after NFKC); a going/ file holds no http(s) link besides the board's
          own quoted row.
  rule 3  going/<slug>/<member>.md: the slug is [a-z0-9-]+ and on the head's board (the newest events/<week>.md,
          read as community.py reads it); the first line is '# <member> is going: <slug>', the next the board's
          row quoted as community.py writes it, then at most one note line of at most 120 characters.
Every finding is one 'FAIL  rule N  <path>: <why>' line and a count; exit 1 on any, else one PASS line and exit 0.
Reads the commits through git only (no checkout of the PR is read or run). Python 3.11+, standard library only.

Run: python3 scripts/check_visitor_pr.py --base <sha> --head <sha> --author <login> --owner <login> [--repo <dir>]
     [--fetched FETCH_HEAD]  (CI: the PR fetched as data must be the event's head, or the check fails)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata

MAX_BYTES = 2048
NOTE_CAP = 120
QUOTED = ("when", "room", "where", "link")  # community.py's QUOTED: the board columns a going file quotes
LOGIN_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,38}")  # a GitHub login, lower-cased; the page lower-cases it too
SLUG_RE = re.compile(r"[a-z0-9-]+")
LINK_RE = re.compile(r"https?://", re.I)
# Pages serves the tree as it is, so a merged .html, .svg or .js would run script on the club's origin: going/ and
# people/ hold only these names, from anyone (people/_template/ and the members' folders use the same four).
MEMBER_FILES = ("README.md", "knows.md", "network.md", "rooms.md")
# community.py's private(): an email, or eight digits with whitespace, dots, brackets, + or - between, once whole
# ISO dates and clock times are masked; plus the page's copy (up to three of any non-alphanumeric between digits).
# Both run after NFKC, so a fullwidth @ or digit is the plain one. A line either copy refuses, this check refuses.
EMAIL_RE = re.compile(r"[^\s@]+@[^\s@]+\.[a-z]{2,}", re.I)
SAFE_RE = re.compile(r"(?<![\d-])\d{4}-\d{2}-\d{2}(?![\d-])|(?<![\d:])\d{1,2}:\d{2}(?![\d:])")
PHONE_RES = (re.compile(r"(?:\d[\s().+-]*){8,}"), re.compile(r"(?:\d[^A-Za-z0-9]{0,3}){8,}"))


class GitError(Exception):
    """A git command failed; the check cannot see the change, so it fails closed."""


def private(line: str) -> bool:
    """True when one line holds an email address or a phone number, after NFKC and whitespace folding."""
    line = " ".join(unicodedata.normalize("NFKC", line).split())
    masked = SAFE_RE.sub(" ", line)
    return bool(EMAIL_RE.search(line) or any(p.search(masked) for p in PHONE_RES))


def git(repo: str, *args: str) -> bytes:
    out = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    if out.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {out.stderr.decode('utf-8', 'replace').strip()[:200]}")
    return out.stdout


def changes(repo: str, base: str, head: str) -> list[tuple[str, str, str, str]]:
    """(status, new mode, new blob, path) for every path the PR changes; a rename is a deletion plus an addition."""
    raw = git(repo, "diff", "--raw", "-z", "--no-renames", "--no-abbrev", f"{base}...{head}").decode("utf-8", "replace")
    parts = raw.split("\0")
    out = []
    for meta, path in zip(parts[0::2], parts[1::2]):
        _old_mode, new_mode, _old_sha, new_sha, status = meta.lstrip(":").split()
        out.append((status[0], new_mode, new_sha, path))
    return out


def board(repo: str, head: str) -> tuple[str, dict[str, dict[str, str]]]:
    """The head's newest events/<week>.md by name and its rows by slug, as community.py's board_rows reads them."""
    names = sorted(n for n in git(repo, "ls-tree", "-z", "--name-only", head, "events/").decode().split("\0")
                   if n.endswith(".md") and n.rsplit("/", 1)[-1][:-3].lower() != "readme")
    if not names:
        return "", {}
    cols: list[str] = []
    rows = {}
    for line in git(repo, "cat-file", "blob", f"{head}:{names[-1]}").decode("utf-8", "replace").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        row = [c.strip() for c in line.strip().strip("|").split("|")]
        if "slug" in [c.lower() for c in row]:
            cols = [c.lower() for c in row]
        elif cols and len(row) == len(cols) and not all(set(c) <= set("-: ") for c in row):
            r = dict(zip(cols, row))
            rows.setdefault(r["slug"], r)
    return names[-1], rows


def allowed_name(path: str) -> bool:
    """Rule 2's file names: going/README.md, going/<slug>/<member>.md, people/members.json (generated) and
    people/<member>/ README.md, knows.md, network.md or rooms.md; nothing else, under going/ or people/."""
    p = path.split("/")
    if p[0] == "going":
        return path == "going/README.md" or (len(p) == 3 and p[2].endswith(".md") and len(p[2]) > 3)
    return path == "people/members.json" or (len(p) == 3 and p[0] == "people" and p[2] in MEMBER_FILES)


def owned(path: str, author: str) -> bool:
    """Rule 1: a visitor's own paths, going/<slug>/<author>.md and anything under people/<author>/."""
    p = path.split("/")
    return (len(p) == 3 and p[0] == "going" and p[2] == f"{author}.md") or path.startswith(f"people/{author}/")


def going_shape(path: str, text: str, board_name: str, rows: dict) -> tuple[list[str], set[str]]:
    """Rule 3 for one going/<slug>/<member>.md: the findings, and the lines the board itself supplies."""
    _, s, name = path.split("/")
    member = name[:-3]
    if not SLUG_RE.fullmatch(s):
        return [f"{s!r} is not a slug ([a-z0-9-]+)"], set()
    if not LOGIN_RE.fullmatch(member):
        return [f"{member!r} is not a member name (lower-case letters, digits, hyphens)"], set()
    if not board_name:
        return ["no board (events/<week>.md) on the PR's head"], set()
    if s not in rows:
        return [f"slug {s} is not on the board ({board_name})"], set()
    heading = f"# {member} is going: {s}"
    quoted = "> " + " | ".join(f"{k}: {rows[s][k]}" for k in QUOTED if rows[s].get(k))
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    problems = []
    if not lines or lines[0] != heading:
        problems.append(f"first line must be '{heading}'")
    if len(lines) < 2 or lines[1] != quoted:
        problems.append(f"second line must be the board's row quoted: '{quoted}'")
    if len(lines) > 3:
        problems.append("the note is one line")
    elif len(lines) == 3 and len(lines[2]) > NOTE_CAP:
        problems.append(f"the note is {len(lines[2])} characters; at most {NOTE_CAP}")
    return problems, {heading, quoted}


def check(repo: str, base: str, head: str, author: str, owner: str) -> list[str]:
    """Every finding as 'rule N  <path>: <why>'; empty when the PR passes."""
    visitor = author != owner
    board_name, rows = board(repo, head)
    found = []
    for status, mode, sha, path in changes(repo, base, head):
        if visitor and not owned(path, author):
            what = "deleted" if status == "D" else "changed"
            found.append(f"rule 1  {path}: {what} by {author}, who may change only going/<slug>/{author}.md "
                         f"and people/{author}/")
        if status == "D" or not path.lower().startswith(("going/", "people/")):
            continue
        if mode != "100644":
            found.append(f"rule 2  {path}: git mode {mode}; only a regular file (100644)")
            continue
        if not allowed_name(path):
            what = ("going/ holds only going/<slug>/<member>.md" if path.lower().startswith("going/") else
                    f"people/<member>/ holds only {', '.join(MEMBER_FILES)}")
            found.append(f"rule 2  {path}: {what} (Pages would serve any other file as it is)")
            continue
        size = int(git(repo, "cat-file", "-s", sha))
        if size > MAX_BYTES:
            found.append(f"rule 2  {path}: {size} bytes; at most {MAX_BYTES}")
            continue
        try:
            text = git(repo, "cat-file", "blob", sha).decode("utf-8")
        except UnicodeDecodeError:
            found.append(f"rule 2  {path}: not UTF-8")
            continue
        safe: set[str] = set()
        parts = path.split("/")
        if len(parts) == 3 and parts[0] == "going" and path.endswith(".md") and parts[2].lower() != "readme.md":
            problems, safe = going_shape(path, text, board_name, rows)
            found += [f"rule 3  {path}: {p}" for p in problems]
        elif len(parts) >= 3 and parts[0] == "people":
            safe = {f"# {parts[1]}"}  # the join file's heading is the login, which may hold digits
        for n, line in enumerate(text.splitlines(), 1):
            if line.rstrip() in safe:
                continue  # the board's row and the login, never the member's own words
            if private(line):
                found.append(f"rule 2  {path}:{n}: looks like an email address or a phone number")
            if path.lower().startswith("going/") and LINK_RE.search(unicodedata.normalize("NFKC", line)):
                found.append(f"rule 2  {path}:{n}: a link; a going file links only through the board's row")
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--author", required=True, help="the PR author's login (github.event.pull_request.user.login)")
    ap.add_argument("--owner", required=True, help="the repository owner's login")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--fetched", help="the ref the PR was fetched to (FETCH_HEAD); it must resolve to --head")
    a = ap.parse_args(argv)
    author, owner = a.author.strip().lower(), a.owner.strip().lower()
    bad = [f"input  --{k}: {v!r} is not a GitHub login" for k, v in (("author", author), ("owner", owner))
           if not LOGIN_RE.fullmatch(v)]
    bad += [f"input  --{k}: {v!r} is not a commit" for k, v in (("base", a.base), ("head", a.head),
                                                                ("fetched", a.fetched or "FETCH_HEAD"))
            if not v or v.startswith("-")]  # never an option to git
    if not bad:
        try:
            if a.fetched:
                got, want = (git(a.repo, "rev-parse", "--verify", "--end-of-options", f"{r}^{{commit}}").decode().strip()
                             for r in (a.fetched, a.head))
                if got != want:
                    raise GitError(f"the fetched head {got} is not the event's head {want}; refusing to judge it")
            bad = check(a.repo, a.base, a.head, author, owner)
        except (GitError, ValueError) as exc:
            bad = [f"git  {exc}"]
    for f in bad:
        print(f"FAIL  {f}")
    if bad:
        print(f"check_visitor_pr: {len(bad)} failure(s)", file=sys.stderr)
        return 1
    print(f"PASS  check_visitor_pr: {author} ({'visitor' if author != owner else 'owner'}), {a.base}...{a.head}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
