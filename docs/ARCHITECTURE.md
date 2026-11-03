# Architecture map

last_reviewed: 2026-11-04

The one living map of this repository: components, flows, boundaries and invariants. Read it before touching unfamiliar code; update it in the same change that moves structure (`harness-close` step 3). It describes this repository only.

## What this repository is

The club's public system: the rooms loop (find the rooms, say you are going, go, log the day, grow a names-only network) as files in one repository that any member's agent can drive. Nothing runs on a server; GitHub Pages serves the map.

## Layout

| Path | Holds | Owner doc or skill |
|---|---|---|
| `README.md` | the front door: what this is, how to join, how a day works | the members |
| `AGENTS.md`, `docs/`, `scripts/`, `.githooks/`, `.github/` | the harness: rules, records, lint, hooks, CI | `docs/HARNESS.md` |
| `people/<name>/` | a member's own folder, in their own shape | the member |
| `.agents/skills/rooms/` | find, rank, pick, go, log; `fetch.py` writes the geojson, `score.py` the count | its `SKILL.md` |
| `rooms/` | the feed list, the venue pins, the generated geojson | `rooms` |
| `map/` | the Leaflet page: the rooms, every member's pins, the count | `rooms` |
| `tests/` | the tests and their fixtures; `./test` runs them | `AGENTS.md` Part B |

## Flows

- **Joining:** clone → `people/<you>/README.md` from the template → pull request.
- **A week:** `fetch.py` → the board → a member says they are going → the room → the day log → the network map.

## Boundaries and invariants

- **Private stays local.** Debriefs, cards, audio and transcripts live in `data/`, which git ignores; raw session transcripts stay in `docs/sessions/raw/`, also ignored. Bought by: ADR-0002.
  <!-- verify: present '^data/$' in .gitignore -->
- **Tests never touch the network.** The fetch is a command a member runs; the tests read fixtures. Bought by: the kit's CI, which has no feed access.
  <!-- verify: exists tests/fixtures/rooms.ics -->
