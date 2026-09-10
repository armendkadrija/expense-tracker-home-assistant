import sqlite3

from custom_components.expense_tracker import db as db_module
from custom_components.expense_tracker.const import DEFAULT_TYPES
from custom_components.expense_tracker.db import ExpenseDB


def test_initialize_creates_tables_and_seeds_defaults(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()

    types = db.list_types()

    # list_types() is in display order (sort_order), not alphabetical --
    # seeded defaults keep DEFAULT_TYPES' own order.
    assert types == DEFAULT_TYPES


def test_initialize_is_idempotent_and_does_not_reseed(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()
    db.add_type("Custom", "mdi:star")

    db.initialize()  # simulate a restart

    types = db.list_types()
    assert ("Custom", "mdi:star") in types
    assert len(types) == len(DEFAULT_TYPES) + 1


def test_initialize_migrates_pre_sort_order_db_alphabetically(tmp_path):
    """A database created before sort_order existed (schema v1: just
    name + icon, no ordering column) must gain the column and have it
    backfilled from the only order that existed before -- alphabetical --
    so upgrading doesn't visibly reshuffle anyone's existing types."""
    db_path = str(tmp_path / "expenses.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE expense_types (name TEXT PRIMARY KEY, icon TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE expenses (id TEXT PRIMARY KEY, amount REAL NOT NULL, "
        "type_name TEXT NOT NULL, user TEXT NOT NULL, receipt_path TEXT, "
        "note TEXT, timestamp TEXT NOT NULL)"
    )
    conn.executemany(
        "INSERT INTO expense_types (name, icon) VALUES (?, ?)",
        [("Zoo", "mdi:paw"), ("Apple", "mdi:food-apple"), ("Mango", "mdi:fruit")],
    )
    conn.execute("PRAGMA user_version = 1")
    conn.commit()
    conn.close()

    db = ExpenseDB(db_path)
    db.initialize()

    assert [name for name, _icon in db.list_types()] == ["Apple", "Mango", "Zoo"]
    conn = sqlite3.connect(db_path)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    conn.close()
    assert version == 3


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
