# going

One file per room, `going/<slug>.md` (the slug column of this week's board): `# going: <slug>`, the board's row quoted (when, room, where, link), then one `- <member>: <note>` line per member who is going.
Written by `python3 .agents/skills/community/community.py going <event> --note "<why>"`; the pull request that adds your line is the notification.
Read back by `python3 .agents/skills/community/community.py whos-going [<event>]`: `<slug>: name, name` for every room, or the one asked for.
