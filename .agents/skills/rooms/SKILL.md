---
name: rooms
description: The club's rooms loop, the in-person part of the people system - the agent finds the events near the city, ranks them by growth, picks for the member, writes the brief; the member goes, meets people and dictates a debrief; the agent writes the log, the person lines and the follow-up queue, and the Sunday count reads it. Use when a member says "rooms", "plan my rooms", "what's on this week", "brief me", "log the room", "debrief", "rooms count" or "Sunday count".
---

# rooms - put yourself where the better people are

A room is any event where people who can grow you gather. The loop: the agent finds and picks the rooms
and writes the brief; the member walks in, present; the member dictates a debrief; the agent writes the log.
The agent does everything but the communication. The log is the data that later ranks rooms.

## Files

| file | what | who writes |
|---|---|---|
| `rooms/feeds.txt` | public ICS feeds, a `# community` line above each URL | anyone |
| `rooms/venues.json` | pins for events with no GEO, matched by venue name; an entry with `who: <member>` is that member's waypoint, drawn on the map | anyone |
| `rooms/melbourne.geojson` | the candidates, next 21 days; generated, never hand-edited | `fetch.py` |
| `people/<name>/rooms.md` | that member's picks and log, one row per room | that member only |
| `people/<name>/network.md` | that member's people, one line per outside person met | that member only |
| `brief.md`, `debrief.md` (this folder) | the templates for before and after a room | by pull request |
| `data/` (git-ignored) | briefs, debriefs, audio and one card per person; private to the member's machine | the member (`data/inbox/`) and his agent |
| `map/index.html` | the map: the feeds' rooms, each member's `went` and `going` rows pinned by `venue`, waypoints, the people lines and the count | anyone |

An agent only writes the files of the member it is working for. Paths in `data/`: a room is
`data/go/<YYYY-MM-DD>-<room-slug>/`, a person is `data/people/<slug>.md`; a slug is the name in lower case
with hyphens (`couch-conversations`, `sam-founder`).

## 1. Find (Sunday, then each morning the member says "rooms")

First, people: ask the member who he wants to meet in this city and look for where those people will be.
Then rooms:

```
python3 .agents/skills/rooms/fetch.py
```

It prints one `ok` line per feed, every `unplaced` event (in the city but no pin: add its venue to
`rooms/venues.json` and rerun) and a summary line `rooms: N placed, M unplaced, F feed(s) failed`. Exit 1
if any feed failed. Virtual events are dropped. London from January 2027 is the same script:
`--feeds rooms/london-feeds.txt --out rooms/london.geojson --center 51.5072,-0.1276 --tz Europe/London --city-words London`.

Then the search: Luma, Meetup, Eventbrite and Humanitix for the days ahead near the city. A calendar or
group with a feed goes into `rooms/feeds.txt` and the fetch is rerun; a one-off room goes straight into
the member's table by hand. The room search reads only those four sites and the feeds, read-only; the
people look-up and the brief read any public page, nothing behind a login.

## 2. Rank by growth

Read the member's own goals in `people/<name>/`. Score each candidate 0-3 on each axis and show the top ten
with one line of reasoning each:

| axis | 3 means |
|---|---|
| **who is in the room** | builders and operators a level above us: hack or demo > talk > panel > mixer |
| **rare access** | screened, approval-only, small, or a speaker you cannot reach any other way |
| **the member's goal** | moves what his own section says he is after (for Alex: the US company, 2028) |
| **give** | the member can demo, speak, volunteer or ask a question on stage |
| **new** | a room nobody in the club has logged yet (a regular scores on proximity instead) |

The rubric is a starting guess. Once four weeks of logs exist, rank rooms by what they produced (the
"who I met" and "what came of it" columns) and say where the data disagrees with the rubric.

Principles behind it: newcomers enter at the edge and give small real things (legitimate peripheral
participation); regulars get liked (mere exposure, proximity); weak ties carry the new information
(Granovetter); luck surface area is doing times telling. It fails when it is passive.

## 3. Pick

The agent picks as many rooms as the week holds and says why in one line each; the member may say no to
any of them. A good week mixes three kinds: **high-bar technical** (the hardest room you can get into),
**left-field** (outside the AI bubble) and **give** (you demo, speak, host or help). Flag a **club night**
when a room suits all members; write `with <name>` in `why` when you go together.

Add the picks as rows to `people/<name>/rooms.md` with status `going`. The `venue` cell is one of the
`match` strings of an entry in `rooms/venues.json`, so the map can pin the row; a venue with no entry gets
one, with the geojson point's coordinates or the address on the event page. Create the file with this header
if it is missing:

```
| date | room | venue | why | status | who I met | what came of it |
|---|---|---|---|---|---|---|
| 2026-11-04 | [Couch Conversations](https://luma.com/cremorne-7ljk) 17:30 | Cremorne Digital Hub | left-field; with a friend | going | | |
```

`date` is `YYYY-MM-DD`. `status` is `going` or `went` (delete the row if you skipped it). The member
clicks an RSVP that needs his login; the agent does the rest.

## 4. Go

The morning of the room the agent writes the brief from `brief.md` into `data/go/<date>-<room-slug>/brief.md`:
where and when to leave, the hosts and the named people with one public link and a quote each, an opening
question, the model and a boldness 1-5 for this room (start from the Frame and Bias lines in the member's
node, the member's own `README.md`; proposals, the member may change a word), what to wear, and one "last time" line
from the member's last debrief. Nothing from behind a login; a name in the brief is not yet a name in the repo.

In the room the member carries three things: one name, one sentence, one ask. Phone away. End good
conversations with the snowball ask: "Who's the most interesting person you know in X?" Ask before
recording anyone; when the answer is no, the debrief is the transcript. A recording is transcribed on the
phone or locally, never uploaded; the audio stays in the room's folder under `data/go/`.

## 5. Log (the same night)

The member dictates the debrief (`debrief.md`, speech to text on the phone) and drops it in `data/inbox/`.
The agent then writes, in this order:

1. one card per person in `data/people/<slug>.md`: the full name, what they offered, what was said in
   confidence, meet again, and the draft of any follow-up words for the member to rewrite and send; never
   committed;
2. the room's `going` row turned into its `went` row (one row per room), with `?` in front of its date;
   **who I met** as `First name (role)` separated by `; `, **what came of it** as the follow-up booked, the
   intro asked or received, or `nothing`;
3. one line per outside person met in `network.md` (section 6), with `?` in front; never a club member;
4. every promise as a follow-up with a date in that line;
5. the next thing: the intro to ask for, the coffee to book (logged as a room with one person) or the
   next room; it goes into the next brief.

A real person's name reaches the repository only as a draft: the agent writes the row and the line with
`?` as the first thing in the first cell (`| ? 2026-11-04 | ...`), never commits or pushes them, and the
member removes the `?`. Write only what that person would be fine to see in a shared repository: first name
and role, no phone numbers, no emails, nothing said in confidence. A person already logged keeps their
exact `First name (role)` so the count sees one person. A name heard but not met stays in the card. The
session log gets the fetch command and its summary line; never a brief, a name or a quote.

## 6. network.md

One table, one person per line, in `people/<name>/network.md` (made-up names below):

```
| person | met at | follow-up | knows |
|---|---|---|---|
| Sam (founder) | Couch Conversations, 2026-11-04 | 2026-11-06 | Priya (PhD) |
| Priya (PhD) | Couch Conversations, 2026-11-04 | | Sam (founder) |
```

`person` is `First name (role)`. `follow-up` is the date the next message is due, or empty. `knows` links
only people who have their own line here, separated by `; ` (the connection between the people you know).
The lines you have un-marked are "how many people do you know?".

## 7. Sunday count

```
python3 .agents/skills/rooms/score.py
```

For the last seven days it prints, per member: rooms went, people met and **new outside people met** (a
`First name (role)` in "who I met" that is not a club member and that member has not logged before); and,
over every un-marked line of `network.md`, people known and follow-ups queued. Members are the folders under
`people/`; a member is never an outside person, whatever role follows the first
name; a `?` row is not counted. The club reads the table together on Sunday. It is a log of progress, not a
leaderboard: the conversation is about what came of it.
