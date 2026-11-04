# Plan (refactor): app-going-format, one file per member per room
Status: done 2026-11-04 15:08. Departures: none.

Observed: `going/<slug>.md` is one file per room with one `- <member>: <note>` line per member, written by
`community.py going` (append) and read by `community.py whos-going`. The club app lets a visitor say "I'm going"
through GitHub's own prefilled new-file page, which can only create a file, never append a line to an existing one.
The only readers of `going/` are `community.py` (`going`, `whos-going`) and the docs (`going/README.md`, the
`community` SKILL.md, `README.md`, `docs/ARCHITECTURE.md`, `board.py`'s docstring); `map/index.html` and
`connections.py` never read `going/` (the map pins `going` rows from `people/<member>/rooms.md`). `origin/main` holds
no `going/<slug>.md` beyond `going/README.md`.
Assumed: the club app writes the same file shape the script writes.

Acceptance criteria: `community.py going <event> [--note]` writes `going/<slug>/<me>.md` (first line
`# <me> is going: <slug>`, then the board's row quoted when the board has it, then the note or nothing); a second
call is a no-op; it never touches another member's file; it refuses a note with an email or a phone number; the slug
resolution and the `--as` rules are unchanged; `whos-going [<event>]` reads the directories, members sorted, notes
shown, and names any old `going/<slug>.md` file loudly; the docs say the new layout and that a visitor's first going
file arrives by pull request; `./test` green; at least 90% of added lines covered; lint 0 errors.
Surface: .agents/skills/community/community.py; .agents/skills/community/SKILL.md; .agents/skills/community/board.py
(docstring); going/README.md; README.md; tests/test_community.py; docs/ARCHITECTURE.md; NEXT-STEPS.md;
docs/sessions/session_2611041506.md; this plan.
Design: one function each. `going` resolves the slug as today (an existing `going/<slug>/` directory is the key as it
is), then writes `going/<slug>/<me>.md` with `x` mode; an existing file for me (any case) is "already going".
`whos_going` lists the directories under `going/`, members by file stem sorted, the note as the file's lines that are
not the heading or the quote, `<slug>: ana (demo), ben`; an old `going/<slug>.md` is listed with a pointer to move it.
No dependency, no migration script (no old file exists).
Test plan: unit in `tests/test_community.py`: the new path and content, idempotence, a second member, the refusal,
never another member's file, the short-slug resolution into a directory, whos-going over directories with notes and
an old file; witnessed red before the code. Bugfix regression test: n/a (refactor of a format).
Architecture map delta: yes (the `going/` row and the two flows). ADR: no (a file format, recorded in the skill).
Cross-repo impact: the club app writes `going/<slug>/<member>.md` through the prefilled new-file link.
Open questions: none.
BACKLOG: a going file written through the club app's new-file link never passes `community.py`'s email and phone refusal; the pull request's two yeses are the only gate today (a CI check over `going/` would close it, a tooling change).
