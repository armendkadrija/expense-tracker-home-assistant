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

**The integration handles almost all of this automatically on setup:**
- It serves both files itself at `/expense_tracker_files/...`
  (`hass.http.async_register_static_paths`, a public HA API).
- It registers both as Lovelace resources automatically
  (`custom_components/expense_tracker/lovelace_setup.py`) — this reaches
  into `hass.data[LOVELACE_DATA].resources`, which is real and reachable
  (built on the public `homeassistant.helpers.collection` base class) but
  is the `lovelace` component's own internal data structure, not part of
  HA's versioned `homeassistant.helpers.*` contract — so this step is
  wrapped defensively and just logs a warning if it ever fails on some
  future HA version, rather than breaking setup.

**One thing it genuinely cannot do:** create the dashboard itself.
Verified directly against the source — the object that owns dashboard
*creation* (`DashboardsCollection`) is a local variable inside lovelace's
own `async_setup()` function; it's never stored anywhere reachable from
another integration's code. This isn't a risk trade-off like the resource
registration above, it's a hard wall. So, one-time manual step:

1. Settings → Dashboards → Add Dashboard → "New dashboard from scratch".
2. Edit → raw YAML editor, paste the contents of
   `dashboards/expense_tracker_dashboard.yaml`.

If you're working with Claude and it still has access to this Home
Assistant instance via the MCP connection, it can do this step for you
directly instead — that's how it was originally set up.

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
