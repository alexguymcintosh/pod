# ADR-0003: Public by choice, names only

**Status:** Proposed. **Date:** 2026-11-04. **Trigger:** the public repository: the club's system leaves the private pod, and anyone can read it.

## Context

The rooms loop was built in a private repository for a few members. Alex's words set the public version: "everyone can see publicly who goes to which event", and the network "doesn't have the details of the actual person's confidential information. It's just people who are friends or shared in the GitHub ... then you can share each other's network names, just not the actual content and detail of it". A public repository is read by search engines, by the people named in it and by anyone the club wants to attract. Whatever enters its history stays there: a name removed later was still published. The `rooms` skill already keeps the private side (cards, audio, debriefs) in `data/`, which git ignores, and publishes an outside person only as `First name (role)` behind a `?` draft until the member removes it.

## Decision

Everything in this repository is public, and a member publishes only what that member chooses. A member's folder `people/<member>/` is theirs; nothing in it is required beyond the four lines of the template. An outside person appears only as a first name and a role, and only after they said yes to being named; a recording needs the consent line read out first, and a no or a maybe is a no. A connection is two names and nothing more: `network/MAP.md` says who knows whom, never what was said. Phone numbers, emails, surnames, employers' secrets, anything said in confidence and the content of any conversation stay in `data/` on the member's machine. A line that starts with `?` is a draft and is never treated as settled. A public speaker named in a public event's title is a public event fact and stays in the board and the map.

## Consequences

- The cost is thinness: a public network of first names and roles cannot be mined for warm introductions by reading the files alone. The member who knows the person makes the introduction, by asking. That is the point.
- Every member's agent must know the rule, so the `community` skill and its day-log procedure carry it, and the lint keeps `people/` free of email addresses (a `verify: absent` claim in `docs/ARCHITECTURE.md`, checked at every commit and in CI), while `community.py` refuses an email address or a phone number before anything is written.
- A mistake is permanent in git history; a name pushed in error needs a history rewrite and a request to GitHub, so the draft marker and the ask-before-push rule are not optional.
- The private pod remains the home of the full cards and debriefs: two repositories, one loop.

## Alternatives rejected

- A private repository with a public mirror: two copies to keep honest, and a mirror that leaks once is public anyway; the choice of what is public belongs with each member, at the line, not with a sync script.
- A chat platform (Discord or similar) for the club, with GitHub for the code: people split across two systems, nothing is a file an agent can read, and the record belongs to the platform, not the club.
