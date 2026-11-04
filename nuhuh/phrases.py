"""Validated, developer-editable phrase pools and stable selection."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from string import Formatter


MAX_COUNT = 2**63 - 1
DEFAULT_PHRASES = Path(__file__).with_name("data") / "phrases.json"


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


def _keys(value: object, required: set[str], location: str) -> dict:
    if not isinstance(value, dict):
        raise PhraseError(f"{location}: expected an object")
    missing = required - value.keys()
    extra = value.keys() - required
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
            if field is not None and (field != "count" or spec or conversion):
                raise PhraseError(f"{location}: only the plain {{count}} placeholder is allowed")
        rendered = value.format(count=MAX_COUNT)
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

    @classmethod
    def load(cls, path: Path = DEFAULT_PHRASES) -> "PhraseBook":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PhraseError(f"Cannot load {path}: {exc}") from exc
        root = _keys(raw, {"schema_version", "tiers"}, "phrase file")
        if type(root["schema_version"]) is not int or root["schema_version"] != 1:
            raise PhraseError("phrase file: schema_version must be 1")
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
        return cls(tuple(tiers))

    def select(
        self, guild_id: int, user_id: int, count: int, last_phrase_id: str | None
    ) -> tuple[Tier, Phrase]:
        tier = next(tier for tier in reversed(self.tiers) if tier.min_count <= count)
        candidates = tuple(p for p in tier.phrases if p.id != last_phrase_id) or tier.phrases
        # v1: ordered JSON integers/strings, SHA-256, unsigned big-endian modulo.
        payload = json.dumps([1, guild_id, user_id, count, tier.id], separators=(",", ":"))
        draw = int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest(), "big")
        return tier, candidates[draw % len(candidates)]
