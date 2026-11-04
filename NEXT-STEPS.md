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
