"""Config flow for the Expense Tracker integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN


class ExpenseTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured(error="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title="Expense Tracker", data={})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
