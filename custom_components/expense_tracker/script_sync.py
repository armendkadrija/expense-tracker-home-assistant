"""Keeps the expense_tracker_add_expense helper script's `type` field
options in sync with the current list of expense types.

The integration owns SCRIPT_CONFIG_FILENAME exclusively — it never reads
or writes the user's own scripts.yaml, and never reaches into the script
component's internal storage objects. It only rewrites its own file and
calls the public script.reload service.
"""
from __future__ import annotations

import os

import yaml

from homeassistant.core import HomeAssistant

from .const import SCRIPT_CONFIG_FILENAME, SCRIPT_OBJECT_ID


def _build_script_config(type_names: list[str]) -> dict:
    return {
        SCRIPT_OBJECT_ID: {
            "alias": "Add expense",
            "fields": {
                "type": {
                    "required": True,
                    "selector": {"select": {"options": type_names}},
                },
                "amount": {
                    "required": True,
                    "selector": {"number": {"min": 0, "mode": "box"}},
                },
                "user": {
                    "required": True,
                    "selector": {"entity": {"domain": "person"}},
                },
                "date": {"required": False, "selector": {"date": {}}},
                "receipt": {"required": False, "selector": {"image": {}}},
                "note": {"required": False, "selector": {"text": {}}},
            },
            "sequence": [
                {
                    "action": "expense_tracker.add_expense",
                    "data": {
                        "amount": "{{ amount }}",
                        "type": "{{ type }}",
                        "user": "{{ user }}",
                        "date": "{{ date | default(None) }}",
                        "receipt": "{{ receipt | default(None) }}",
                        "note": "{{ note | default(None) }}",
                    },
                }
            ],
        }
    }


def _write_script_file(path: str, config: dict) -> None:
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
    os.replace(tmp_path, path)


async def async_sync_script(hass: HomeAssistant, type_names: list[str]) -> None:
    path = hass.config.path(SCRIPT_CONFIG_FILENAME)
    config = _build_script_config(type_names)
    await hass.async_add_executor_job(_write_script_file, path, config)
    await hass.services.async_call("script", "reload", blocking=True)
