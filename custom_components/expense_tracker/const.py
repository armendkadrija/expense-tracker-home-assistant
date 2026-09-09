"""Constants for the Expense Tracker integration."""

DOMAIN = "expense_tracker"
DB_FILENAME = "expenses.db"
RECEIPTS_DIR = "www/expense_tracker/receipts"
SCRIPT_OBJECT_ID = "expense_tracker_add_expense"
SCRIPT_CONFIG_FILENAME = "expense_tracker_scripts.yaml"
SCHEMA_VERSION = 1

# Dashboard card JS, shipped by the integration and served via
# hass.http.async_register_static_paths (a verified public HA API --
# see __init__.py). Dashboard resource registration and the dashboard
# itself still need a one-time manual step: there is no equivalent public
# API for a custom integration to create Lovelace resources/dashboards
# from its own code, only the internal storage-collection objects the
# frontend/WebSocket API reach, which this project deliberately avoids
# poking (same reasoning as the script-sync mechanism).
STATIC_URL_PREFIX = "/expense_tracker_files"
CARD_FILES = ["expense-tracker-add-card.js", "expense-tracker-list-card.js"]

DEFAULT_TYPES = [
    ("Groceries", "mdi:cart"),
    ("Transport", "mdi:car"),
    ("Utilities", "mdi:flash"),
    ("Health", "mdi:medical-bag"),
    ("Entertainment", "mdi:movie"),
    ("Other", "mdi:dots-horizontal"),
]
