# NEXT-STEPS

Rewritten at every `harness-close`. Assume the next session knows nothing that is not written here.

## What is true now (measured 2026-11-04)

- The loop exists: the `community` skill (`going`, `whos-going`, `whats-on`, `day`, `knows`, `network` in `community.py`), `board.py` (the week's board) and `connections.py` (the names-only network map), with their tests under `tests/`.
- The repository is public at github.com/alexguymcintosh/pod and GitHub Pages serves `map/` at https://alexguymcintosh.github.io/pod/map/.
- `days/2026-11-05/` holds the consent line only.
- `going/` is one file per member per room, `going/<slug>/<member>.md`, so the club app's prefilled new-file link can say "I'm going" (branch `app-going-format`, plan `docs/plans/PLAN-app-going-format-2611041506.md`).

## Step 0: re-verify before acting on anything above

1. `python3 scripts/harness_lint.py`
2. `git status --short && git log --oneline -3`
3. `./test`

## Open threads

- Alex fills his four `?` lines in `people/alex/README.md`; nobody writes them for him.
- Members add themselves: `people/<member>/` from `people/_template/` by pull request (the join prompt in `README.md`).
- The social-media engine is the next build, after the demo.
- Make `harness-gates / visitor-pr` a required status check on main (plan `docs/plans/PLAN-visitor-pr-check-2611041649.md`). Until then visitor PRs are merged one at a time by the four-line hand checklist: one file at `going/<slug>/<pr-author>.md`; the slug is on the board; no email, phone, link or symlink; nothing else changed. The last line stays binding after the check is required, since a PR can edit its own workflow (the plan's departure 2).
- The page's going link writes `# <login> is going: <slug>`, a blank line, the board's row quoted as `community.py`'s QUOTED join, then the optional note: the shape `scripts/check_visitor_pr.py` rule 3 requires.
