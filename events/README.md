# events

The board: one file per ISO week, `events/<YYYY>-W<WW>.md`, a header line with the window, then a table with the columns when, room, where, link, community and slug, sorted by start.
Written by `python3 .agents/skills/community/board.py` (today in Melbourne, seven days; `--from` and `--days` change the window) from `rooms/melbourne.geojson`, which `python3 .agents/skills/rooms/fetch.py` refreshes; never hand-edited.
Read back by `python3 .agents/skills/community/community.py whats-on` (the newest board by file name), or on the live map.
