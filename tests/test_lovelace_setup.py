from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.setup import async_setup_component

from custom_components.expense_tracker.const import (
    CARD_FILES,
    DOMAIN,
    STATIC_URL_PREFIX,
)


async def test_setup_entry_registers_dashboard_resources_when_lovelace_loaded(
    hass, tmp_path
):
    assert await async_setup_component(hass, "lovelace", {})
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    urls = {
        item.get("url")
        for item in hass.data[LOVELACE_DATA].resources.async_items()
    }
    for name in CARD_FILES:
        assert f"{STATIC_URL_PREFIX}/{name}" in urls


async def test_registering_resources_twice_does_not_duplicate(hass, tmp_path):
    assert await async_setup_component(hass, "lovelace", {})
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    from custom_components.expense_tracker.lovelace_setup import (
        async_register_dashboard_resources,
    )

    await async_register_dashboard_resources(hass)
    await async_register_dashboard_resources(hass)

    urls = [
        item.get("url")
        for item in hass.data[LOVELACE_DATA].resources.async_items()
        if item.get("url", "").startswith(STATIC_URL_PREFIX)
    ]
    assert len(urls) == len(CARD_FILES)


async def test_setup_entry_survives_lovelace_not_loaded(hass, tmp_path):
    """lovelace isn't set up at all in this test -- setup must not raise."""
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state.value == "loaded"
