"""Constants for the Expense Tracker integration."""

DOMAIN = "expense_tracker"
DB_FILENAME = "expenses.db"
RECEIPTS_DIR = "www/expense_tracker/receipts"
SCRIPT_OBJECT_ID = "expense_tracker_add_expense"
SCRIPT_CONFIG_FILENAME = "expense_tracker_scripts.yaml"
SCHEMA_VERSION = 1

DEFAULT_TYPES = [
    ("Groceries", "mdi:cart"),
    ("Transport", "mdi:car"),
    ("Utilities", "mdi:flash"),
    ("Health", "mdi:medical-bag"),
    ("Entertainment", "mdi:movie"),
    ("Other", "mdi:dots-horizontal"),
]
