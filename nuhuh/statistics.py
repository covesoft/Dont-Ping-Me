# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""Read-only usage summaries of recorded guild/user counts."""

from collections import Counter
from dataclasses import dataclass
from statistics import mean, median


@dataclass(frozen=True)
class Distribution:
    samples: int
    maximum: int | None
    p95: int | None
    average: float | None
    median: float | None
    mode: int | None

    @classmethod
    def of(cls, values):
        values = sorted(values)
        if not values:
            return cls(0, None, None, None, None, None)
        frequencies = Counter(values)
        highest = max(frequencies.values())
        modes = [value for value, frequency in frequencies.items() if frequency == highest]
        # Nearest rank: the smallest observed value covering at least 95%.
        p95_index = (95 * len(values) + 99) // 100 - 1
        return cls(len(values), values[-1], values[p95_index], mean(values), median(values),
                   modes[0] if len(modes) == 1 else None)


@dataclass(frozen=True)
class UsageStatistics:
    total_pesters: int
    per_guild: Distribution
    per_relationship: Distribution

    @classmethod
    def from_rows(cls, rows):
        guild_totals = Counter()
        relationship_counts = []
        for guild_id, count in rows:
            guild_totals[guild_id] += count
            relationship_counts.append(count)
        # Python integers keep totals safe even when they exceed SQLite SUM's range.
        return cls(sum(relationship_counts), Distribution.of(guild_totals.values()),
                   Distribution.of(relationship_counts))
