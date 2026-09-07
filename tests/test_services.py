import base64
import os

import pytest
import yaml
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.exceptions import ServiceValidationError

from custom_components.expense_tracker.const import (
    DOMAIN,
    RECEIPTS_DIR,
    SCRIPT_CONFIG_FILENAME,
    SCRIPT_OBJECT_ID,
)

# add_type/remove_type now sync the add-expense helper script (Task 10),
# which calls the real script.reload service; startup does too.
pytestmark = pytest.mark.usefixtures("stub_script_reload")


async def _setup(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _script_type_options(hass):
    """Read the real script-sync YAML file and return its `type` options.

    Proves the script-sync wiring actually ran (wrote the file with the
    right content), not just that some function was called.
    """
    path = hass.config.path(SCRIPT_CONFIG_FILENAME)
    with open(path) as f:
        config = yaml.safe_load(f)
    return config[SCRIPT_OBJECT_ID]["fields"]["type"]["selector"]["select"]["options"]


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
    never leave an orphaned receipt file on disk."""
    await _setup(hass, tmp_path)

    fake_image = base64.b64encode(b"fake image bytes").decode()

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "add_expense",
            {
                "amount": 1.0,
                "type": "NotAType",
                "user": "person.armend",
                "receipt": f"data:image/jpg;base64,{fake_image}",
            },
            blocking=True,
        )

    receipts_root = os.path.join(str(tmp_path), RECEIPTS_DIR)
    if os.path.exists(receipts_root):
        assert os.listdir(receipts_root) == []


async def test_add_type_then_remove_type_service(hass, tmp_path):
    await _setup(hass, tmp_path)

    await hass.services.async_call(
        DOMAIN, "add_type", {"name": "Subscriptions", "icon": "mdi:credit-card"},
        blocking=True,
    )

    # Proves the add_type -> runtime._async_notify_types_changed ->
    # async_sync_script wiring actually fired (Task 10, Finding 2): the
    # real script-sync file on disk must now list the new type.
    assert "Subscriptions" in _script_type_options(hass)

    await hass.services.async_call(
        DOMAIN, "add_expense",
        {"amount": 9.99, "type": "Subscriptions", "user": "person.armend"},
        blocking=True,
    )

    await hass.services.async_call(
        DOMAIN, "remove_type", {"name": "Subscriptions"}, blocking=True
    )

    # Same wiring, other direction: removal must be reflected in the
    # script-sync file too.
    assert "Subscriptions" not in _script_type_options(hass)

    total = hass.states.get("sensor.expense_tracker_total")
    assert total.attributes["by_type"]["Subscriptions"] == 9.99  # history survives


async def test_remove_type_rejects_unknown_name(hass, tmp_path):
    await _setup(hass, tmp_path)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "remove_type", {"name": "Nonexistent"}, blocking=True
        )


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
