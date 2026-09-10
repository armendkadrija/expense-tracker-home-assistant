import os

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util

from custom_components.expense_tracker.const import DOMAIN, RECEIPTS_DIR


async def _setup(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_add_expense_service_inserts_and_updates_sensor(hass, tmp_path):
    await _setup(hass, tmp_path)

    await hass.services.async_call(
        DOMAIN,
        "add_expense",
        {"amount": 12.5, "type": "Groceries", "user": "person.armend"},
        blocking=True,
    )

    total = hass.states.get("sensor.expense_tracker_total")
    assert float(total.state) == 12.5


async def test_add_expense_resolves_user_from_calling_context_when_omitted(
    hass, tmp_path
):
    from homeassistant.core import Context

    await _setup(hass, tmp_path)
    hass.states.async_set("person.armend", "home", {"user_id": "the-caller"})

    await hass.services.async_call(
        DOMAIN,
        "add_expense",
        {"amount": 5.0, "type": "Groceries"},  # no `user`
        blocking=True,
        context=Context(user_id="the-caller"),
    )

    total = hass.states.get("sensor.expense_tracker_total")
    assert total.attributes["by_user"] == {"person.armend": 5.0}


async def test_add_expense_raises_when_user_omitted_and_unresolvable(hass, tmp_path):
    from homeassistant.core import Context

    await _setup(hass, tmp_path)
    # No person entity linked to this (or any) user_id.

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "add_expense",
            {"amount": 5.0, "type": "Groceries"},
            blocking=True,
            context=Context(user_id="someone-unlinked"),
        )


async def test_add_expense_service_rejects_unknown_type(hass, tmp_path):
    await _setup(hass, tmp_path)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "add_expense",
            {"amount": 1.0, "type": "NotAType", "user": "person.armend"},
            blocking=True,
        )


async def test_add_expense_unknown_type_with_receipt_writes_no_orphaned_file(
    hass, tmp_path
):
    """Regression test for the receipt-ordering bug: the type must be
    validated BEFORE the receipt file is saved, so a rejected call must
    never leave an orphaned receipt file on disk. (Type validation fails
    before the receipt field is ever touched, so a fake, never-resolved
    file_id is fine here.)"""
    await _setup(hass, tmp_path)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "add_expense",
            {
                "amount": 1.0,
                "type": "NotAType",
                "user": "person.armend",
                "receipt": "fake-never-resolved-file-id",
            },
            blocking=True,
        )

    receipts_root = os.path.join(str(tmp_path), RECEIPTS_DIR)
    if os.path.exists(receipts_root):
        assert os.listdir(receipts_root) == []


async def test_add_expense_deletes_receipt_when_add_expense_raises_any_error(
    hass, tmp_path, stage_uploaded_file, monkeypatch
):
    """M4 regression: previously only the specific UnknownTypeError path
    (already unreachable here since the type is validated up front) was
    guarded. If runtime.async_add_expense fails for ANY reason after a
    receipt was already saved, that receipt file must not be left
    orphaned on disk."""
    entry = await _setup(hass, tmp_path)
    runtime = hass.data[DOMAIN][entry.entry_id]
    file_id = await stage_uploaded_file("receipt.jpg", b"receipt-bytes")

    async def _boom(**kwargs):
        raise RuntimeError("simulated database failure")

    monkeypatch.setattr(runtime, "async_add_expense", _boom)

    with pytest.raises(RuntimeError):
        await hass.services.async_call(
            DOMAIN,
            "add_expense",
            {
                "amount": 1.0,
                "type": "Groceries",
                "user": "person.armend",
                "receipt": file_id,
            },
            blocking=True,
        )

    receipts_root = os.path.join(str(tmp_path), RECEIPTS_DIR)
    assert not os.path.exists(receipts_root) or os.listdir(receipts_root) == []


async def test_add_expense_accepts_explicit_none_for_optional_fields(hass, tmp_path):
    """Regression test for the real bug: when a script field is left
    blank, HA's template rendering (`{{ date | default(None) }}`) produces
    a real Python None, not an omitted key. cv.string rejects None
    outright ("string value is None"), so a blank optional field on the
    dashboard form would previously blow up the whole call.
    """
    await _setup(hass, tmp_path)

    await hass.services.async_call(
        DOMAIN,
        "add_expense",
        {
            "amount": 3.0,
            "type": "Groceries",
            "user": "person.armend",
            "date": None,
            "receipt": None,
            "note": None,
        },
        blocking=True,
    )

    total = hass.states.get("sensor.expense_tracker_total")
    assert float(total.state) == 3.0


async def test_add_expense_backdated_to_first_of_month_counts_in_month_total(
    hass, tmp_path
):
    """Regression test for the reviewer-found bug: a bare date string
    (what the real `date` selector actually produces, e.g. "2026-09-01")
    must be normalized to a full UTC ISO timestamp before being stored,
    and the "this month" sensor's boundary must be computed in the
    configured local timezone (the test harness's `hass` fixture sets
    US/Pacific) -- not UTC -- so this backdated expense isn't silently
    excluded by a string comparison quirk or a shifted month boundary.
    """
    await _setup(hass, tmp_path)
    first_of_month = dt_util.now().strftime("%Y-%m-01")

    await hass.services.async_call(
        DOMAIN,
        "add_expense",
        {
            "amount": 42.0,
            "type": "Groceries",
            "user": "person.armend",
            "date": first_of_month,
        },
        blocking=True,
    )

    month_total = hass.states.get("sensor.expense_tracker_total_this_month")
    assert float(month_total.state) == 42.0


async def test_add_type_updates_sensor_types_attribute_immediately(hass, tmp_path):
    """The sensors' `types` attribute must reflect a new type right away,
    not just after the next expense is logged -- other config (e.g. a
    helper kept in sync by an automation) reads the live type list from
    here."""
    await _setup(hass, tmp_path)

    await hass.services.async_call(
        DOMAIN, "add_type", {"name": "Subscriptions", "icon": "mdi:credit-card"},
        blocking=True,
    )

    total = hass.states.get("sensor.expense_tracker_total")
    assert "Subscriptions" in dict(total.attributes["types"])

    await hass.services.async_call(
        DOMAIN, "remove_type", {"name": "Subscriptions"}, blocking=True
    )

    total = hass.states.get("sensor.expense_tracker_total")
    assert "Subscriptions" not in dict(total.attributes["types"])


async def test_list_expenses_service_returns_expenses_with_icons(hass, tmp_path):
    await _setup(hass, tmp_path)
    await hass.services.async_call(
        DOMAIN,
        "add_expense",
        {"amount": 12.5, "type": "Groceries", "user": "person.armend"},
        blocking=True,
    )

    result = await hass.services.async_call(
        DOMAIN, "list_expenses", {}, blocking=True, return_response=True
    )

    assert len(result["expenses"]) == 1
    expense = result["expenses"][0]
    assert expense["amount"] == 12.5
    assert expense["type"] == "Groceries"
    assert expense["icon"] == "mdi:cart"  # Groceries' seeded default icon


async def test_list_expenses_service_respects_limit(hass, tmp_path):
    await _setup(hass, tmp_path)
    for _ in range(3):
        await hass.services.async_call(
            DOMAIN,
            "add_expense",
            {"amount": 1.0, "type": "Groceries", "user": "person.armend"},
            blocking=True,
        )

    result = await hass.services.async_call(
        DOMAIN, "list_expenses", {"limit": 2}, blocking=True, return_response=True
    )

    assert len(result["expenses"]) == 2


async def test_add_type_then_remove_type_service(hass, tmp_path):
    await _setup(hass, tmp_path)

    await hass.services.async_call(
        DOMAIN, "add_type", {"name": "Subscriptions", "icon": "mdi:credit-card"},
        blocking=True,
    )

    await hass.services.async_call(
        DOMAIN, "remove_type", {"name": "Subscriptions"}, blocking=True
    )

    total = hass.states.get("sensor.expense_tracker_total")
    assert "Subscriptions" not in dict(total.attributes["types"])


async def test_remove_type_rejects_unknown_name(hass, tmp_path):
    await _setup(hass, tmp_path)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "remove_type", {"name": "Nonexistent"}, blocking=True
        )


async def test_remove_type_service_rejects_when_in_use(hass, tmp_path):
    await _setup(hass, tmp_path)
    await hass.services.async_call(
        DOMAIN, "add_expense",
        {"amount": 9.99, "type": "Groceries", "user": "person.armend"},
        blocking=True,
    )

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "remove_type", {"name": "Groceries"}, blocking=True
        )

    # Rejected removal must leave the type fully intact and usable.
    total = hass.states.get("sensor.expense_tracker_total")
    assert "Groceries" in dict(total.attributes["types"])


async def test_remove_type_service_succeeds_once_expense_is_gone(hass, tmp_path):
    await _setup(hass, tmp_path)
    await hass.services.async_call(
        DOMAIN, "add_expense",
        {"amount": 9.99, "type": "Groceries", "user": "person.armend"},
        blocking=True,
    )
    result = await hass.services.async_call(
        DOMAIN, "list_expenses", {}, blocking=True, return_response=True
    )
    expense_id = result["expenses"][0]["id"]
    await hass.services.async_call(
        DOMAIN, "remove_expense", {"id": expense_id}, blocking=True
    )

    await hass.services.async_call(  # must not raise now
        DOMAIN, "remove_type", {"name": "Groceries"}, blocking=True
    )

    total = hass.states.get("sensor.expense_tracker_total")
    assert "Groceries" not in dict(total.attributes["types"])


async def test_list_types_service_returns_usage_counts(hass, tmp_path):
    await _setup(hass, tmp_path)
    await hass.services.async_call(
        DOMAIN, "add_expense",
        {"amount": 9.99, "type": "Groceries", "user": "person.armend"},
        blocking=True,
    )

    result = await hass.services.async_call(
        DOMAIN, "list_types", {}, blocking=True, return_response=True
    )

    by_name = {t["name"]: t for t in result["types"]}
    assert by_name["Groceries"]["count"] == 1
    assert by_name["Groceries"]["icon"] == "mdi:cart"
    assert by_name["Transport"]["count"] == 0


async def test_reorder_types_service_persists_order(hass, tmp_path):
    await _setup(hass, tmp_path)
    result = await hass.services.async_call(
        DOMAIN, "list_types", {}, blocking=True, return_response=True
    )
    original = [t["name"] for t in result["types"]]
    reversed_names = list(reversed(original))

    await hass.services.async_call(
        DOMAIN, "reorder_types", {"names": reversed_names}, blocking=True
    )

    result = await hass.services.async_call(
        DOMAIN, "list_types", {}, blocking=True, return_response=True
    )
    assert [t["name"] for t in result["types"]] == reversed_names


async def test_reorder_types_service_rejects_partial_list(hass, tmp_path):
    await _setup(hass, tmp_path)
    result = await hass.services.async_call(
        DOMAIN, "list_types", {}, blocking=True, return_response=True
    )
    original = [t["name"] for t in result["types"]]

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "reorder_types", {"names": original[:-1]}, blocking=True
        )


async def test_reorder_types_updates_add_expense_sensor_attribute_order(
    hass, tmp_path
):
    """The add-expense card's type picker reads sensor.expense_tracker_total's
    `types` attribute -- it must reflect a reorder immediately, the same
    way it already does for add_type/remove_type."""
    await _setup(hass, tmp_path)
    result = await hass.services.async_call(
        DOMAIN, "list_types", {}, blocking=True, return_response=True
    )
    reversed_names = list(reversed([t["name"] for t in result["types"]]))

    await hass.services.async_call(
        DOMAIN, "reorder_types", {"names": reversed_names}, blocking=True
    )

    state = hass.states.get("sensor.expense_tracker_total")
    assert [name for name, _icon in state.attributes["types"]] == reversed_names


async def test_remove_expense_service_deletes_and_updates_sensor(hass, tmp_path):
    await _setup(hass, tmp_path)
    runtime = hass.data[DOMAIN][list(hass.data[DOMAIN])[0]]
    await runtime.async_add_expense(
        expense_id="id-1",
        amount=5.0,
        type_name="Groceries",
        user="person.armend",
        timestamp="2026-09-07T10:00:00+00:00",
    )

    await hass.services.async_call(
        DOMAIN, "remove_expense", {"id": "id-1"}, blocking=True
    )

    total = hass.states.get("sensor.expense_tracker_total")
    assert total.attributes["count"] == 0
