# Plan (feature): demo-home, the club's public system
Status: done 2026-11-04 10:36. Departures: the scripts live in the community skill folder, not scripts/ (one-kind); knows.md is the names-only member list, network.md keeps the rooms skill's meaning; Thursday's day folder holds the consent line only; the root commit was rewritten once (cc6e4e5) to scrub two member names from history.

Observed: the private repository (`pod-private`) already has the rooms loop built and audited: `.agents/skills/rooms/` (`fetch.py`,
`score.py`, the brief and debrief templates), `rooms/` (feeds, venues, the generated geojson) and `map/index.html`,
with 19 passing tests. The kit is copied from the private repository's main (84209b9); lint 0 errors. Alex's spec (4 Nov 09:55) is
in the kickoff: "essentially the exact same workflow that I used to actually find the event and plan the day in the
first place" made public: "anyone essentially to join the club, you just got to join a repo and use their agent to
communicate through the system".
Assumed: the repository is public under Alex's account (the pod stays private); GitHub Pages serves it from the root
of `main`, so the map's relative fetches work unchanged; members' agents are Claude Code, Codex or opencode and
read `AGENTS.md` and `.agents/skills/` natively; nobody but Alex has a folder before Thursday.

Acceptance criteria: on a phone, the Pages map shows this week's rooms and every member's pins; `events/<week>.md`
lists the rooms with time, place, link and community; `going/<slug>.md` lists who is going; `days/2026-11-05/`
holds only the consent line until Thursday; `network/MAP.md` links members by name only; a newcomer pastes the join
prompt into any agent and gets a pull request adding `people/<you>/README.md`; `./test` green; lint 0 errors; the
whole loop verified once by the integrator as a fake member in a local clone.
Surface: README.md; people/_template/**; people/alex/**; events/**; going/**; days/2026-11-05/README.md; network/**;
.agents/skills/community/** (SKILL.md, community.py, board.py, connections.py); tests/test_community.py;
tests/test_board.py; tests/test_connections.py; tests/fixtures/**; map/index.html (members from
`people/members.json`); docs/adr/0003-public-by-choice-names-only.md; docs/adr/README.md; docs/ARCHITECTURE.md;
NEXT-STEPS.md; docs/sessions/session_<stamp>.md; this plan.
Design: files, git and Pages; no server, no bot, no dependency. One skill, `community`, three stdlib scripts:
`board.py` (geojson to the week's board), `community.py` (going, whos-going, whats-on, day, network, knows),
`connections.py` (`people/members.json` and the names-only `network/MAP.md`). The scripts live in the skill folder,
not `scripts/`, so a product change never rides with tooling (`one-kind`); a departure from the kickoff's
`scripts/connections.py`. `people/<you>/network.md` keeps the rooms skill's meaning (outside people, `?` drafts);
`people/<you>/knows.md` is the names-only list of members you know, so the rooms skill and the map keep working.
Test plan: unit for the three scripts on fixtures, no network, at least 90% of added lines; e2e: the integrator joins
as `zed` in a local clone, says going, logs a day under the consent line, appears on the network map; bugfix
regression test: n/a (feature).
Architecture map delta: yes (new rows and flows). ADR: yes, 0003 "Public by choice, names only" (the cost named).
Cross-repo impact: none; the pod is untouched; the rooms skill is copied, not moved.
Open questions: (1) the repository's name (Alex: `rooms`, `walk-in` or `club`); (2) protect `main` (no force-push, no
delete, no required review): yes (fresh, 10:15); (3) Pages from the root of `main`: yes (fresh, 10:15).
BACKLOG: the social-media engine (the next build, after the demo); moving the repository into the organisation;
`fetch.py` reported two unplaced rooms (venues to add to `rooms/venues.json`).
