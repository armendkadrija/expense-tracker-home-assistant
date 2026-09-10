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

The UI lives in a dedicated 4-tab dashboard (Add / All Expenses / Stats /
Types) built from three custom cards this integration ships:
`www/expense-tracker-add-card.js`, `www/expense-tracker-list-card.js`, and
`www/expense-tracker-types-card.js`.

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
- Each resource URL carries `?v=<integration version>`. The static files
  are served with a 31-day `Cache-Control`, and on a deployment that sits
  behind a CDN (verified against this project's own instance, Cloudflare)
  that header gets honored at the edge — a bare URL can keep serving a
  stale card file for up to a month after an update, hard browser refresh
  or not. Bumping the version changes the URL, which is what actually
  invalidates it, and setup updates the existing resource entry in place
  on every restart so this stays automatic. This version is read straight
  from `manifest.json` on disk on every call, deliberately not through
  `homeassistant.loader`'s `async_get_integration` — that caches the
  parsed manifest for the life of the HA process, so a config-entry
  reload (rather than a full restart) would keep reporting the old
  version and never actually bust the cache.

**A Python code change always needs a full Home Assistant restart** —
Python caches an already-imported module for the life of the process, so
re-running setup via a config-entry reload executes the *old* code, not
whatever HACS just wrote to disk. A JS-only release (a card file plus a
manifest version bump, no `.py` changes) is different: `Settings → Devices
& Services → Expense Tracker → ⋯ → Reload` is enough, since the version
lookup above re-reads `manifest.json` fresh every time rather than relying
on anything cached.

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

The "Types" tab lists every type with an icon and a usage count, a form
to add new ones, and a delete button per row. Types ship seeded with
Groceries, Transport, Utilities, Health, Entertainment, Other. The icon
field is HA's own `ha-icon-picker` — full search over the MDI set, same
widget the native UI uses for icon selectors — with a raw `mdi:...` string
still accepted as a fallback.

**Order is drag-and-drop, via the grip handle on each row.** It persists
server-side (`expense_tracker.reorder_types`) and is the same order the
Add-expense tab's type picker uses — dragging in one place changes both,
immediately, no separate sync step. Reordering uses touch-compatible
Pointer Events rather than the HTML5 Drag-and-Drop API, which has no
touch support on iOS/Android and would otherwise silently not work from
a phone.

**A type in use can't be deleted — enforced server-side, not just hidden
in the UI.** `expense_tracker.remove_type` checks for any expense still
referencing that type name and refuses with a clear error if one exists
(`db.py`'s `TypeInUseError`); the card disables the delete button for
in-use types for the same reason, but the backend check is what actually
matters — calling the service directly (Developer Tools, an automation)
gets the same refusal. Remove or re-type the referencing expenses first
if you need to retire a type.

The dashboard's type picker (and the "By type" stats breakdown) update
automatically wherever types are used — no separate sync step.

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
