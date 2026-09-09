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


def test_list_expenses_returns_most_recent_first(tmp_path):
    db = _seeded_db(tmp_path)
    db.add_expense(
        "id-old", 5.0, "Groceries", "person.armend", "2026-09-01T00:00:00+00:00"
    )
    db.add_expense(
        "id-new", 7.0, "Transport", "person.armend", "2026-09-05T00:00:00+00:00"
    )

    expenses = db.list_expenses()

    assert [e["id"] for e in expenses] == ["id-new", "id-old"]
    assert expenses[0]["amount"] == 7.0
    assert expenses[0]["type"] == "Transport"


def test_list_expenses_respects_limit_and_offset(tmp_path):
    db = _seeded_db(tmp_path)
    for i in range(5):
        db.add_expense(
            f"id-{i}", float(i), "Groceries", "person.armend",
            f"2026-09-0{i + 1}T00:00:00+00:00",
        )

    page = db.list_expenses(limit=2, offset=1)

    # Most recent first: id-4, id-3, id-2, id-1, id-0 -- offset 1, limit 2
    # skips id-4 and returns id-3, id-2.
    assert [e["id"] for e in page] == ["id-3", "id-2"]
