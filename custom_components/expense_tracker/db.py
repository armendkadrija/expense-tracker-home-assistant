"""Blocking SQLite access for the Expense Tracker integration.

Every method here does file I/O and must only ever be called via
hass.async_add_executor_job — never directly from the event loop.
"""
from __future__ import annotations

import os
import sqlite3

from .const import DEFAULT_TYPES, SCHEMA_VERSION

# Migrations as plain SQL strings, indexed by version: MIGRATIONS[i] is
# the migration that takes the schema from version i to version i + 1.
# No ORM, no migration framework - PRAGMA user_version plus this list is
# the whole mechanism. Each entry must be a single statement (see the
# conn.execute call below, which runs exactly one statement per call).
MIGRATIONS: list[str] = [
    # v0 -> v1: no-op placeholder. The CREATE TABLE statements in
    # initialize() already establish what shipped as schema version 1 --
    # no real installation has ever run at version 0 -- but this index
    # must stay reserved so the entries below land on the right version.
    "SELECT 1",
    # v1 -> v2: add the column expense-type ordering (drag-and-drop
    # reordering, see reorder_types) is stored in.
    "ALTER TABLE expense_types ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0",
    # v2 -> v3: backfill sort_order for rows that predate the column,
    # using their current alphabetical position -- keeps the visible
    # order stable across the upgrade instead of jumbling to whatever
    # order SQLite happens to return them in.
    "UPDATE expense_types SET sort_order = ("
    "SELECT COUNT(*) FROM expense_types e2 WHERE e2.name < expense_types.name)",
]


class DuplicateTypeError(ValueError):
    """Raised when adding a type whose name already exists."""


class UnknownTypeError(ValueError):
    """Raised when referencing a type name that does not exist."""


class UnknownExpenseError(ValueError):
    """Raised when referencing an expense id that does not exist."""


class TypeInUseError(ValueError):
    """Raised when trying to remove a type that at least one expense
    still references. Removal is unsafe to allow here because type_name
    is deliberately not a real foreign key (see remove_type's docstring
    and the spec's "not a real FK" note) -- there is no cascade to fall
    back on, so blocking the removal outright is the only safe choice."""


class TypeSetMismatchError(ValueError):
    """Raised when reorder_types isn't given exactly the current set of
    type names. A partial list would leave the omitted types at whatever
    sort_order they already had, silently interleaving them with the
    reordered ones in a way nothing in the UI would explain."""


class ExpenseDB:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def initialize(self) -> None:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS expense_types "
                "(name TEXT PRIMARY KEY, icon TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS expenses ("
                "id TEXT PRIMARY KEY, amount REAL NOT NULL, "
                "type_name TEXT NOT NULL, user TEXT NOT NULL, "
                "receipt_path TEXT, note TEXT, timestamp TEXT NOT NULL)"
            )
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            for migration_sql in MIGRATIONS[version:SCHEMA_VERSION]:
                conn.execute(migration_sql)
            if version < SCHEMA_VERSION:
                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            count = conn.execute(
                "SELECT COUNT(*) FROM expense_types"
            ).fetchone()[0]
            if count == 0:
                conn.executemany(
                    "INSERT INTO expense_types (name, icon, sort_order) "
                    "VALUES (?, ?, ?)",
                    [
                        (name, icon, i)
                        for i, (name, icon) in enumerate(DEFAULT_TYPES)
                    ],
                )
            conn.commit()
        finally:
            conn.close()

    def list_types(self) -> list[tuple[str, str]]:
        conn = sqlite3.connect(self._db_path)
        try:
            rows = conn.execute(
                "SELECT name, icon FROM expense_types ORDER BY sort_order"
            ).fetchall()
            return rows
        finally:
            conn.close()

    def list_types_with_usage(self) -> list[dict]:
        """Like list_types, plus how many expenses currently reference
        each type -- the types-management page needs this to know which
        types are safe to delete without the user having to try and fail
        first."""
        conn = sqlite3.connect(self._db_path)
        try:
            rows = conn.execute(
                "SELECT et.name, et.icon, COUNT(e.id) "
                "FROM expense_types et "
                "LEFT JOIN expenses e ON e.type_name = et.name "
                "GROUP BY et.name, et.icon, et.sort_order "
                "ORDER BY et.sort_order"
            ).fetchall()
            return [
                {"name": row[0], "icon": row[1], "count": row[2]} for row in rows
            ]
        finally:
            conn.close()

    def add_type(self, name: str, icon: str) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            existing = conn.execute(
                "SELECT 1 FROM expense_types WHERE name = ?", (name,)
            ).fetchone()
            if existing:
                raise DuplicateTypeError(f"Type '{name}' already exists")
            # New types go at the end of the display order, not wherever
            # SQLite happens to place them.
            next_order = conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM expense_types"
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO expense_types (name, icon, sort_order) "
                "VALUES (?, ?, ?)",
                (name, icon, next_order),
            )
            conn.commit()
        finally:
            conn.close()

    def reorder_types(self, ordered_names: list[str]) -> None:
        """Persist a full drag-and-drop reorder. `ordered_names` must be
        exactly the current set of type names, in their new order -- see
        TypeSetMismatchError."""
        conn = sqlite3.connect(self._db_path)
        try:
            existing_names = {
                row[0]
                for row in conn.execute("SELECT name FROM expense_types").fetchall()
            }
            if (
                set(ordered_names) != existing_names
                or len(ordered_names) != len(existing_names)
            ):
                raise TypeSetMismatchError(
                    "Reorder must include every existing type exactly once"
                )
            conn.executemany(
                "UPDATE expense_types SET sort_order = ? WHERE name = ?",
                [(i, name) for i, name in enumerate(ordered_names)],
            )
            conn.commit()
        finally:
            conn.close()

    def remove_type(self, name: str) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            existing = conn.execute(
                "SELECT 1 FROM expense_types WHERE name = ?", (name,)
            ).fetchone()
            if not existing:
                raise UnknownTypeError(f"Type '{name}' does not exist")
            in_use_count = conn.execute(
                "SELECT COUNT(*) FROM expenses WHERE type_name = ?", (name,)
            ).fetchone()[0]
            if in_use_count > 0:
                raise TypeInUseError(
                    f"Cannot remove '{name}': {in_use_count} expense(s) "
                    "still use this type"
                )
            conn.execute("DELETE FROM expense_types WHERE name = ?", (name,))
            conn.commit()
        finally:
            conn.close()

    def add_expense(
        self,
        expense_id: str,
        amount: float,
        type_name: str,
        user: str,
        timestamp: str,
        receipt_path: str | None = None,
        note: str | None = None,
    ) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            existing = conn.execute(
                "SELECT 1 FROM expense_types WHERE name = ?", (type_name,)
            ).fetchone()
            if not existing:
                raise UnknownTypeError(f"Type '{type_name}' does not exist")
            conn.execute(
                "INSERT INTO expenses "
                "(id, amount, type_name, user, receipt_path, note, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (expense_id, amount, type_name, user, receipt_path, note, timestamp),
            )
            conn.commit()
        finally:
            conn.close()

    def remove_expense(self, expense_id: str) -> str | None:
        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute(
                "SELECT receipt_path FROM expenses WHERE id = ?", (expense_id,)
            ).fetchone()
            if row is None:
                raise UnknownExpenseError(f"Expense '{expense_id}' does not exist")
            conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            conn.commit()
            return row[0]
        finally:
            conn.close()

    def list_expenses(self, limit: int | None = None, offset: int = 0) -> list[dict]:
        conn = sqlite3.connect(self._db_path)
        try:
            query = (
                "SELECT id, amount, type_name, user, receipt_path, note, "
                "timestamp FROM expenses ORDER BY timestamp DESC"
            )
            params: tuple = ()
            if limit is not None:
                query += " LIMIT ? OFFSET ?"
                params = (limit, offset)
            rows = conn.execute(query, params).fetchall()
            return [
                {
                    "id": row[0],
                    "amount": row[1],
                    "type": row[2],
                    "user": row[3],
                    "receipt_path": row[4],
                    "note": row[5],
                    "timestamp": row[6],
                }
                for row in rows
            ]
        finally:
            conn.close()

    def get_totals(self, since: str | None = None) -> dict:
        conn = sqlite3.connect(self._db_path)
        try:
            where = "WHERE timestamp >= ?" if since else ""
            params = (since,) if since else ()
            total = conn.execute(
                f"SELECT COALESCE(SUM(amount), 0) FROM expenses {where}", params
            ).fetchone()[0]
            count = conn.execute(
                f"SELECT COUNT(*) FROM expenses {where}", params
            ).fetchone()[0]
            by_type = dict(
                conn.execute(
                    f"SELECT type_name, SUM(amount) FROM expenses {where} "
                    "GROUP BY type_name",
                    params,
                ).fetchall()
            )
            by_user = dict(
                conn.execute(
                    f"SELECT user, SUM(amount) FROM expenses {where} "
                    "GROUP BY user",
                    params,
                ).fetchall()
            )
            return {
                "total": total,
                "count": count,
                "by_type": by_type,
                "by_user": by_user,
            }
        finally:
            conn.close()
