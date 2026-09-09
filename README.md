# Expense Tracker for Home Assistant

Private, personal-use custom integration for tracking household expenses:
amount, type, who spent it, optional receipt photo — plus a real custom
dashboard UI (not just the native auto-generated form). See
`docs/superpowers/specs/2026-09-07-expense-tracker-design.md` in the
home-assistant repo for the original design rationale.

## Install

1. HACS → Custom repositories → add this repo's URL, category "Integration".
2. Install "Expense Tracker" from HACS, restart Home Assistant.
3. Settings → Devices & Services → Add Integration → "Expense Tracker"
   (no configuration needed).

## Dashboard setup

The UI lives in a dedicated 3-tab dashboard (Add / All Expenses / Stats)
built from two custom cards this integration ships:
`www/expense-tracker-add-card.js` and `www/expense-tracker-list-card.js`.
The integration serves both files itself at `/expense_tracker_files/...`
(verified via `hass.http.async_register_static_paths`, a public HA API) —
but registering them as Lovelace *resources*, and creating the dashboard
itself, has no equivalent public API for a custom integration to do from
its own code. Only the frontend's internal storage objects reach that far,
which this project deliberately avoids poking. So this part is a one-time
manual step — the *only* one; there is no `configuration.yaml` editing
required at all:

1. Settings → Dashboards → Resources → Add Resource, twice:
   - URL: `/expense_tracker_files/expense-tracker-add-card.js`, type: JavaScript Module
   - URL: `/expense_tracker_files/expense-tracker-list-card.js`, type: JavaScript Module
2. Create a new dashboard (Settings → Dashboards → Add Dashboard → "New
   dashboard from scratch"), then Edit → raw YAML editor, and paste the
   contents of `dashboards/expense_tracker_dashboard.yaml`.

If you're working with Claude and it still has access to this Home
Assistant instance via the MCP connection, it can do both of these steps
for you directly instead — that's how they were originally set up.

## Managing expense types

Types ship seeded with Groceries, Transport, Utilities, Health,
Entertainment, Other. Add or remove your own from the Stats tab isn't
built in yet — use Developer Tools → Actions:

- `expense_tracker.add_type` — `name`, `icon` (mdi icon string)
- `expense_tracker.remove_type` — `name` (existing expenses keep their
  historical type name even after it's removed)

The dashboard's type picker (and the "By type" stats breakdown) update
automatically — no separate sync step.

## Fixing a mistake

Delete an expense straight from the "Add" or "All Expenses" tab (trash
icon on each row) — this calls `expense_tracker.remove_expense`, which
also deletes its receipt file if it had one.

## A note on receipt privacy

Receipt images are served from `/local/expense_tracker/receipts/...` like
any other file under `www/` — with no authentication. Filenames are the
expense's uuid4 id, so they aren't guessable, and this isn't currently
exploitable in practice. Still worth knowing since this integration
stores financial records: anyone who obtains a receipt's exact URL (e.g.
via a shared link, browser history, or a proxy log) can view it without
logging in.
