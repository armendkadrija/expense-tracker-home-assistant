from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.expense_tracker.const import DOMAIN


async def test_setup_entry_creates_runtime_and_initializes_db(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    runtime = hass.data[DOMAIN][entry.entry_id]
    types = await runtime.async_list_types()
    assert len(types) == 6  # the seeded defaults


async def test_setup_entry_serves_card_js_files(hass, hass_client, tmp_path):
    """The card JS files must be reachable over real HTTP at the
    documented static path, and a reload must not error on double
    static-path registration."""
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "http", {})
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    client = await hass_client()
    resp = await client.get("/expense_tracker_files/expense-tracker-add-card.js")
    assert resp.status == 200
    body = await resp.text()
    assert "customElements.define(\"expense-tracker-add-card\"" in body

    resp = await client.get("/expense_tracker_files/expense-tracker-list-card.js")
    assert resp.status == 200

    # Reload the entry to prove the static-path registration guard
    # doesn't raise on a second async_setup_entry call.
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_unload_entry_removes_runtime(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass.data.get(DOMAIN, {})
