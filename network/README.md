# network

`network/MAP.md`: who knows whom across the club, as a mermaid graph and a table (member, knows, shared names); names only, never what was said.
Written by `python3 .agents/skills/community/connections.py` from every `people/<member>/knows.md` and `network.md`, with `people/members.json` (the sorted member list) beside it; never hand-edited. Two members are linked when either lists the other, or both have the same un-marked `First name (role)` in `network.md`.
Read back by `python3 .agents/skills/community/community.py network`: your `knows.md`, then every line of the map that mentions you.
