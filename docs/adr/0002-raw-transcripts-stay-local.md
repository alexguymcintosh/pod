# ADR-0002: Raw session transcripts stay on the session host

**Status:** Accepted. **Date:** 2026-10-21. **Trigger:** bootstrapping a repository that a second member will clone.

## Context

Part A section 8 copies each session's raw transcript into `docs/sessions/raw/<host>/` and commits it. A raw transcript holds everything the session host loaded: its private global instructions, its memory, every file it read. Measured on 2026-10-21 in the sibling repository that runs the same kit: each of its three committed transcripts carries the host's private global instructions (a term from them appears five times in each). This repository is shared by two members, and its invariants say raw data stays on each member's own box and nothing reaches the repository unscrubbed.

## Decision

Ignore `docs/sessions/raw/` in git. `save_transcript.py` still copies the transcript there at close, so the record leaves the vendor folder and stays on the session host's disk. The session log (`docs/sessions/session_<stamp>.md`), written for the reader and holding only the work, is committed as before.

## Consequences

- The raw record is not versioned or mirrored: a lost disk loses it. A clone cannot audit the raw conversation, only the session log.
- Part A section 8 holds for the session log only. The `session-log` and `promotions` push checks still bind.
- A session log must be written knowing the other member reads it.

## Alternatives rejected

- Commit raw transcripts as the kit ships: it hands the session host's private context to every member.
- Scrub transcripts before committing: no scrubber is reliable over tool output, and a miss is permanent in git history.
- A second private repository for transcripts: a second store to keep, for a record nobody reads.
