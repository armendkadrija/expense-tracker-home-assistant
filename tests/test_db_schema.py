import sqlite3

from custom_components.expense_tracker import db as db_module
from custom_components.expense_tracker.const import DEFAULT_TYPES
from custom_components.expense_tracker.db import ExpenseDB


def test_initialize_creates_tables_and_seeds_defaults(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()

    types = db.list_types()

    assert types == sorted(DEFAULT_TYPES)


def test_initialize_is_idempotent_and_does_not_reseed(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()
    db.add_type("Custom", "mdi:star")

    db.initialize()  # simulate a restart

    types = db.list_types()
    assert ("Custom", "mdi:star") in types
    assert len(types) == len(DEFAULT_TYPES) + 1


def test_initialize_runs_pending_migrations_and_bumps_user_version(
    tmp_path, monkeypatch
):
    """M1 regression: MIGRATIONS isn't just a decorative empty list -
    initialize() actually walks it for whatever versions are pending."""
    db_path = str(tmp_path / "expenses.db")
    db = ExpenseDB(db_path)
    db.initialize()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA user_version = 0")
    conn.commit()
    conn.close()

    monkeypatch.setattr(
        db_module, "MIGRATIONS", ["ALTER TABLE expenses ADD COLUMN currency TEXT"]
    )
    monkeypatch.setattr(db_module, "SCHEMA_VERSION", 1)

    db.initialize()

    conn = sqlite3.connect(db_path)
    columns = [row[1] for row in conn.execute("PRAGMA table_info(expenses)")]
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    conn.close()

    assert "currency" in columns
    assert version == 1
