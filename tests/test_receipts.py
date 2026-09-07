import os

from homeassistant.components.file_upload import _DATA

from custom_components.expense_tracker.receipts import (
    async_delete_receipt,
    async_save_receipt,
)

# stage_uploaded_file is a shared fixture in conftest.py (also used by
# tests/test_services.py for the M4 orphaned-receipt regression test).


async def test_save_receipt_copies_uploaded_file_and_derives_extension(
    hass, tmp_path, stage_uploaded_file
):
    hass.config.config_dir = str(tmp_path)
    image_bytes = b"fake-jpeg-bytes"
    file_id = await stage_uploaded_file("receipt.jpeg", image_bytes)

    relative_path = await async_save_receipt(hass, "expense-1", file_id)

    assert relative_path == "www/expense_tracker/receipts/expense-1.jpeg"
    full_path = os.path.join(str(tmp_path), relative_path)
    with open(full_path, "rb") as f:
        assert f.read() == image_bytes


async def test_save_receipt_defaults_extension_when_filename_has_none(
    hass, tmp_path, stage_uploaded_file
):
    hass.config.config_dir = str(tmp_path)
    file_id = await stage_uploaded_file("receipt", b"more-bytes")

    relative_path = await async_save_receipt(hass, "expense-2", file_id)

    assert relative_path == "www/expense_tracker/receipts/expense-2.jpg"


async def test_save_receipt_consumes_the_uploaded_temp_file(
    hass, tmp_path, stage_uploaded_file
):
    """process_uploaded_file deletes the temp file/dir on context exit;
    confirm our copy survives after that cleanup runs."""
    hass.config.config_dir = str(tmp_path)
    file_id = await stage_uploaded_file("receipt.png", b"png-bytes")
    upload_data = hass.data[_DATA]
    temp_file_dir = upload_data.file_dir(file_id)

    relative_path = await async_save_receipt(hass, "expense-3", file_id)

    assert not os.path.exists(temp_file_dir)
    full_path = os.path.join(str(tmp_path), relative_path)
    assert os.path.exists(full_path)


async def test_delete_receipt_removes_file(hass, tmp_path, stage_uploaded_file):
    hass.config.config_dir = str(tmp_path)
    file_id = await stage_uploaded_file("r.jpg", b"x")
    relative_path = await async_save_receipt(hass, "expense-4", file_id)
    full_path = os.path.join(str(tmp_path), relative_path)
    assert os.path.exists(full_path)

    await async_delete_receipt(hass, relative_path)

    assert not os.path.exists(full_path)


async def test_delete_receipt_missing_file_is_a_noop(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)

    await async_delete_receipt(hass, "www/expense_tracker/receipts/nope.jpg")


async def test_delete_receipt_refuses_path_outside_config_root(hass, tmp_path):
    """_delete_receipt_file must not follow a relative_path that escapes
    config_root via '../' segments."""
    hass.config.config_dir = str(tmp_path)
    outside_file = tmp_path.parent / "outside-secret.txt"
    outside_file.write_text("do not delete me")

    escaping_relative_path = os.path.join("..", outside_file.name)
    await async_delete_receipt(hass, escaping_relative_path)

    assert outside_file.exists()
