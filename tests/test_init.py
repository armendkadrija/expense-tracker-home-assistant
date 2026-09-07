import os

import pytest
import yaml
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.expense_tracker.const import (
    DEFAULT_TYPES,
    DOMAIN,
    SCRIPT_CONFIG_FILENAME,
    SCRIPT_OBJECT_ID,
)

# async_setup_entry now syncs the add-expense helper script at startup
# (Task 10), which calls the real script.reload service.
pytestmark = pytest.mark.usefixtures("stub_script_reload")


async def test_setup_entry_creates_runtime_and_initializes_db(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    runtime = hass.data[DOMAIN][entry.entry_id]
    types = await runtime.async_list_types()
    assert len(types) == 6  # the seeded defaults


async def test_setup_entry_syncs_script_with_default_types_on_startup(hass, tmp_path):
    """Proves the one-time startup async_sync_script call in
    __init__.py actually ran (Task 10, Finding 2): the real script-sync
    file must exist on disk and list the seeded DEFAULT_TYPES."""
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    path = os.path.join(str(tmp_path), SCRIPT_CONFIG_FILENAME)
    assert os.path.exists(path)
    with open(path) as f:
        config = yaml.safe_load(f)
    options = config[SCRIPT_OBJECT_ID]["fields"]["type"]["selector"]["select"]["options"]
    # db.py's async_list_types is ORDER BY name, so options come back
    # alphabetically sorted rather than in DEFAULT_TYPES' seed order.
    assert options == sorted(name for name, _icon in DEFAULT_TYPES)


async def test_unload_entry_removes_runtime(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass.data.get(DOMAIN, {})
