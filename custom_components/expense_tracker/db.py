"""Blocking SQLite access for the Expense Tracker integration.

Every method here does file I/O and must only ever be called via
hass.async_add_executor_job — never directly from the event loop.
"""
from __future__ import annotations

import os
import sqlite3

from .const import DEFAULT_TYPES, SCHEMA_VERSION


class DuplicateTypeError(ValueError):
    """Raised when adding a type whose name already exists."""


class UnknownTypeError(ValueError):
    """Raised when referencing a type name that does not exist."""


class UnknownExpenseError(ValueError):
    """Raised when referencing an expense id that does not exist."""


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
            if version < SCHEMA_VERSION:
                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            count = conn.execute(
                "SELECT COUNT(*) FROM expense_types"
            ).fetchone()[0]
            if count == 0:
                conn.executemany(
                    "INSERT INTO expense_types (name, icon) VALUES (?, ?)",
                    DEFAULT_TYPES,
                )
            conn.commit()
        finally:
            conn.close()

    def list_types(self) -> list[tuple[str, str]]:
        conn = sqlite3.connect(self._db_path)
        try:
            rows = conn.execute(
                "SELECT name, icon FROM expense_types ORDER BY name"
            ).fetchall()
            return rows
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
            conn.execute(
                "INSERT INTO expense_types (name, icon) VALUES (?, ?)",
                (name, icon),
            )
            conn.commit()
        finally:
            conn.close()
