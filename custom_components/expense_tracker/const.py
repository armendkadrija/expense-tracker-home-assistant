"""Constants for the Expense Tracker integration."""

DOMAIN = "expense_tracker"
DB_FILENAME = "expenses.db"
RECEIPTS_DIR = "www/expense_tracker/receipts"
SCHEMA_VERSION = 1

# Dashboard card JS, shipped by the integration and served via
# hass.http.async_register_static_paths (see __init__.py), then
# auto-registered as Lovelace resources (see lovelace_setup.py). Creating
# the dashboard *itself* is the one thing that stays a manual step -- see
# lovelace_setup.py's docstring for exactly why.
STATIC_URL_PREFIX = "/expense_tracker_files"
CARD_FILES = [
    "expense-tracker-add-card.js",
    "expense-tracker-list-card.js",
    "expense-tracker-types-card.js",
]

DEFAULT_TYPES = [
    ("Groceries", "mdi:cart"),
    ("Transport", "mdi:car"),
    ("Utilities", "mdi:flash"),
    ("Health", "mdi:medical-bag"),
    ("Entertainment", "mdi:movie"),
    ("Other", "mdi:dots-horizontal"),
]
