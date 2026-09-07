# Expense Tracker for Home Assistant

Private, personal-use custom integration for tracking household expenses:
amount, type, who spent it, optional receipt photo. See
`docs/superpowers/specs/2026-09-07-expense-tracker-design.md` in the
home-assistant repo for the full design rationale.

## Install

1. HACS → Custom repositories → add this repo's URL, category "Integration".
2. Install "Expense Tracker" from HACS, restart Home Assistant.
3. Settings → Devices & Services → Add Integration → "Expense Tracker"
   (no configuration needed).

## One-time setup: wire in the entry-form script

The integration maintains a dedicated script config file so the "Add
expense" dashboard form always shows your current expense types. Add this
line under a `script` key in `configuration.yaml`:

```yaml
script expense_tracker: !include expense_tracker_scripts.yaml
```

Restart Home Assistant once after adding this line.

## Dashboard

Copy the contents of `dashboards/expense_tracker_view.yaml` into a new
Lovelace view (Edit Dashboard → Add View → raw YAML editor).

## Managing expense types

Types ship seeded with Groceries, Transport, Utilities, Health,
Entertainment, Other. Add or remove your own from Developer Tools →
Actions:

- `expense_tracker.add_type` — `name`, `icon` (mdi icon string)
- `expense_tracker.remove_type` — `name` (existing expenses keep their
  historical type name even after it's removed)

## Fixing a mistake

`expense_tracker.remove_expense` with the expense's `id` deletes the row
and its receipt file. Find the `id` via the SQLite file directly:
`<config>/expense_tracker/expenses.db`.
