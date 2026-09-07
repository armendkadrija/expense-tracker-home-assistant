"""Service (action) handlers for the Expense Tracker integration."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .db import DuplicateTypeError, UnknownExpenseError, UnknownTypeError
from .receipts import async_delete_receipt, async_save_receipt
from .runtime import ExpenseTrackerRuntime

SERVICE_ADD_EXPENSE = "add_expense"
SERVICE_ADD_TYPE = "add_type"
SERVICE_REMOVE_TYPE = "remove_type"
SERVICE_REMOVE_EXPENSE = "remove_expense"

ADD_EXPENSE_SCHEMA = vol.Schema(
    {
        vol.Required("amount"): vol.All(vol.Coerce(float), vol.Range(min=0)),
        vol.Required("type"): cv.string,
        vol.Required("user"): cv.entity_id,
        vol.Optional("date"): cv.string,
        vol.Optional("receipt"): cv.string,
        vol.Optional("note"): cv.string,
    }
)
ADD_TYPE_SCHEMA = vol.Schema(
    {vol.Required("name"): cv.string, vol.Required("icon"): cv.icon}
)
REMOVE_TYPE_SCHEMA = vol.Schema({vol.Required("name"): cv.string})
REMOVE_EXPENSE_SCHEMA = vol.Schema({vol.Required("id"): cv.string})


def async_register_services(hass: HomeAssistant, runtime: ExpenseTrackerRuntime) -> None:
    async def handle_add_expense(call: ServiceCall) -> None:
        expense_id = str(uuid.uuid4())
        timestamp = call.data.get("date") or datetime.now(timezone.utc).isoformat()

        # Validate the type BEFORE touching the receipt file. Saving the
        # receipt first would leave an orphaned file on disk if the type
        # turns out to be invalid, since nothing would reference it.
        type_name = call.data["type"]
        existing_types = await runtime.async_list_types()
        if type_name not in [name for name, _icon in existing_types]:
            raise ServiceValidationError(f"Unknown expense type: {type_name}")

        receipt_path = None
        if call.data.get("receipt"):
            receipt_path = await async_save_receipt(
                hass, expense_id, call.data["receipt"]
            )
        try:
            await runtime.async_add_expense(
                expense_id=expense_id,
                amount=call.data["amount"],
                type_name=type_name,
                user=call.data["user"],
                timestamp=timestamp,
                receipt_path=receipt_path,
                note=call.data.get("note"),
            )
        except UnknownTypeError as err:
            # Defensive fallback only: the membership check above already
            # guards against this, but async_add_expense re-validates on
            # its own so it stays correct if ever called from elsewhere.
            raise ServiceValidationError(str(err)) from err

    async def handle_add_type(call: ServiceCall) -> None:
        try:
            await runtime.async_add_type(call.data["name"], call.data["icon"])
        except DuplicateTypeError as err:
            raise ServiceValidationError(str(err)) from err

    async def handle_remove_type(call: ServiceCall) -> None:
        try:
            await runtime.async_remove_type(call.data["name"])
        except UnknownTypeError as err:
            raise ServiceValidationError(str(err)) from err

    async def handle_remove_expense(call: ServiceCall) -> None:
        try:
            receipt_path = await runtime.async_remove_expense(call.data["id"])
        except UnknownExpenseError as err:
            raise ServiceValidationError(str(err)) from err
        if receipt_path:
            await async_delete_receipt(hass, receipt_path)

    hass.services.async_register(
        DOMAIN, SERVICE_ADD_EXPENSE, handle_add_expense, schema=ADD_EXPENSE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_TYPE, handle_add_type, schema=ADD_TYPE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_TYPE, handle_remove_type, schema=REMOVE_TYPE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_EXPENSE,
        handle_remove_expense,
        schema=REMOVE_EXPENSE_SCHEMA,
    )


def async_unregister_services(hass: HomeAssistant) -> None:
    for service in (
        SERVICE_ADD_EXPENSE,
        SERVICE_ADD_TYPE,
        SERVICE_REMOVE_TYPE,
        SERVICE_REMOVE_EXPENSE,
    ):
        hass.services.async_remove(DOMAIN, service)
