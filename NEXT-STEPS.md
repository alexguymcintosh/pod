# NEXT-STEPS

Rewritten at every `harness-close`. Assume the next session knows nothing that is not written here.

## What is true now (measured 2026-11-04)

- The kit is in from the pod's main (84209b9) with the `rooms` skill, its data and the map. Lint 0 errors; `./test` 19 passed.
- Nothing of the club's own system exists yet: no front door, no `community` skill, no board, no network map.

## Step 0: re-verify before acting on anything above

1. `python3 scripts/harness_lint.py`
2. `git status --short && git log --oneline -3`
3. `./test`

## Open threads

- Build the smallest complete loop (plan in `docs/plans/`).
