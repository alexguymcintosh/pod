# Plan (feature, tooling): visitor-pr-check, the CI check of a pull request's going/ and people/ files
Status: done 2026-11-04 16:54. Departures: (1) the brief served as the plan and this file was written after the
work, from the brief, the code and the session log `docs/sessions/session_2611041638.md`. (2) The trigger changed
in review: the first build ran on `pull_request`, which runs the PR's own version of the workflow, so a PR that
edited it could rewrite or skip the job. The security review ruled `pull_request_target` with the PR read as data
only, and the job moved to its own `.github/workflows/visitor-pr.yml`; `.github/CODEOWNERS` gives `/.github/` to the
owner. (3) The file-type rule (W1) was added in review: Pages serves the tree as it is, so only named `.md` files may
sit under `going/` and `people/`. (4) The live proof (a fork PR whose run shows the base's workflow FAIL) can only
run after merge: `pull_request_target` runs the base branch's workflow, and the base has no `visitor-pr.yml` until
this merges. Until the check is a required status, the four-line hand checklist stays binding.

Why: a visitor says "I'm going" through GitHub's prefilled new-file link, which writes `going/<slug>/<login>.md`
directly and skips `community.py`'s `private()` refusal. Until a check is a required status, a person merges each
visitor PR by a four-line checklist: one file at `going/<slug>/<pr-author>.md`; the slug is on the board; no email,
phone, link or symlink; nothing else changed.
Observed: `harness_lint.py` classifies `scripts/`, `.githooks/` and `.github/` as tooling and anything outside its
not-source list (so `tests/`) as product, so the tests live in `scripts/tests/` and the change stays one kind;
`prepush_check.py` skips `scripts/`, `.github/` and `.md`. `community.py`'s `private()` has no NFKC; the page's copy
adds NFKC and wider phone separators. The board's own links can hold long digit runs (an event id). The members'
folders and `people/_template/` hold only `README.md`, `knows.md`, `network.md` and `rooms.md`; `people/` also holds
the generated `people/members.json`.
Assumed: the page writes the going file exactly as `community.py going` does (confirmed in round 2 by a test).

Acceptance criteria: `scripts/check_visitor_pr.py --base --head --author --owner [--fetched]`, standard library only,
reading the commits through git only:
1. a PR whose author is not the repository owner (logins compared lower-cased) changes only
   `going/<slug>/<author>.md` and files under `people/<author>/`; anything else fails, `.github/` included, and a
   deletion or a rename of another member's file;
2. every added or changed file under `going/` or `people/`, from anyone, the owner included, is named as they allow
   (`going/README.md`, `going/<slug>/<member>.md`, `people/members.json`, `people/<member>/` `README.md`,
   `knows.md`, `network.md` or `rooms.md`), a regular file (git mode 100644; a symlink, an executable or a submodule
   fails), at most 2 KB, UTF-8, with no line `private()` refuses (the `community.py` rule and the page's, after NFKC:
   emails including a fullwidth @, phones including separators and fullwidth digits); a going file holds no http(s)
   link besides the board's own quoted row;
3. `going/<slug>/<member>.md` has a `[a-z0-9-]+` slug on the head's newest `events/<week>.md`, first line
   `# <member> is going: <slug>`, then the board's row quoted as `community.py`'s QUOTED join, then at most one note
   line of at most 120 characters (`going/README.md`);
4. one `FAIL  rule N  <path>: <why>` line per finding and a count, exit 1; else one PASS line, exit 0; bad input, a
   git failure and a fetched head that is not the event's head fail closed.
The job, `.github/workflows/visitor-pr.yml`, job `visitor-pr`: `on: pull_request_target` only, types opened,
synchronize, reopened; `permissions: contents: read`; no secrets, no cache, no setup step, no install; checkout of the
base only (no `ref:`), `persist-credentials: false`, `fetch-depth: 0`; the PR fetched as data with
`git fetch --no-tags origin "refs/pull/${PR_NUMBER}/head"`; the event's values through `env:` only; the base's checker
run with `python3 -I ... --fetched FETCH_HEAD`. `harness-gates.yml` keeps `./test tests scripts/tests` and no visitor
job. `./test tests scripts/tests` green; at least 90% of added lines covered; lint 0 errors.
Surface: scripts/check_visitor_pr.py; scripts/tests/test_check_visitor_pr.py; .github/workflows/harness-gates.yml;
.github/workflows/visitor-pr.yml; .github/CODEOWNERS; docs/ARCHITECTURE.md; docs/sessions/session_2611041638.md;
this plan; NEXT-STEPS.md.
Design: one script, one function per rule's input (`changes` from `git diff --raw -z --no-renames base...head`,
`board` from `git ls-tree` and `git cat-file` on head, `allowed_name` for the file names, `going_shape` for rule 3),
`check` walks the changes; `private()` mirrored, not imported, so no repository code a PR could change is executed.
No dependency.
Test plan: `scripts/tests/test_check_visitor_pr.py`, a real git repository per test in tmp_path: the passing shapes;
each rule's failures (parametrized); the file names for a visitor and for the owner (the owner's proof PR with a
workflow edit and `people/bob/x.html` fails); `private()` covers `community.py`'s; the fetched-head check; a visitor
editing `.github/` fails rule 1; the workflow files as text (trigger, permissions, no `${{` in a run line, no secrets,
cache, setup or `ref:`, `-I`, the fetch); round 2, the page's file for every row of the real board, lower-case and
mixed-case author. Witnessed red: a stub first, then one mutation per behaviour (the session log lists them).
Architecture map delta: yes (a layout row and a boundary invariant). ADR: no (a CI check, recorded in the map).
Cross-repo impact: the page's going link must write the shape of rule 3.
Open questions: none.
BACKLOG: the live proof after merge (departure 4); making `visitor-pr` a required status check, with code-owner review
required for `/.github/`.
