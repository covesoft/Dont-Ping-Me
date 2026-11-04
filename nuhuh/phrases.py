# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""Validated, developer-editable phrase pools and stable selection."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from string import Formatter

from .signals import Signals


MAX_COUNT = 2**63 - 1
DEFAULT_PHRASES = Path(__file__).with_name("data") / "phrases.json"
CONTEXT_EVENT_IDS = ("first_guild_ping", "new_user_in_crowd", "first_user_ping", "returning_user", "recent_ping")
MESSAGE_EVENT_IDS = ("large_text", "emoji", "repeated_mentions", "apology", "bargaining", "group_incident")
MEMORY_EVENTS = {
    "large_text": "shorter_this_time",
    "emoji": "emoji_callback",
    "repeated_mentions": "single_knock",
    "apology": "broken_promise",
}
EVENT_IDS = CONTEXT_EVENT_IDS + ("help_extra",) + MESSAGE_EVENT_IDS + tuple(MEMORY_EVENTS.values()) + ("milestone", "rare_admission")


class PhraseError(ValueError):
    """An actionable error in an editable phrase file."""


@dataclass(frozen=True)
class Phrase:
    id: str
    text: str


@dataclass(frozen=True)
class Tier:
    id: str
    min_count: int
    phrases: tuple[Phrase, ...]


@dataclass(frozen=True)
class Context:
    first_guild_ping: bool
    first_user_ping: bool
    other_users: int
    elapsed_seconds: float | None


@dataclass(frozen=True)
class EventPool:
    id: str
    phrases: tuple[Phrase, ...]


@dataclass(frozen=True)
class ContextRules:
    recent_seconds: int = 120
    return_after_seconds: int = 86400
    crowd_min_others: int = 5
    recent_one_in: int = 3


@dataclass(frozen=True)
class SurpriseRules:
    large_text_chars: int = 350
    message_one_in: int = 3
    callback_one_in: int = 12
    rare_one_in: int = 80
    rare_min_count: int = 151
    group_window_seconds: int = 60
    group_min_others: int = 3
    milestones: tuple[int, ...] = (10, 25, 50, 100, 250, 500, 1000)
    milestone_every: int = 1000


def _keys(value: object, required: set[str], location: str, optional: set[str] = frozenset()) -> dict:
    if not isinstance(value, dict):
        raise PhraseError(f"{location}: expected an object")
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing or extra:
        raise PhraseError(
            f"{location}: missing fields {sorted(missing)}; unknown fields {sorted(extra)}"
        )
    return value


def _identifier(value: object, location: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_.-]*", value):
        raise PhraseError(f"{location}: use a lowercase ID such as 'familiar.hello'")
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise PhraseError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _text(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PhraseError(f"{location}: phrase text must be a nonempty string")
    try:
        for _, field, spec, conversion in Formatter().parse(value):
            if field is not None and (field not in ("count", "others") or spec or conversion):
                raise PhraseError(f"{location}: only plain {{count}} and {{others}} placeholders are allowed")
        rendered = value.format(count=MAX_COUNT, others=MAX_COUNT)
        if len(rendered.encode("utf-16-le")) // 2 > 2000:
            raise PhraseError(f"{location}: rendered text exceeds 2,000 UTF-16 units")
    except (ValueError, KeyError, IndexError, UnicodeError) as exc:
        if isinstance(exc, PhraseError):
            raise
        raise PhraseError(f"{location}: invalid text or braces: {exc}") from exc
    return value


@dataclass(frozen=True)
class PhraseBook:
    tiers: tuple[Tier, ...]
    events: tuple[EventPool, ...] = ()
    rules: ContextRules = ContextRules()
    surprises: SurpriseRules = SurpriseRules()

    @classmethod
    def load(cls, path: Path = DEFAULT_PHRASES) -> "PhraseBook":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PhraseError(f"Cannot load {path}: {exc}") from exc
        if not isinstance(raw, dict) or type(raw.get("schema_version")) is not int or raw["schema_version"] != 3:
            raise PhraseError("phrase file: schema_version must be 3")
        required = {"schema_version", "tiers", "context", "events"}
        root = _keys(raw, required, "phrase file", {"surprises"})
        if not isinstance(root["tiers"], list) or not root["tiers"]:
            raise PhraseError("phrase file: tiers must be a nonempty list")
        tiers = []
        tier_ids: set[str] = set()
        phrase_ids: set[str] = set()
        previous_min = 0
        for index, item in enumerate(root["tiers"]):
            row = _keys(item, {"id", "min_count", "phrases"}, f"tiers[{index}]")
            tier_id = _identifier(row["id"], f"tiers[{index}].id")
            if tier_id in tier_ids:
                raise PhraseError(f"Duplicate tier ID: {tier_id}")
            tier_ids.add(tier_id)
            minimum = row["min_count"]
            if type(minimum) is not int or not previous_min < minimum <= MAX_COUNT:
                raise PhraseError(f"{tier_id}: min_count must increase and be a positive integer")
            if index == 0 and minimum != 1:
                raise PhraseError(f"{tier_id}: the first tier must start at 1")
            previous_min = minimum
            if not isinstance(row["phrases"], list) or not row["phrases"]:
                raise PhraseError(f"{tier_id}: phrases must be a nonempty list")
            phrases = []
            for phrase_index, item in enumerate(row["phrases"]):
                location = f"{tier_id}.phrases[{phrase_index}]"
                phrase = _keys(item, {"id", "text"}, location)
                phrase_id = _identifier(phrase["id"], location + ".id")
                if phrase_id in phrase_ids:
                    raise PhraseError(f"Duplicate phrase ID: {phrase_id}")
                phrase_ids.add(phrase_id)
                phrases.append(Phrase(phrase_id, _text(phrase["text"], phrase_id)))
            tiers.append(Tier(tier_id, minimum, tuple(phrases)))
        events = []
        config = _keys(root["context"], {"recent_seconds", "return_after_seconds", "crowd_min_others", "recent_one_in"}, "context")
        for name, value in config.items():
            if type(value) is not int or not 1 <= value <= MAX_COUNT:
                raise PhraseError(f"context.{name}: must be a positive integer")
        rules = ContextRules(**config)
        if rules.recent_seconds >= rules.return_after_seconds:
            raise PhraseError("context: recent_seconds must be less than return_after_seconds")
        if not isinstance(root["events"], dict) or set(root["events"]) - set(EVENT_IDS):
            raise PhraseError(f"events: expected an object using these event IDs: {', '.join(EVENT_IDS)}")
        for event_id in EVENT_IDS:
            items = root["events"].get(event_id, [])
            if not isinstance(items, list):
                raise PhraseError(f"{event_id}: expected a phrase list (empty disables the event)")
            phrases = []
            for index, item in enumerate(items):
                location = f"events.{event_id}[{index}]"
                row = _keys(item, {"id", "text"}, location)
                phrase_id = _identifier(row["id"], location + ".id")
                if phrase_id in phrase_ids:
                    raise PhraseError(f"Duplicate phrase ID: {phrase_id}")
                phrase_ids.add(phrase_id)
                phrases.append(Phrase(phrase_id, _text(row["text"], phrase_id)))
            if phrases:
                events.append(EventPool(event_id, tuple(phrases)))
        config = _keys(root.get("surprises", {}), set(), "surprises", set(SurpriseRules.__dataclass_fields__))
        settings = dict(config)
        for name, value in settings.items():
            if name == "milestones":
                if (not isinstance(value, list)
                        or any(type(n) is not int or not 2 <= n <= MAX_COUNT for n in value)
                        or value != sorted(set(value))):
                    raise PhraseError("surprises.milestones: use a strictly increasing list of integers >= 2")
                settings[name] = tuple(value)
            elif type(value) is not int or not (0 if name == "milestone_every" else 1) <= value <= MAX_COUNT:
                raise PhraseError(f"surprises.{name}: must be {'a nonnegative' if name == 'milestone_every' else 'a positive'} integer")
        return cls(tuple(tiers), tuple(events), rules, SurpriseRules(**settings))

    def encounter_for(self, context: Context, signals: Signals, memories: dict[str, int],
                      active_others: int, guild_id: int, user_id: int, count: int) -> tuple[str | None, int | None]:
        """Choose one event, preserving first contact/returns and ordinary tiers.

        The optional origin count identifies the exact remembered setup to
        consume on delivery; merely selecting a callback never consumes it.
        """
        ordinary = self.event_for(context, guild_id, user_id, count)
        if ordinary not in (None, "recent_ping"):
            return ordinary, None
        enabled = {pool.id for pool in self.events}
        rules = self.surprises
        every = rules.milestone_every
        if "milestone" in enabled and (count in rules.milestones or (
                every and count >= max(every, max(rules.milestones, default=0)) and count % every == 0)):
            return "milestone", None
        # An acknowledged apology is betrayed by the next non-apology play.
        if not signals.apology and "apology" in memories and "broken_promise" in enabled:
            return "broken_promise", memories["apology"]

        matches = (signals.characters >= rules.large_text_chars, signals.emoji,
                   signals.mentions > 1, signals.apology, signals.bargaining,
                   active_others >= rules.group_min_others)
        candidates = [name for name, match in zip(MESSAGE_EVENT_IDS, matches) if match and name in enabled]
        def draw(label, options):
            return options[self._number([4, guild_id, user_id, count, label]) % len(options)]
        if candidates and self._number([4, guild_id, user_id, count, "message_gate"]) % rules.message_one_in == 0:
            return draw("message_choice", candidates), None

        # Recall only the absence of a previously acknowledged habit. Do not
        # make a "shorter" joke on another long message or betray an apology
        # while the player is apologizing again.
        absent = {"large_text": signals.characters < rules.large_text_chars,
                  "emoji": not signals.emoji, "repeated_mentions": signals.mentions <= 1}
        callbacks = [kind for kind, matches in absent.items()
                     if matches and kind in memories and MEMORY_EVENTS[kind] in enabled]
        if callbacks and self._number([4, guild_id, user_id, count, "callback_gate"]) % rules.callback_one_in == 0:
            kind = draw("callback_choice", callbacks)
            return MEMORY_EVENTS[kind], memories[kind]
        if ("rare_admission" in enabled and count >= rules.rare_min_count
                and self._number([4, guild_id, user_id, count, "rare_gate"]) % rules.rare_one_in == 0):
            return "rare_admission", None
        return ordinary, None

    def event_for(self, context: Context, guild_id: int, user_id: int, count: int) -> str | None:
        elapsed = context.elapsed_seconds
        matches = (
            context.first_guild_ping,
            context.first_user_ping and context.other_users >= self.rules.crowd_min_others,
            context.first_user_ping,
            elapsed is not None and elapsed > self.rules.return_after_seconds,
            elapsed is not None and 0 <= elapsed <= self.rules.recent_seconds
            and self._number([3, guild_id, user_id, count, "recent_gate"]) % self.rules.recent_one_in == 0,
        )
        enabled = {event.id for event in self.events}
        return next((event_id for event_id, match in zip(CONTEXT_EVENT_IDS, matches) if match and event_id in enabled), None)

    def select_event(self, event_id: str, guild_id: int, user_id: int, count: int, last_phrase_id: str | None, *, recent_phrase_ids: tuple[str, ...] = ()) -> Phrase:
        pool = next(event for event in self.events if event.id == event_id)
        payload = [2, guild_id, user_id, count, "event:" + event_id]
        return self._draw(pool.phrases, payload, last_phrase_id, recent_phrase_ids)

    @staticmethod
    def _number(payload: list) -> int:
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return int.from_bytes(hashlib.sha256(encoded).digest(), "big")

    @staticmethod
    def _draw(phrases: tuple[Phrase, ...], payload: list, last_phrase_id: str | None,
              recent_phrase_ids: tuple[str, ...] = ()) -> Phrase:
        avoided = [phrase_id for phrase_id in recent_phrase_ids if phrase_id != last_phrase_id]
        if last_phrase_id is not None:
            avoided.append(last_phrase_id)
        while True:
            candidates = tuple(p for p in phrases if p.id not in avoided)
            if candidates:
                break
            # Custom pools can be smaller than the history window. Relax the
            # oldest exclusion first, retaining the newest whenever possible.
            avoided.pop(0)
        return candidates[PhraseBook._number(payload) % len(candidates)]

    def select(
        self, guild_id: int, user_id: int, count: int, last_phrase_id: str | None,
        *, recent_phrase_ids: tuple[str, ...] = ()
    ) -> tuple[Tier, Phrase]:
        tier = next(tier for tier in reversed(self.tiers) if tier.min_count <= count)
        # Preserve the v0.1 count-tier algorithm for event-free selections.
        return tier, self._draw(tier.phrases, [1, guild_id, user_id, count, tier.id], last_phrase_id, recent_phrase_ids)
