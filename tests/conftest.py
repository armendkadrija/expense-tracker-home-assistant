import pytest

from homeassistant.components.file_upload import _DATA, FileUploadData

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def stage_uploaded_file(hass, tmp_path):
    """Factory fixture: stage a fake uploaded file the same way
    file_upload's real HTTP upload view (FileUploadView.post) does -
    populate a FileUploadData in hass.data, make a per-file_id temp
    directory, write the bytes under the original filename - and return
    its file_id. Lets tests exercise the real
    homeassistant.components.file_upload.process_uploaded_file context
    manager end to end without driving the actual /api/file_upload
    aiohttp endpoint, which this harness has no clean way to call
    directly.
    """

    async def _stage(filename: str, content: bytes) -> str:
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

    return _stage
