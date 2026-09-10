import pytest

from custom_components.expense_tracker.const import DEFAULT_TYPES
from custom_components.expense_tracker.db import (
    DuplicateTypeError,
    ExpenseDB,
    TypeInUseError,
    TypeSetMismatchError,
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


def test_add_type_appends_to_end_of_order(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()

    db.add_type("Subscriptions", "mdi:credit-card")

    names = [name for name, _icon in db.list_types()]
    assert names[-1] == "Subscriptions"
    assert names[:-1] == [name for name, _icon in DEFAULT_TYPES]


def test_reorder_types_persists_new_order(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()
    original_names = [name for name, _icon in db.list_types()]
    reversed_names = list(reversed(original_names))

    db.reorder_types(reversed_names)

    assert [name for name, _icon in db.list_types()] == reversed_names
    # Usage-count listing must follow the same order, not drift back to
    # alphabetical -- the add-expense card's type picker and the types
    # page both read their order from these two methods.
    assert [t["name"] for t in db.list_types_with_usage()] == reversed_names


def test_reorder_types_rejects_missing_type(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()
    names = [name for name, _icon in db.list_types()]

    with pytest.raises(TypeSetMismatchError):
        db.reorder_types(names[:-1])  # dropped one -- must be rejected

    # Rejected reorder must not have partially applied.
    assert [name for name, _icon in db.list_types()] == names


def test_reorder_types_rejects_unknown_type(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()
    names = [name for name, _icon in db.list_types()]

    with pytest.raises(TypeSetMismatchError):
        db.reorder_types(names + ["Nonexistent"])


def test_reorder_types_rejects_duplicate_entry(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()
    names = [name for name, _icon in db.list_types()]

    with pytest.raises(TypeSetMismatchError):
        db.reorder_types([names[0], names[0]] + names[2:])
