# Just Don't

**The name was the instruction.**

Just Don't is a small Discord game about a button everyone is told not to press.
Mention it, and it objects. Mention it again, and it remembers.

At first, it would simply like you to stop. Keep returning, and the objections
give way to disbelief, bargaining, paperwork, resignation, and a familiarity it
would prefer you didn't mention. The button is still annoyed. It has just become
rather accustomed to you.

## How to play

In a server where Just Don't is installed:

1. Mention the bot in a channel where it can read and reply.
2. Read its objection.
3. Decide whether you've learned anything.

For instructions, send a direct mention followed by `help`:

```text
@Just Don't help
```

Select the actual bot mention in Discord; its server nickname may differ.
An exact help request doesn't count as a ping. Give it about five seconds
between replies: it remembers rapid pings, but won't queue a flood of responses.

It plays in text channels, threads and forum posts, and voice/stage text chat.
When installed in a new server, it gives one short introduction after about
15 seconds, if a suitable system or bot channel is available.

## A small disagreement, with a memory

Each person has a separate relationship with the button in each server.
Your pings elsewhere won't spoil a fresh first impression here.

There are hundreds of authored replies, with more to discover than a changing
count. It may notice how you interrupt, recognize your return after an absence,
or recall an earlier exchange. Some responses mark an occasion; others are rare
slips in its carefully maintained air of indifference.

There is no leaderboard to climb. The reward is finding out what this particular
grump has to say to you next.

## Try it without Discord

The same game engine runs in a terminal with **Python 3.11 or later**.
Once you have the project files, terminal play needs no packages, bot token,
Discord account, or network connection.

```sh
git clone https://github.com/covesoft/Dont-Ping-Me.git
cd Dont-Ping-Me
python -m nuhuh --demo
```

Use `python3` or `py` if that is your system's Python command. To play a fresh,
disposable game yourself:

```sh
python -m nuhuh --db :memory:
```

Press **Enter** to ping, or type a message. Use `/help` for instructions and
`/quit` to leave. Running `python -m nuhuh` without the database option saves
your progress for next time.

For reviewers and the curious:

| Command | What it shows |
| --- | --- |
| `python -m nuhuh --demo` | First meetings, returns, newcomers, and repeated play, using simulated time |
| `python -m nuhuh --tour` | A preview of every personality stage |
| `python -m nuhuh --encounters` | A spoiler-filled preview of special replies and callbacks |

The previews leave your saved game alone. The encounter preview shows the copy
directly, without waiting for its usual triggers or chances.

## Run it or change its voice

Developers can edit the phrases and pacing in
[`nuhuh/data/phrases.json`](nuhuh/data/phrases.json), then restart. Replies are
written in advance; the game uses no AI service at runtime.

The Discord bot responds to direct mentions rather than monitoring surrounding
conversation. It uses minimal channel permissions and no privileged Discord
intents. It remembers interaction state, not message bodies; see the
[data and privacy notes](PRIVACY.md).

| I want to… | Read this |
| --- | --- |
| Set up a Discord copy, configure permissions, or troubleshoot it | [Operator guide](OPERATING.md) |
| Customize phrases or understand the engine and its tests | [Developer guide](DEVELOPING.md) |
| Host it as a Linux service | [Linux deployment guide](DEPLOYMENT.md) |
| Review the jam entry | [Submission overview](SUBMISSION.md) |
| Prepare a release | [Release checklist](RELEASE_CHECKLIST.md) and [changelog](CHANGELOG.md) |

The Python package is named `nuhuh`, the project's original codename.
Licensed under **AGPL-3.0-only**; see [LICENSE](LICENSE) for the full terms and
[NOTICE.md](NOTICE.md) for scope, copyright, and earlier MIT releases. Bundled
Unicode data retains its own [third-party notice](THIRD_PARTY_NOTICES.md).
