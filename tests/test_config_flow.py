import pytest
from homeassistant import config_entries, data_entry_flow

from custom_components.expense_tracker.const import DOMAIN

# CREATE_ENTRY here drives a full config-entry setup (async_setup_entry),
# which now syncs the add-expense helper script at startup (Task 10) via
# the real script.reload service. Without this stub, ServiceNotFound is
# raised and silently swallowed by config-entries setup machinery.
pytestmark = pytest.mark.usefixtures("stub_script_reload")


async def test_user_flow_creates_single_entry(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Expense Tracker"


async def test_second_flow_aborts_single_instance(hass):
    await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    first = hass.config_entries.flow.async_progress()[0]
    await hass.config_entries.flow.async_configure(first["flow_id"], user_input={})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
