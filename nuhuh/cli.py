"""Play the same core game locally, without Discord or third-party packages."""

import argparse
from pathlib import Path
import sqlite3
import time

from . import __version__
from .engine import Game, positive_id, timestamp
from .phrases import DEFAULT_PHRASES, PhraseBook
from .helptext import help_text, mention_kind


def _id(text: str) -> int:
    try:
        return positive_id(int(text))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _pings(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("pings must be an integer from 1 through 1000") from exc
    if not 1 <= value <= 1000:
        raise argparse.ArgumentTypeError("pings must be an integer from 1 through 1000")
    return value


def _seconds(text: str) -> float:
    try:
        value = timestamp(float(text))
        if value > 3652500000:
            raise ValueError("Use a duration of at most 100 years")
        return value
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def demonstrate(phrases):
    """Exercise actual engine events with a virtual clock and several identities."""
    scenarios = [
        (2, 1000000, "First ping in a guild"),
        *[(2, 1000000 + n * 5, f"Repeat {n}, showing event/tier mixing") for n in range(1, 7)],
        (2, 1086431, "Same user, over a day later"),
        (3, 1086600, "A second participant"),
        (4, 1086800, "A third participant"),
        (5, 1087000, "A fourth participant"),
        (6, 1087200, "A fifth participant"),
        (7, 1087400, "A newcomer joins five existing participants"),
        (2, 1087600, "Ordinary tier reply after the recent window"),
    ]
    with Game(phrases) as game:
        for user_id, now, label in scenarios:
            reply = game.ping(1, user_id, now=now)
            print(f"{label} [{reply.event_id or reply.tier_id}]")
            print(reply.text, flush=True)
            game.delivered(reply)


def tour(phrases, guild_id, user_id):
    """Preview the ordinary tier pools without changing a saved relationship."""
    for index, tier in enumerate(phrases.tiers):
        upper = str(phrases.tiers[index + 1].min_count - 1) if index + 1 < len(phrases.tiers) else "+"
        span = f"{tier.min_count}-{upper}" if upper != "+" else f"{tier.min_count}+"
        _, phrase = phrases.select(guild_id, user_id, tier.min_count, None)
        print(f"[{span} / {tier.id}]")
        print(phrase.text.format(count=tier.min_count, others=0), flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Just Don't — an offline demo of nuhuh.")
    parser.add_argument("--version", action="version", version=f"nuhuh {__version__}")
    parser.add_argument("--guild-id", type=_id, default=1, help="simulated guild (default: 1)")
    parser.add_argument("--user-id", type=_id, default=1, help="simulated user (default: 1)")
    parser.add_argument("--db", default=".nuhuh/demo.sqlite3", help="database path, or :memory: for a fresh run")
    parser.add_argument("--phrases", type=Path, default=DEFAULT_PHRASES, help="custom phrase JSON file")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--pings", type=_pings, help="print N replies and exit instead of playing interactively")
    mode.add_argument("--demo", action="store_true", help="show context events and recent/tier mixing in a disposable game")
    mode.add_argument("--tour", action="store_true", help="preview every count tier without changing saved data")
    parser.add_argument("--step-seconds", type=_seconds, default=0, help="advance simulated time after each ping (default: 0)")
    parser.add_argument("--debug", action="store_true", help="show count and tier beside each reply")
    args = parser.parse_args(argv)
    try:
        phrases = PhraseBook.load(args.phrases)
        if args.tour:
            tour(phrases, args.guild_id, args.user_id)
            return 0
        if args.demo:
            demonstrate(phrases)
            return 0
        if args.db != ":memory:":
            Path(args.db).expanduser().parent.mkdir(parents=True, exist_ok=True)
        database = str(Path(args.db).expanduser()) if args.db != ":memory:" else args.db
        with Game(phrases, database) as game:
            offset = 0

            def ping(response_event=None) -> None:
                nonlocal offset
                reply = game.ping(args.guild_id, args.user_id, now=time.time() + offset,
                                  response_event=response_event)
                prefix = f"[{reply.count} / {reply.tier_id}] " if args.debug else ""
                if args.debug and reply.event_id:
                    prefix += f"[{reply.event_id}] "
                print(prefix + reply.text, flush=True)
                game.delivered(reply)
                offset += args.step_seconds

            if args.pings is not None:
                for _ in range(args.pings):
                    ping()
                return 0
            print("Just Don't — offline demo")
            print(f"Guild {args.guild_id}, user {args.user_id}. Enter to ping; /help; /wait SECONDS; /quit to leave.")
            while True:
                try:
                    command = input("> ").strip()
                except EOFError:
                    print()
                    break
                if command.casefold() in ("/quit", "quit", "exit"):
                    break
                kind = mention_kind(f"<@1> {command[1:]}", 1) if command.startswith("/") else "ping"
                if kind == "help":
                    info = game.help(args.guild_id, args.user_id, now=time.time() + offset)
                    title, description, footer = help_text(info.count > 0)
                    print(f"{title}\n\n{description}\n\n{footer}")
                    continue
                if kind == "help_extra":
                    ping(response_event="help_extra")
                    continue
                if command.casefold().startswith("/wait "):
                    try:
                        seconds = _seconds(command[6:].strip())
                    except argparse.ArgumentTypeError as exc:
                        print(str(exc))
                        continue
                    offset += seconds
                    print(f"Clock advanced by {seconds:g} seconds.")
                    continue
                if command:
                    print("Press Enter to ping, use /help or /wait SECONDS, or type /quit.")
                    continue
                ping()
    except KeyboardInterrupt:
        print()
        return 0
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(2, f"nuhuh: {exc}\n")
    return 0
