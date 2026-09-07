import pytest

from custom_components.expense_tracker.db import (
    ExpenseDB,
    UnknownExpenseError,
    UnknownTypeError,
)


def _seeded_db(tmp_path):
    db = ExpenseDB(str(tmp_path / "expenses.db"))
    db.initialize()
    return db


def test_add_expense_rejects_unknown_type(tmp_path):
    db = _seeded_db(tmp_path)

    with pytest.raises(UnknownTypeError):
        db.add_expense(
            "id-1", 12.50, "NotAType", "person.armend", "2026-09-07T10:00:00+00:00"
        )


def test_add_and_total_expenses(tmp_path):
    db = _seeded_db(tmp_path)
    db.add_expense(
        "id-1", 12.50, "Groceries", "person.armend", "2026-09-07T10:00:00+00:00"
    )
    db.add_expense(
        "id-2", 7.25, "Transport", "person.partner", "2026-09-07T11:00:00+00:00"
    )

    totals = db.get_totals()

    assert totals["total"] == pytest.approx(19.75)
    assert totals["count"] == 2
    assert totals["by_type"] == {"Groceries": 12.50, "Transport": 7.25}
    assert totals["by_user"] == {"person.armend": 12.50, "person.partner": 7.25}


def test_get_totals_filters_by_since(tmp_path):
    db = _seeded_db(tmp_path)
    db.add_expense(
        "id-old", 100.0, "Groceries", "person.armend", "2025-01-01T00:00:00+00:00"
    )
    db.add_expense(
        "id-new", 5.0, "Groceries", "person.armend", "2026-09-07T00:00:00+00:00"
    )

    totals = db.get_totals(since="2026-09-01T00:00:00+00:00")

    assert totals["total"] == pytest.approx(5.0)
    assert totals["count"] == 1


def test_remove_expense_returns_receipt_path_and_deletes_row(tmp_path):
    db = _seeded_db(tmp_path)
    db.add_expense(
        "id-1",
        12.50,
        "Groceries",
        "person.armend",
        "2026-09-07T10:00:00+00:00",
        receipt_path="www/expense_tracker/receipts/id-1.jpg",
    )

    receipt_path = db.remove_expense("id-1")

    assert receipt_path == "www/expense_tracker/receipts/id-1.jpg"
    assert db.get_totals()["count"] == 0


def test_remove_expense_rejects_unknown_id(tmp_path):
    db = _seeded_db(tmp_path)

    with pytest.raises(UnknownExpenseError):
        db.remove_expense("nonexistent")
