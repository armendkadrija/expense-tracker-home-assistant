"""Runtime coordination layer: marshals ExpenseDB calls off the event
loop and pushes fresh state to sensors after every write."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from .db import ExpenseDB


class ExpenseTrackerRuntime:
    def __init__(self, hass: HomeAssistant, db: ExpenseDB) -> None:
        self.hass = hass
        self.db = db
        self.sensors: list = []

    async def async_initialize(self) -> None:
        await self.hass.async_add_executor_job(self.db.initialize)

    async def async_list_types(self) -> list[tuple[str, str]]:
        return await self.hass.async_add_executor_job(self.db.list_types)

    async def async_add_type(self, name: str, icon: str) -> None:
        await self.hass.async_add_executor_job(self.db.add_type, name, icon)
        await self.async_sync_script_now()
        # The sensors' `types` attribute is the live source other config
        # (e.g. a helper synced by an automation) reads the current type
        # list from -- it must update immediately, not just lag behind
        # until the next expense is logged.
        await self._async_refresh_sensors()

    async def async_remove_type(self, name: str) -> None:
        await self.hass.async_add_executor_job(self.db.remove_type, name)
        await self.async_sync_script_now()
        await self._async_refresh_sensors()

    async def async_add_expense(
        self,
        expense_id: str,
        amount: float,
        type_name: str,
        user: str,
        timestamp: str,
        receipt_path: str | None = None,
        note: str | None = None,
    ) -> None:
        await self.hass.async_add_executor_job(
            self.db.add_expense,
            expense_id,
            amount,
            type_name,
            user,
            timestamp,
            receipt_path,
            note,
        )
        await self._async_refresh_sensors()

    async def async_remove_expense(self, expense_id: str) -> str | None:
        receipt_path = await self.hass.async_add_executor_job(
            self.db.remove_expense, expense_id
        )
        await self._async_refresh_sensors()
        return receipt_path

    async def async_get_totals(self, since: str | None = None) -> dict:
        return await self.hass.async_add_executor_job(self.db.get_totals, since)

    async def _async_refresh_sensors(self) -> None:
        for sensor in self.sensors:
            await sensor.async_refresh()

    async def async_sync_script_now(self) -> None:
        """(Re)write the add-expense helper script's `type` field options
        to match the current expense_types list, and reload it via the
        `script` component. Shared by add_type/remove_type and the
        one-time startup sync in __init__.py -- callers that need setup
        to survive a missing `script` component (i.e. __init__.py) must
        catch homeassistant.exceptions.ServiceNotFound themselves; this
        method does not swallow it, since add_type/remove_type callers
        should see that failure."""
        from .script_sync import async_sync_script

        type_names = [name for name, _icon in await self.async_list_types()]
        await async_sync_script(self.hass, type_names)
