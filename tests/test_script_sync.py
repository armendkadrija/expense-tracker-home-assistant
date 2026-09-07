import os
from unittest.mock import AsyncMock

import yaml

from homeassistant.components.script.config import SCRIPT_ENTITY_SCHEMA

from custom_components.expense_tracker.const import SCRIPT_CONFIG_FILENAME, SCRIPT_OBJECT_ID
from custom_components.expense_tracker.script_sync import (
    _build_script_config,
    async_sync_script,
)


async def test_sync_script_writes_valid_yaml_with_current_types(hass, tmp_path, monkeypatch):
    hass.config.config_dir = str(tmp_path)
    monkeypatch.setattr(type(hass.services), "async_call", AsyncMock())

    await async_sync_script(hass, ["Groceries", "Transport"])

    path = os.path.join(str(tmp_path), SCRIPT_CONFIG_FILENAME)
    with open(path) as f:
        config = yaml.safe_load(f)

    script_def = config[SCRIPT_OBJECT_ID]
    assert script_def["fields"]["type"]["selector"]["select"]["options"] == [
        "Groceries",
        "Transport",
    ]
    assert script_def["sequence"][0]["action"] == "expense_tracker.add_expense"


async def test_sync_script_calls_script_reload(hass, tmp_path, monkeypatch):
    hass.config.config_dir = str(tmp_path)
    monkeypatch.setattr(type(hass.services), "async_call", AsyncMock())

    await async_sync_script(hass, ["Groceries"])

    hass.services.async_call.assert_awaited_once_with(
        "script", "reload", blocking=True
    )


async def test_sync_script_overwrites_previous_options(hass, tmp_path, monkeypatch):
    hass.config.config_dir = str(tmp_path)
    monkeypatch.setattr(type(hass.services), "async_call", AsyncMock())
    await async_sync_script(hass, ["Groceries"])

    await async_sync_script(hass, ["Groceries", "Subscriptions"])

    path = os.path.join(str(tmp_path), SCRIPT_CONFIG_FILENAME)
    with open(path) as f:
        config = yaml.safe_load(f)
    options = config[SCRIPT_OBJECT_ID]["fields"]["type"]["selector"]["select"]["options"]
    assert options == ["Groceries", "Subscriptions"]


def test_build_script_config_validates_against_real_script_schema():
    """The single most important test in this fix wave: the generated
    script config must pass Home Assistant's REAL SCRIPT_ENTITY_SCHEMA
    validator, not just "look right". This is what would have caught the
    `image` selector (which does not exist in HA) before it ever shipped.
    """
    config = _build_script_config(["Groceries", "Transport"])

    # SCRIPT_ENTITY_SCHEMA validates one script's inner config (the value
    # under its object_id key), not the outer {object_id: {...}} mapping.
    SCRIPT_ENTITY_SCHEMA(config[SCRIPT_OBJECT_ID])
