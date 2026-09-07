import pytest

from custom_components.expense_tracker.db import (
    DuplicateTypeError,
    ExpenseDB,
    UnknownTypeError,
)


def test_add_type_rejects_duplicate_name(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()

    with pytest.raises(DuplicateTypeError):
        db.add_type("Groceries", "mdi:cart-outline")


def test_remove_type_deletes_it(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()
    db.add_type("Subscriptions", "mdi:credit-card")

    db.remove_type("Subscriptions")

    names = [name for name, _icon in db.list_types()]
    assert "Subscriptions" not in names


def test_remove_type_rejects_unknown_name(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()

    with pytest.raises(UnknownTypeError):
        db.remove_type("Nonexistent")
