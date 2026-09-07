import base64
import os

from custom_components.expense_tracker.receipts import (
    async_delete_receipt,
    async_save_receipt,
)


async def test_save_receipt_decodes_data_url_and_writes_file(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    image_bytes = b"fake-jpeg-bytes"
    data_url = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode()

    relative_path = await async_save_receipt(hass, "expense-1", data_url)

    assert relative_path == "www/expense_tracker/receipts/expense-1.jpeg"
    full_path = os.path.join(str(tmp_path), relative_path)
    with open(full_path, "rb") as f:
        assert f.read() == image_bytes


async def test_save_receipt_handles_bare_base64(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    image_bytes = b"more-bytes"
    encoded = base64.b64encode(image_bytes).decode()

    relative_path = await async_save_receipt(hass, "expense-2", encoded)

    assert relative_path == "www/expense_tracker/receipts/expense-2.jpg"


async def test_delete_receipt_removes_file(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    relative_path = await async_save_receipt(
        hass, "expense-3", base64.b64encode(b"x").decode()
    )
    full_path = os.path.join(str(tmp_path), relative_path)
    assert os.path.exists(full_path)

    await async_delete_receipt(hass, relative_path)

    assert not os.path.exists(full_path)


async def test_delete_receipt_missing_file_is_a_noop(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)

    await async_delete_receipt(hass, "www/expense_tracker/receipts/nope.jpg")
