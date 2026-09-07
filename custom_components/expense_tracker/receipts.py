"""Receipt file storage for the Expense Tracker integration."""
from __future__ import annotations

import base64
import os

from homeassistant.core import HomeAssistant

from .const import RECEIPTS_DIR


def _write_receipt_file(
    receipts_root: str, expense_id: str, image_bytes: bytes, ext: str
) -> str:
    os.makedirs(receipts_root, exist_ok=True)
    filename = f"{expense_id}.{ext}"
    with open(os.path.join(receipts_root, filename), "wb") as f:
        f.write(image_bytes)
    return f"{RECEIPTS_DIR}/{filename}"


def _delete_receipt_file(config_root: str, relative_path: str) -> None:
    full_path = os.path.join(config_root, relative_path)
    if os.path.exists(full_path):
        os.remove(full_path)


async def async_save_receipt(
    hass: HomeAssistant, expense_id: str, image_data_url: str
) -> str:
    """image_data_url is the raw value from HA's `image` selector: a
    base64 string, optionally prefixed 'data:image/<ext>;base64,'."""
    if image_data_url.startswith("data:") and "," in image_data_url:
        header, encoded = image_data_url.split(",", 1)
        ext = header.split("/")[1].split(";")[0] if "/" in header else "jpg"
    else:
        encoded = image_data_url
        ext = "jpg"
    image_bytes = base64.b64decode(encoded)
    receipts_root = hass.config.path(RECEIPTS_DIR)
    return await hass.async_add_executor_job(
        _write_receipt_file, receipts_root, expense_id, image_bytes, ext
    )


async def async_delete_receipt(hass: HomeAssistant, relative_path: str) -> None:
    config_root = hass.config.path()
    await hass.async_add_executor_job(_delete_receipt_file, config_root, relative_path)
