import os

from homeassistant.components.file_upload import _DATA, FileUploadData

from custom_components.expense_tracker.receipts import (
    async_delete_receipt,
    async_save_receipt,
)


async def _stage_uploaded_file(hass, tmp_path, filename: str, content: bytes) -> str:
    """Stage a fake uploaded file the same way file_upload's real HTTP
    upload view (FileUploadView.post) does: create a FileUploadData (or
    reuse the existing one) in hass.data, make a per-file_id temp
    directory, and write the bytes under the original filename. This lets
    us exercise the real `process_uploaded_file` context manager end to
    end without spinning up the actual /api/file_upload aiohttp endpoint,
    which the test harness has no clean way to drive directly.
    """
    file_id = "fake-" + filename.replace(".", "-")

    def _create() -> None:
        upload_data = hass.data.get(_DATA)
        if upload_data is None:
            temp_dir = tmp_path / "file_upload_temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            upload_data = FileUploadData(temp_dir=temp_dir, files={})
            hass.data[_DATA] = upload_data
        file_dir = upload_data.file_dir(file_id)
        file_dir.mkdir(parents=True, exist_ok=True)
        (file_dir / filename).write_bytes(content)
        upload_data.files[file_id] = filename

    await hass.async_add_executor_job(_create)
    return file_id


async def test_save_receipt_copies_uploaded_file_and_derives_extension(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    image_bytes = b"fake-jpeg-bytes"
    file_id = await _stage_uploaded_file(hass, tmp_path, "receipt.jpeg", image_bytes)

    relative_path = await async_save_receipt(hass, "expense-1", file_id)

    assert relative_path == "www/expense_tracker/receipts/expense-1.jpeg"
    full_path = os.path.join(str(tmp_path), relative_path)
    with open(full_path, "rb") as f:
        assert f.read() == image_bytes


async def test_save_receipt_defaults_extension_when_filename_has_none(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    file_id = await _stage_uploaded_file(hass, tmp_path, "receipt", b"more-bytes")

    relative_path = await async_save_receipt(hass, "expense-2", file_id)

    assert relative_path == "www/expense_tracker/receipts/expense-2.jpg"


async def test_save_receipt_consumes_the_uploaded_temp_file(hass, tmp_path):
    """process_uploaded_file deletes the temp file/dir on context exit;
    confirm our copy survives after that cleanup runs."""
    hass.config.config_dir = str(tmp_path)
    file_id = await _stage_uploaded_file(hass, tmp_path, "receipt.png", b"png-bytes")
    upload_data = hass.data[_DATA]
    temp_file_dir = upload_data.file_dir(file_id)

    relative_path = await async_save_receipt(hass, "expense-3", file_id)

    assert not os.path.exists(temp_file_dir)
    full_path = os.path.join(str(tmp_path), relative_path)
    assert os.path.exists(full_path)


async def test_delete_receipt_removes_file(hass, tmp_path):
    hass.config.config_dir = str(tmp_path)
    file_id = await _stage_uploaded_file(hass, tmp_path, "r.jpg", b"x")
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
