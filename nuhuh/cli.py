"""Play the same core game locally, without Discord or third-party packages."""

import argparse
from pathlib import Path
import sqlite3

from . import __version__
from .engine import Game, positive_id
from .phrases import DEFAULT_PHRASES, PhraseBook


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Just Don't — an offline demo of nuhuh.")
    parser.add_argument("--version", action="version", version=f"nuhuh {__version__}")
    parser.add_argument("--guild-id", type=_id, default=1, help="simulated guild (default: 1)")
    parser.add_argument("--user-id", type=_id, default=1, help="simulated user (default: 1)")
    parser.add_argument("--db", default=".nuhuh/demo.sqlite3", help="database path, or :memory: for a fresh run")
    parser.add_argument("--phrases", type=Path, default=DEFAULT_PHRASES, help="custom phrase JSON file")
    parser.add_argument("--pings", type=_pings, help="print N replies and exit instead of playing interactively")
    parser.add_argument("--debug", action="store_true", help="show count and tier beside each reply")
    args = parser.parse_args(argv)
    try:
        phrases = PhraseBook.load(args.phrases)
        if args.db != ":memory:":
            Path(args.db).expanduser().parent.mkdir(parents=True, exist_ok=True)
        database = str(Path(args.db).expanduser()) if args.db != ":memory:" else args.db
        with Game(phrases, database) as game:
            def ping() -> None:
                reply = game.ping(args.guild_id, args.user_id)
                prefix = f"[{reply.count} / {reply.tier_id}] " if args.debug else ""
                print(prefix + reply.text, flush=True)
                game.delivered(reply)

            if args.pings is not None:
                for _ in range(args.pings):
                    ping()
                return 0
            print("Just Don't — offline demo")
            print(f"Guild {args.guild_id}, user {args.user_id}. Enter to ping; /quit to leave.")
            while True:
                try:
                    command = input("> ").strip()
                except EOFError:
                    print()
                    break
                if command.casefold() in ("/quit", "quit", "exit"):
                    break
                if command:
                    print("Press Enter to ping, or type /quit.")
                    continue
                ping()
    except KeyboardInterrupt:
        print()
        return 0
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(2, f"nuhuh: {exc}\n")
    return 0
