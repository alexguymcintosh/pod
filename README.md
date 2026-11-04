# the club

Put yourself where the better people are.

This repository is the club's public home: "essentially the exact same workflow that I used to actually find the event and plan the day in the first place", open to anyone who joins.

Members "look for all these events", pick one, and "put it out into the shared group, and everyone gets notified".

Then "other people can join that event, and then everyone can see publicly who goes to which event".

After the room "you dump everything you learned or did ... and it goes in and builds your own actual network", and "if you know two people, it connects you".

The network is names, never notes: "it doesn't have the details of the actual person's confidential information". To join, "you just got to join a repo and use their agent to communicate through the system", and "your agent will tell you what's going on".

**The map:** [the rooms this week, pinned](https://alexguymcintosh.github.io/pod/map/) (GitHub Pages serves `map/`; the data is `rooms/melbourne.geojson`).

## Join

1. Clone or fork this repository.
2. Copy `people/_template/` to `people/<you>/` (your GitHub login, in lower case) and answer its four lines.
3. Open a pull request. Your own folder needs no review; a member merges it.

Or paste this into any agent:

```text
Read this repository's README.md and AGENTS.md. Ask me the four questions in people/_template/README.md (who I am, what I'm building, what I want to learn, my links), make people/<you>/ from people/_template/ with my answers, <you> being my GitHub login in lower case; set `git config community.member <you>`; show me the folder; on my yes, fork this repository if I cannot push to it, push a branch and open the pull request; then tell me what is on this week.
```

## A day

Say the words to your own agent; the command is what it runs (the `community` skill, `.agents/skills/community/SKILL.md`).

1. **what's on**: `python3 .agents/skills/community/community.py whats-on` prints this week's board from `events/`.
2. **I'm going `<room>`**: `python3 .agents/skills/community/community.py going <room> --note "<why>"` adds your line to `going/<slug>.md`; **who's going** (`python3 .agents/skills/community/community.py whos-going`) reads it back.
3. **the room**: no command. One name, one sentence, one ask; phone away; the consent line in `days/<date>/README.md` before you record anyone.
4. **log my day**: your agent writes what you dictate under three headings (what I learned; who I met, first name and role only; follow-ups) and runs `python3 .agents/skills/community/community.py day --from <file>`, which refuses an email or a phone number and writes `days/<date>/<you>.md`. Your agent shows you the file and pushes only on your yes.
5. **my network**: `python3 .agents/skills/community/community.py network` shows who you know and where the map links you; `python3 .agents/skills/community/community.py knows <member>` adds a member; `python3 .agents/skills/community/connections.py` redraws `network/MAP.md`, linking two members when one lists the other or both met the same person.

## Rules

1. Your folder is yours: `people/<you>/` changes only for you and needs no review.
2. Everything else changes by pull request with two yeses from members.
3. Names only: an outside person is `First name (role)`, and only after they said yes; no phone numbers, no emails; nothing said in confidence; nothing recorded without a yes, and a recording stays on the member's phone. A no is a no. A maybe is a no.
4. Private stays on your machine: debriefs, cards, audio and transcripts live in `data/`, which git ignores; you publish only what you choose.
5. A line starting with `?` is a draft its owner has not approved.
