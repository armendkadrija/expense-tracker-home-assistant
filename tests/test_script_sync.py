import os
from unittest.mock import AsyncMock

import yaml

from custom_components.expense_tracker.const import SCRIPT_CONFIG_FILENAME, SCRIPT_OBJECT_ID
from custom_components.expense_tracker.script_sync import async_sync_script


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
