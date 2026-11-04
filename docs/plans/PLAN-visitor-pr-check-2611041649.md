# Plan (feature, tooling): visitor-pr-check, the CI check of a pull request's going/ and people/ files
Status: done 2026-11-04 16:49. Departures: (1) the brief served as the plan and this file was written after the
work, from the brief, the code and the session log `docs/sessions/session_2611041638.md`; (2) the residual below
stays open: `pull_request` runs the PR's own version of the workflow, so a PR that edits
`.github/workflows/harness-gates.yml` can rewrite or skip the `visitor-pr` job, and running the base branch's copy
of the checker does not help then; a required status check does not close it either (a rewritten job of the same
name still reports). Until something closes it, fork-run approval for first-time contributors and the reviewer's
read of any workflow edit cover it, and the hand checklist's "nothing else changed" stays binding even after the
check is required.

Why: a visitor says "I'm going" through GitHub's prefilled new-file link, which writes `going/<slug>/<login>.md`
directly and skips `community.py`'s `private()` refusal. Until a check is a required status, a person merges each
visitor PR by a four-line checklist: one file at `going/<slug>/<pr-author>.md`; the slug is on the board; no email,
phone, link or symlink; nothing else changed.
Observed: `harness_lint.py` classifies `scripts/`, `.githooks/` and `.github/` as tooling and anything outside its
not-source list (so `tests/`) as product, so the tests live in `scripts/tests/` and the change stays one kind;
`prepush_check.py` skips `scripts/`, `.github/` and `.md`. `community.py`'s `private()` has no NFKC; the page's copy
adds NFKC and wider phone separators. The board's own links can hold long digit runs (an event id).
Assumed: the page writes the going file exactly as `community.py going` does (confirmed in round 2 by a test).

Acceptance criteria: `scripts/check_visitor_pr.py --base --head --author --owner`, standard library only, reading the
two commits through git only:
1. a PR whose author is not the repository owner (logins compared lower-cased) changes only
   `going/<slug>/<author>.md` and files under `people/<author>/`; anything else fails, a deletion or a rename of
   another member's file included;
2. every added or changed file under `going/` or `people/`, from anyone, is a regular file (git mode 100644; a
   symlink, an executable or a submodule fails), at most 2 KB, UTF-8, with no line `private()` refuses (the
   `community.py` rule and the page's, after NFKC: emails including a fullwidth @, phones including separators and
   fullwidth digits); a going file holds no http(s) link besides the board's own quoted row;
3. `going/<slug>/<member>.md` has a `[a-z0-9-]+` slug on the head's newest `events/<week>.md`, first line
   `# <member> is going: <slug>`, then the board's row quoted as `community.py`'s QUOTED join, then at most one note
   line of at most 120 characters (`going/README.md`);
4. one `FAIL  rule N  <path>: <why>` line per finding and a count, exit 1; else one PASS line, exit 0; bad input and
   a git failure fail closed.
The `visitor-pr` job in `harness-gates.yml`: `pull_request` only (never `pull_request_target`),
`permissions: contents: read`, `persist-credentials: false`, no secrets, the event's values through `env:` only,
`fetch-depth: 0`, the base branch's copy of the checker run with `python -I`. `./test tests scripts/tests` green;
at least 90% of added lines covered; lint 0 errors.
Surface: scripts/check_visitor_pr.py; scripts/tests/test_check_visitor_pr.py; .github/workflows/harness-gates.yml;
docs/ARCHITECTURE.md; docs/sessions/session_2611041638.md; this plan; NEXT-STEPS.md.
Design: one script, one function per rule's input (`changes` from `git diff --raw -z --no-renames base...head`,
`board` from `git ls-tree` and `git cat-file` on head, `going_shape` for rule 3), `check` walks the changes;
`private()` mirrored, not imported, so no repository code a PR could change is executed. No dependency.
Test plan: `scripts/tests/test_check_visitor_pr.py`, a real git repository per test in tmp_path: the passing shapes;
each rule's failures (parametrized); `private()` covers `community.py`'s; the workflow's safety (no
`pull_request_target`, no secrets, `contents: read`, event values only in `env:` or `if:`); round 2, the page's file
for every row of the real board, lower-case and mixed-case author. Witnessed red: a stub first, then one mutation per
behaviour (the session log lists them).
Architecture map delta: yes (a layout row and a boundary invariant). ADR: no (a CI check, recorded in the map).
Cross-repo impact: the page's going link must write the shape of rule 3.
Open questions: none.
BACKLOG: the residual in departure (2).
