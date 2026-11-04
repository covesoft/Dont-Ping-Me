# Just Don't

**An ornery button that practically begs to be pressed.**

Just Don't is a small Discord game about ignoring one very simple instruction.
Mention it, and it objects. Keep going, and its objections become a relationship:
disbelief, bargaining, paperwork, resignation, and reluctant familiarity.

The game has 135 editable phrases, six stages, and contextual replies for first
contact, returning users, recent pings, and joining an existing group of pingers.
Its seeded choices give each user a distinct progression within each server.

It also runs entirely offline from a terminal. Evaluators need only Python
3.11+, with no token, Discord account, dependencies, or network connection:

```sh
python -m nuhuh --demo
python -m nuhuh --tour
python -m nuhuh --db :memory:
```

For the interactive game, press Enter to ping, `/wait 86401` to simulate time
away, and `/quit` to leave. The offline game and Discord bot share the same
engine. The bot uses SQLite, minimal channel permissions, and no privileged
Discord intents. Developers can change its voice by editing a JSON file.

Repository: https://github.com/covesoft/Dont-Ping-Me

Stack: Python, SQLite, and discord.py for optional Discord play. MIT licensed.
