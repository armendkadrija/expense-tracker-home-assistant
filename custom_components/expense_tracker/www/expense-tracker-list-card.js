/**
 * expense-tracker-list-card
 *
 * Renders individual expense rows (icon, type, date, note, amount,
 * receipt link, delete) by calling the read-only expense_tracker.list_expenses
 * service over the WebSocket connection with return_response: true --
 * the exact message shape (type/domain/service/service_data/return_response)
 * verified directly against homeassistant/components/websocket_api/commands.py's
 * handle_call_service schema, not guessed.
 *
 * Config:
 *   limit: number (optional) -- max rows to show. Omit for "all".
 *   show_more_path: string (optional) -- if set (and limit is set), a
 *     "Show all" button navigates here via HA's SPA history mechanism.
 *   title: string (optional) -- card header, defaults to "Expenses".
 */
class ExpenseTrackerListCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._render();
      this._fetch();
    } else {
      this._maybeRefetch();
    }
  }

  getCardSize() {
    return this._config.limit ? Math.min(this._config.limit, 5) + 1 : 6;
  }

  _maybeRefetch() {
    const state = this._hass.states["sensor.expense_tracker_total"];
    const key = state ? `${state.state}:${state.attributes.count}` : null;
    if (key !== this._watchKey) {
      this._watchKey = key;
      this._fetch();
    }
  }

  async _fetch() {
    const data = {};
    if (this._config.limit) data.limit = this._config.limit;
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "call_service",
        domain: "expense_tracker",
        service: "list_expenses",
        service_data: data,
        return_response: true,
      });
      this._expenses = (result.response && result.response.expenses) || [];
      this._renderRows();
    } catch (err) {
      this._el.rows.innerHTML = `<div class="empty">Couldn't load expenses: ${
        (err && err.message) || err
      }</div>`;
    }
  }

  _render() {
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `
      <style>
        ha-card { padding: 8px 0 16px; }
        .rows { display: flex; flex-direction: column; }
        .row {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 16px;
          border-bottom: 1px solid var(--divider-color);
        }
        .row:last-child { border-bottom: none; }
        .row ha-icon.type-icon { color: var(--secondary-text-color); flex-shrink: 0; }
        .info { flex: 1; min-width: 0; }
        .type-line {
          display: flex;
          justify-content: space-between;
          gap: 8px;
          font-size: 14px;
          color: var(--primary-text-color);
        }
        .type-line .date { color: var(--secondary-text-color); font-size: 12px; }
        .note {
          font-size: 12px;
          color: var(--secondary-text-color);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .amount {
          font-size: 15px;
          font-weight: 500;
          color: var(--primary-text-color);
          flex-shrink: 0;
        }
        .receipt-link, .delete {
          flex-shrink: 0;
          color: var(--secondary-text-color);
          background: none;
          border: none;
          cursor: pointer;
          display: flex;
        }
        .delete:hover { color: var(--error-color, #db4437); }
        .empty {
          padding: 20px 16px;
          text-align: center;
          color: var(--secondary-text-color);
          font-size: 14px;
        }
        .show-more {
          display: block;
          width: calc(100% - 32px);
          margin: 12px 16px 0;
          padding: 10px;
          font-size: 14px;
          color: var(--primary-color);
          background: none;
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 8px);
          cursor: pointer;
        }
      </style>
      <ha-card header="${this._config.title || "Expenses"}">
        <div class="rows" id="rows"><div class="empty">Loading…</div></div>
        ${
          this._config.limit && this._config.show_more_path
            ? `<button class="show-more" id="showMore">Show all</button>`
            : ""
        }
      </ha-card>
    `;
    this._el = { rows: root.getElementById("rows") };
    const showMore = root.getElementById("showMore");
    if (showMore) {
      showMore.addEventListener("click", () => this._navigate(this._config.show_more_path));
    }
  }

  _navigate(path) {
    window.history.pushState(null, "", path);
    window.dispatchEvent(new CustomEvent("location-changed", { bubbles: true, composed: true }));
  }

  _formatDate(iso) {
    try {
      return new Date(iso).toLocaleDateString();
    } catch (e) {
      return iso;
    }
  }

  _formatAmount(amount) {
    const unit = (this._hass.states["sensor.expense_tracker_total"] || {}).attributes
      ?.unit_of_measurement;
    const n = Number(amount).toFixed(2);
    return unit ? `${n} ${unit}` : n;
  }

  _renderRows() {
    if (!this._expenses || this._expenses.length === 0) {
      this._el.rows.innerHTML = `<div class="empty">No expenses yet.</div>`;
      return;
    }
    this._el.rows.innerHTML = "";
    for (const e of this._expenses) {
      const row = document.createElement("div");
      row.className = "row";
      const receiptHtml = e.receipt_path
        ? `<a class="receipt-link" href="/local/${e.receipt_path.replace(/^www\//, "")}" target="_blank" rel="noopener"><ha-icon icon="mdi:receipt"></ha-icon></a>`
        : "";
      row.innerHTML = `
        <ha-icon class="type-icon" icon="${e.icon}"></ha-icon>
        <div class="info">
          <div class="type-line">
            <span class="type">${this._escape(e.type)}</span>
            <span class="date">${this._formatDate(e.timestamp)}</span>
          </div>
          ${e.note ? `<div class="note">${this._escape(e.note)}</div>` : ""}
        </div>
        <div class="amount">${this._formatAmount(e.amount)}</div>
        ${receiptHtml}
        <button class="delete" data-id="${e.id}" title="Delete">
          <ha-icon icon="mdi:delete-outline"></ha-icon>
        </button>
      `;
      row.querySelector(".delete").addEventListener("click", () => this._delete(e.id));
      this._el.rows.appendChild(row);
    }
  }

  _escape(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  async _delete(id) {
    if (!window.confirm("Delete this expense?")) return;
    try {
      await this._hass.callService("expense_tracker", "remove_expense", { id });
      await this._fetch();
    } catch (err) {
      window.alert((err && err.message) || "Failed to delete.");
    }
  }
}

customElements.define("expense-tracker-list-card", ExpenseTrackerListCard);
