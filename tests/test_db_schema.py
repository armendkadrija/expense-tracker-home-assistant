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
