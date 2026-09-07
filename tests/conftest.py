import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def stub_script_reload(hass):
    """Stand in for the `script` component's `script.reload` service.

    expense_tracker's script_sync module calls the public, documented
    `script.reload` service on every add_type/remove_type call and once
    at startup, to pick up its freshly rewritten
    expense_tracker_scripts.yaml. The `script` component itself is not
    loaded in this test harness, so any test that exercises a full
    config entry setup (or add_type/remove_type) needs this stub
    registered or the call raises ServiceNotFound. Opt a test module in
    with `pytestmark = pytest.mark.usefixtures("stub_script_reload")`.
    """

    async def _noop(call):
        return None

    hass.services.async_register("script", "reload", _noop)
