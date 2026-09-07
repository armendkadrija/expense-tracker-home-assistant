# tests/test_sensor.py
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.expense_tracker.const import DOMAIN


async def test_sensors_start_at_zero_with_seeded_types(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    total = hass.states.get("sensor.expense_tracker_total")
    month = hass.states.get("sensor.expense_tracker_total_this_month")

    assert total.state == "0"
    assert total.attributes["count"] == 0
    assert month.state == "0"


async def test_sensor_updates_after_add_expense(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    runtime = hass.data[DOMAIN][entry.entry_id]
    await runtime.async_add_expense(
        expense_id="id-1",
        amount=9.5,
        type_name="Groceries",
        user="person.armend",
        timestamp="2026-09-07T10:00:00+00:00",
    )
    await hass.async_block_till_done()

    total = hass.states.get("sensor.expense_tracker_total")
    assert float(total.state) == 9.5
    assert total.attributes["by_type"] == {"Groceries": 9.5}
