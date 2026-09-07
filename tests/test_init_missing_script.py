"""Regression tests for I1: async_setup_entry must not leak
services/platforms when the `script` component isn't loaded.

Deliberately does NOT use the `stub_script_reload` fixture (unlike every
other test module) -- the whole point is to exercise the real failure
mode where `script.reload` is unregistered and calling it raises
ServiceNotFound, exactly as it does in a real HA instance where `script`
hasn't loaded yet (or the user never enabled it).
"""
import logging

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.expense_tracker.const import DOMAIN


async def test_setup_entry_survives_missing_script_component(hass, tmp_path, caplog):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    with caplog.at_level(logging.WARNING):
        assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state.value == "loaded"
    assert "script" in caplog.text.lower()


async def test_setup_entry_registers_services_despite_missing_script(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.services.has_service(DOMAIN, "add_expense")
    assert hass.services.has_service(DOMAIN, "add_type")
    assert hass.services.has_service(DOMAIN, "remove_type")
    assert hass.services.has_service(DOMAIN, "remove_expense")


async def test_setup_entry_forwards_platforms_despite_missing_script(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.expense_tracker_total") is not None
    assert hass.states.get("sensor.expense_tracker_total_this_month") is not None


async def test_add_expense_still_works_despite_missing_script(hass, tmp_path):
    """The data layer and services must keep working even though the
    dashboard form's script never got synced."""
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "add_expense",
        {"amount": 5.0, "type": "Groceries", "user": "person.armend"},
        blocking=True,
    )

    total = hass.states.get("sensor.expense_tracker_total")
    assert float(total.state) == 5.0
