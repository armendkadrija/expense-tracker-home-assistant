import pytest

from custom_components.expense_tracker.db import (
    DuplicateTypeError,
    ExpenseDB,
    TypeInUseError,
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


def test_remove_type_rejects_when_in_use(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()
    db.add_expense(
        "id-1", 10.0, "Groceries", "person.armend", "2026-09-07T10:00:00+00:00"
    )

    with pytest.raises(TypeInUseError):
        db.remove_type("Groceries")

    # Rejected removal must not have touched the type row.
    names = [name for name, _icon in db.list_types()]
    assert "Groceries" in names


def test_remove_type_succeeds_once_no_longer_in_use(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()
    db.add_expense(
        "id-1", 10.0, "Groceries", "person.armend", "2026-09-07T10:00:00+00:00"
    )

    db.remove_expense("id-1")
    db.remove_type("Groceries")  # no longer in use -- must not raise

    names = [name for name, _icon in db.list_types()]
    assert "Groceries" not in names


def test_list_types_with_usage_returns_counts(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()
    db.add_expense(
        "id-1", 10.0, "Groceries", "person.armend", "2026-09-07T10:00:00+00:00"
    )
    db.add_expense(
        "id-2", 5.0, "Groceries", "person.armend", "2026-09-08T10:00:00+00:00"
    )

    by_name = {t["name"]: t for t in db.list_types_with_usage()}

    assert by_name["Groceries"]["count"] == 2
    assert by_name["Groceries"]["icon"] == "mdi:cart"
    assert by_name["Transport"]["count"] == 0
