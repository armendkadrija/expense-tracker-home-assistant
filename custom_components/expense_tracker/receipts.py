"""Receipt file storage for the Expense Tracker integration.

Receipts arrive via the custom dashboard card's file upload (see
services.yaml), which hands the handler a `file_id` string referencing a
file the `file_upload` integration is holding in a temp directory — not a
base64 payload. `homeassistant.components.file_upload.process_uploaded_file`
is the public, documented way to get at that file's real path; it deletes
the temp file when its `with` block exits, so we must copy the bytes we
want to keep before the block ends. This mirrors the pattern used by HA's
own `local_calendar` config flow (`save_uploaded_ics_file`): the whole
`with process_uploaded_file(...)` block runs inside a single
`hass.async_add_executor_job` call, since `process_uploaded_file` itself
is a synchronous context manager and its exit does blocking file I/O.
"""
from __future__ import annotations

import os
import shutil

from homeassistant.components.file_upload import process_uploaded_file
from homeassistant.core import HomeAssistant

from .const import RECEIPTS_DIR


def _save_uploaded_receipt(
    hass: HomeAssistant, receipts_root: str, expense_id: str, file_id: str
) -> str:
    os.makedirs(receipts_root, exist_ok=True)
    with process_uploaded_file(hass, file_id) as file_path:
        ext = file_path.suffix.lstrip(".") or "jpg"
        filename = f"{expense_id}.{ext}"
        shutil.copyfile(file_path, os.path.join(receipts_root, filename))
    return f"{RECEIPTS_DIR}/{filename}"


def _delete_receipt_file(config_root: str, relative_path: str) -> None:
    config_root_real = os.path.realpath(config_root)
    full_path = os.path.realpath(os.path.join(config_root, relative_path))
    if os.path.commonpath([config_root_real, full_path]) != config_root_real:
        # relative_path escapes config_root (e.g. via "../"). Never
        # delete outside the config directory.
        return
    if os.path.exists(full_path):
        os.remove(full_path)


async def async_save_receipt(hass: HomeAssistant, expense_id: str, file_id: str) -> str:
    """Save the uploaded file referenced by `file_id` (the value produced
    by HA's `file` selector) as this expense's receipt, returning its path
    relative to the config directory."""
    receipts_root = hass.config.path(RECEIPTS_DIR)
    return await hass.async_add_executor_job(
        _save_uploaded_receipt, hass, receipts_root, expense_id, file_id
    )


async def async_delete_receipt(hass: HomeAssistant, relative_path: str) -> None:
    config_root = hass.config.path()
    await hass.async_add_executor_job(_delete_receipt_file, config_root, relative_path)
