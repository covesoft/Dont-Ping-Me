# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""Run the suite and fail if any SQLite connection is not explicitly closed.

Retaining handles makes this independent of garbage-collection timing. This
also catches test-helper leaks on Linux, where unlinking open files can succeed.
"""

from pathlib import Path
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    opened = []
    original_connect = sqlite3.connect

    class TrackedConnection(sqlite3.Connection):
        explicitly_closed = False

        def close(self):
            super().close()
            self.explicitly_closed = True

    def connect(*args, **kwargs):
        kwargs.setdefault("factory", TrackedConnection)
        connection = original_connect(*args, **kwargs)
        opened.append(connection)
        return connection

    sqlite3.connect = connect
    try:
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        sqlite3.connect = original_connect
    leaked = [db for db in opened if not getattr(db, "explicitly_closed", False)]
    print(f"SQLite connections: {len(opened)} opened; {len(leaked)} not explicitly closed.")
    return 0 if result.wasSuccessful() and not leaked else 1


if __name__ == "__main__":
    raise SystemExit(main())
