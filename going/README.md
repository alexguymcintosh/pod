# going

One folder per room, `going/<slug>/` (the slug column of this week's board), and one file per member going, `going/<slug>/<member>.md`: first line `# <member> is going: <slug>`, then the board's row quoted (when, room, where, link), then the member's note, or nothing.
Written by `python3 .agents/skills/community/community.py going <event> --note "<why>"`, or by the club app's prefilled new-file link; the pull request that adds your file is the notification.
A visitor's first going file arrives by pull request like everything outside their own folder.
Read back by `python3 .agents/skills/community/community.py whos-going [<event>]`: `<slug>: name (note), name` for every room, members sorted, or the one asked for.
