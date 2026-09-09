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
from .dt_helpers import local_date_string_to_utc_iso
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
        # Optional: the dashboard script no longer asks for this — it's
        # resolved from whoever is actually running the script (see
        # _resolve_user_from_context). Still overridable by direct service
        # calls (Developer Tools, automations) that want to log on someone
        # else's behalf.
        vol.Optional("user"): vol.Any(None, cv.entity_id),
        # The script wrapper's sequence renders blank optional fields as a
        # real Jinja/Python None (e.g. "{{ date | default(None) }}"), not
        # an omitted key. cv.string rejects None outright, so these must
        # explicitly allow it.
        vol.Optional("date"): vol.Any(None, cv.string),
        vol.Optional("receipt"): vol.Any(None, cv.string),
        vol.Optional("note"): vol.Any(None, cv.string),
    }
)
ADD_TYPE_SCHEMA = vol.Schema(
    {vol.Required("name"): cv.string, vol.Required("icon"): cv.icon}
)
REMOVE_TYPE_SCHEMA = vol.Schema({vol.Required("name"): cv.string})
REMOVE_EXPENSE_SCHEMA = vol.Schema({vol.Required("id"): cv.string})


def _resolve_user_from_context(hass: HomeAssistant, user_id: str | None) -> str | None:
    """Map the HA user who triggered this call to their linked person
    entity. `person` entities expose the HA account they're linked to as
    a `user_id` state attribute (homeassistant/components/person -
    PersonEntity._update_attributes, verified against the installed
    source) whenever that person was set up with a login. Returns None
    if there's no calling user (e.g. a context-less internal call) or no
    person is linked to that account."""
    if user_id is None:
        return None
    for state in hass.states.async_all("person"):
        if state.attributes.get("user_id") == user_id:
            return state.entity_id
    return None


def async_register_services(hass: HomeAssistant, runtime: ExpenseTrackerRuntime) -> None:
    async def handle_add_expense(call: ServiceCall) -> None:
        expense_id = str(uuid.uuid4())
        raw_date = call.data.get("date")
        if raw_date:
            # The `date` selector hands us a bare "YYYY-MM-DD" string with
            # no time/timezone. Normalize it to a full UTC ISO timestamp
            # so it sorts and compares correctly against the full ISO
            # timestamps used for undated expenses (db.get_totals does a
            # plain string >= comparison against `since`).
            timestamp = local_date_string_to_utc_iso(raw_date)
        else:
            timestamp = datetime.now(timezone.utc).isoformat()

        # Validate the type BEFORE touching the receipt file. Saving the
        # receipt first would leave an orphaned file on disk if the type
        # turns out to be invalid, since nothing would reference it.
        type_name = call.data["type"]
        existing_types = await runtime.async_list_types()
        if type_name not in [name for name, _icon in existing_types]:
            raise ServiceValidationError(f"Unknown expense type: {type_name}")

        user = call.data.get("user")
        if not user:
            user = _resolve_user_from_context(hass, call.context.user_id)
            if user is None:
                raise ServiceValidationError(
                    "Could not determine who this expense belongs to: no "
                    "person is linked to your Home Assistant user account. "
                    "Pass `user` explicitly (e.g. person.jane) to fix this, "
                    "or link your account under Settings > People."
                )

        receipt_path = None
        if call.data.get("receipt"):
            receipt_path = await async_save_receipt(
                hass, expense_id, call.data["receipt"]
            )
        try:
            try:
                await runtime.async_add_expense(
                    expense_id=expense_id,
                    amount=call.data["amount"],
                    type_name=type_name,
                    user=user,
                    timestamp=timestamp,
                    receipt_path=receipt_path,
                    note=call.data.get("note"),
                )
            except UnknownTypeError as err:
                # Defensive fallback only: the membership check above
                # already guards against this, but async_add_expense
                # re-validates on its own so it stays correct if ever
                # called from elsewhere.
                raise ServiceValidationError(str(err)) from err
        except Exception:
            # If the DB write fails for ANY reason (not just the
            # UnknownTypeError case above) after a receipt was already
            # saved, that file would otherwise orphan on disk with
            # nothing ever pointing at it. Clean it up, then let
            # whatever error resulted keep propagating unchanged.
            if receipt_path:
                await async_delete_receipt(hass, receipt_path)
            raise

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
