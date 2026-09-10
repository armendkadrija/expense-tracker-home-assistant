# tests/test_sensor.py
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.util import dt as dt_util

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


async def test_sensors_have_monetary_device_class_and_precision(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    for entity_id in (
        "sensor.expense_tracker_total",
        "sensor.expense_tracker_total_this_month",
    ):
        state = hass.states.get(entity_id)
        assert state.attributes["device_class"] == SensorDeviceClass.MONETARY

    # suggested_display_precision only affects display/registry options,
    # not the raw state attributes dict - check it directly on the
    # entities the runtime is tracking.
    runtime = hass.data[DOMAIN][entry.entry_id]
    for sensor in runtime.sensors:
        assert sensor.suggested_display_precision == 2


async def test_month_sensor_sets_last_reset_to_start_of_month(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    month_state = hass.states.get("sensor.expense_tracker_total_this_month")
    last_reset = dt_util.parse_datetime(month_state.attributes["last_reset"])
    assert last_reset is not None

    local_now = dt_util.now()
    expected_local_start = local_now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    assert dt_util.as_local(last_reset) == expected_local_start


async def test_total_sensor_exposes_types_attribute(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    total = hass.states.get("sensor.expense_tracker_total")
    # A list of [name, icon] pairs in display order, not a dict -- see
    # sensor.py's async_refresh docstring for why (order must survive
    # HA's state-equality check for reorder_types to be observable here).
    types = dict(total.attributes["types"])
    assert types["Groceries"] == "mdi:cart"
    assert types["Transport"] == "mdi:car"
