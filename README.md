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
as its own top-level key in `configuration.yaml`, alongside (not nested
inside) any existing `script:` key you may already have:

```yaml
script expense_tracker: !include expense_tracker_scripts.yaml
```

HA merges multiple differently-suffixed `script <label>:` top-level keys
together (the same mechanism `automation ui:` / `automation manual:` use),
so this line lives next to — never inside — your own `script:` block.

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

## A note on receipt privacy

Receipt images are served from `/local/expense_tracker/receipts/...` like
any other file under `www/` — with no authentication. Filenames are the
expense's uuid4 id, so they aren't guessable, and this isn't currently
exploitable in practice. Still worth knowing since this integration
stores financial records: anyone who obtains a receipt's exact URL (e.g.
via a shared link, browser history, or a proxy log) can view it without
logging in.
