# Architecture map

last_reviewed: 2026-11-04

The one living map of this repository: components, flows, boundaries and invariants. Read it before touching unfamiliar code; update it in the same change that moves structure (`harness-close` step 3). It describes this repository only.

## What this repository is

The club's public system: the rooms loop (find the rooms, say you are going, go, log the day, grow a names-only network) as files in one repository that any member's agent can drive through the `community` skill. Nothing runs on a server; GitHub carries the pull requests and the notifications; GitHub Pages serves the map.

## Layout

| Path | Holds | Owner doc or skill |
|---|---|---|
| `README.md` | the front door: what this is, how to join, how a day works, the rules | the members |
| `AGENTS.md`, `docs/`, `scripts/`, `.githooks/`, `.github/` | the harness: rules, records, lint, hooks, CI | `docs/HARNESS.md` |
| `scripts/check_visitor_pr.py`, `scripts/tests/` | the CI check of a pull request's `going/` and `people/` files (the `visitor-pr` job) and its tests; CI runs `./test tests scripts/tests` | its docstring |
| `people/<member>/` | a member's own folder: `README.md` (the four lines), `knows.md` (`# knows: <member>`, then one `- <member>` line per member they know), and the rooms skill's `rooms.md` and `network.md` | the member |
| `people/_template/` | the newcomer's starting folder: a `README.md` of four `?` lines and a `knows.md` with its heading only | `community` |
| `people/members.json` | the member list the scripts share; generated | `connections.py` |
| `.agents/skills/rooms/` | find, rank, pick, go, log; `fetch.py` writes the geojson, `score.py` the count | its `SKILL.md` |
| `.agents/skills/community/` | what's on, who's going, I'm going, log my day, my network, join; `community.py` (the commands), `board.py` (the board), `connections.py` (the network map) | its `SKILL.md` |
| `rooms/` | the feed list, the venue pins, the generated geojson | `rooms` |
| `events/` | the board: one `<YYYY>-W<WW>.md` per ISO week, a table with the columns when, room, where, link, community, slug | `community` (`board.py`) |
| `going/` | one `<slug>/` folder per room and one `<member>.md` per member going: `# <member> is going: <slug>`, the board's row quoted, then the note (one file each, so the club app's prefilled new-file link can write it) | `community` |
| `days/<date>/` | the consent line in `README.md` (required before `community.py day` writes); one `<member>.md` per member who chooses to push a day log, under three headings | `community` |
| `network/` | `MAP.md`: who knows whom across the club, a mermaid graph and a table, names only | `community` (`connections.py`) |
| `map/` | the Leaflet page: the rooms, every member's pins, the count | `rooms` |
| `tests/` | the tests and their fixtures; `./test` runs them | `AGENTS.md` Part B |

<!-- verify: exists people/_template/README.md -->
<!-- verify: exists people/_template/knows.md -->
<!-- verify: exists .agents/skills/community/SKILL.md -->
<!-- verify: exists .agents/skills/community/community.py -->
<!-- verify: exists .agents/skills/community/board.py -->
<!-- verify: exists .agents/skills/community/connections.py -->
<!-- verify: exists events/README.md -->
<!-- verify: exists going/README.md -->
<!-- verify: exists days/2026-11-05/README.md -->
<!-- verify: exists network/README.md -->

## Flows

- **Joining:** clone or fork → `people/<you>/` from `people/_template/` (the four questions, answered by the member, never rewritten) → `git config community.member <you>` → pull request; the own folder needs no review.
- **A week:** `fetch.py` → `board.py` → `events/<week>.md` → a member says they are going → the room → the day log → `connections.py` → `network/MAP.md`.
- **`whats-on`:** `python3 .agents/skills/community/community.py whats-on` reads this week's `events/<YYYY>-W<WW>.md` back; `python3 .agents/skills/rooms/fetch.py` then `python3 .agents/skills/community/board.py` write it first.
- **`going <event>`:** `python3 .agents/skills/community/community.py going <event> --note "<why>"` writes `going/<slug>/<me>.md` (the board's row quoted, then the note) once and never another member's file; the pull request is the notification.
- **`whos-going [<event>]`:** `python3 .agents/skills/community/community.py whos-going` prints `<slug>: name (note), name` for every folder in `going/`, members sorted, or the one asked for; an old `going/<slug>.md` is named, not read.
- **`day`:** the agent writes the dictated log under the three headings; `python3 .agents/skills/community/community.py day --date <date> --from <file>` (or stdin) refuses an email, a phone number or a missing `days/<date>/README.md` and writes `days/<date>/<member>.md`; pushed only on the member's yes.
- **`knows <member>`:** `python3 .agents/skills/community/community.py knows <member>` appends `- <member>` to `people/<me>/knows.md`; `python3 .agents/skills/community/connections.py` then rewrites `people/members.json` and `network/MAP.md`, linking two members when either lists the other in `knows.md` or both have the same un-marked `First name (role)` in `network.md`.
- **`network`:** `python3 .agents/skills/community/community.py network` prints `people/<me>/knows.md`, then every line of `network/MAP.md` that mentions the member.

## Boundaries and invariants

- **Private stays local.** Debriefs, cards, audio and transcripts live in `data/`, which git ignores; raw session transcripts stay in `docs/sessions/raw/`, also ignored. Bought by: ADR-0002.
  <!-- verify: present '^data/$' in .gitignore -->
- **Tests never touch the network.** The fetch is a command a member runs; the tests read fixtures. Bought by: the kit's CI, which has no feed access.
  <!-- verify: exists tests/fixtures/rooms.ics -->
- **Public by choice, names only.** Everything here is public; a member publishes only what they choose; an outside person is `First name (role)` after a yes; a connection is two names; no email address appears under `people/`. Bought by: ADR-0003.
  <!-- verify: absent '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' in people -->
- **A visitor's pull request touches only that visitor's files.** A PR whose author is not the repository owner changes only `going/<slug>/<login>.md` and `people/<login>/`; every added or changed file under `going/` or `people/`, from anyone, is a regular file of at most 2 KB, UTF-8, with no email address or phone number, and a going file has the shape `going/README.md` gives, for a slug on the board. Bought by: the `visitor-pr` job in `.github/workflows/harness-gates.yml`, binding once it is a required status check; until then the person who merges checks the same by hand.
  <!-- verify: exists scripts/check_visitor_pr.py -->
  <!-- verify: present 'check_visitor_pr\.py' in .github -->
