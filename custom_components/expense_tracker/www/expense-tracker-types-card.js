/**
 * expense-tracker-types-card
 *
 * Manage expense types: add new ones, remove unused ones. A type with
 * one or more expenses still referencing it cannot be removed -- enforced
 * server-side (custom_components/expense_tracker/db.py's remove_type
 * raises TypeInUseError), not just hidden client-side. This card reads
 * usage counts from the read-only expense_tracker.list_types service
 * (WebSocket call_service + return_response: true, same verified message
 * shape as expense-tracker-list-card.js) and disables the delete button
 * for anything in use, but even if that were bypassed the backend still
 * refuses the removal.
 */
class ExpenseTrackerTypesCard extends HTMLElement {
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
    return 6;
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
    try {
      const result = await this._hass.connection.sendMessagePromise({
        type: "call_service",
        domain: "expense_tracker",
        service: "list_types",
        service_data: {},
        return_response: true,
      });
      this._types = (result.response && result.response.types) || [];
      this._renderRows();
    } catch (err) {
      this._el.rows.innerHTML = `<div class="empty">Couldn't load types: ${
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
        .name { flex: 1; font-size: 14px; color: var(--primary-text-color); }
        .count {
          font-size: 12px;
          color: var(--secondary-text-color);
          flex-shrink: 0;
        }
        .delete {
          flex-shrink: 0;
          color: var(--secondary-text-color);
          background: none;
          border: none;
          cursor: pointer;
          display: flex;
        }
        .delete:hover:not(:disabled) { color: var(--error-color, #db4437); }
        .delete:disabled { opacity: 0.3; cursor: default; }
        .empty {
          padding: 20px 16px;
          text-align: center;
          color: var(--secondary-text-color);
          font-size: 14px;
        }

        .add-section {
          display: flex;
          align-items: flex-end;
          gap: 12px;
          padding: 16px 16px 4px;
          border-top: 1px solid var(--divider-color);
          margin-top: 8px;
        }
        .field { position: relative; flex: 1; }
        .field input {
          width: 100%;
          box-sizing: border-box;
          padding: 14px 10px 6px;
          font-size: 16px;
          font-family: inherit;
          color: var(--primary-text-color);
          background: var(--card-background-color);
          border: none;
          border-bottom: 2px solid var(--divider-color);
          outline: none;
        }
        .field input:focus { border-bottom-color: var(--primary-color); }
        .field label {
          position: absolute;
          left: 10px;
          top: 14px;
          font-size: 16px;
          color: var(--secondary-text-color);
          pointer-events: none;
          transition: 0.15s ease all;
        }
        .field input:focus + label,
        .field input:not(:placeholder-shown) + label {
          top: -6px;
          font-size: 12px;
          color: var(--primary-color);
        }
        .icon-field { display: flex; align-items: center; gap: 8px; }
        .icon-preview { flex-shrink: 0; color: var(--secondary-text-color); }
        .add-btn {
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 44px;
          height: 44px;
          color: var(--text-primary-color, #fff);
          background: var(--primary-color);
          border: none;
          border-radius: 50%;
          cursor: pointer;
        }
        .add-btn:disabled { opacity: 0.5; cursor: default; }
        .status {
          padding: 4px 16px 0;
          min-height: 18px;
          font-size: 13px;
          text-align: center;
        }
        .status.error { color: var(--error-color, #db4437); }
      </style>
      <ha-card header="${this._config.title || "Expense types"}">
        <div class="rows" id="rows"><div class="empty">Loading…</div></div>
        <div class="add-section">
          <div class="field">
            <input type="text" id="newName" placeholder=" ">
            <label for="newName">New type</label>
          </div>
          <div class="field icon-field">
            <ha-icon class="icon-preview" id="iconPreview" icon="mdi:help-circle-outline"></ha-icon>
            <input type="text" id="newIcon" placeholder=" " value="mdi:tag">
            <label for="newIcon">Icon (mdi:...)</label>
          </div>
          <button class="add-btn" id="addBtn" title="Add type">
            <ha-icon icon="mdi:plus"></ha-icon>
          </button>
        </div>
        <div class="status" id="status"></div>
      </ha-card>
    `;

    this._el = {
      rows: root.getElementById("rows"),
      newName: root.getElementById("newName"),
      newIcon: root.getElementById("newIcon"),
      iconPreview: root.getElementById("iconPreview"),
      addBtn: root.getElementById("addBtn"),
      status: root.getElementById("status"),
    };

    this._el.newIcon.addEventListener("input", () => {
      const value = this._el.newIcon.value.trim() || "mdi:help-circle-outline";
      this._el.iconPreview.setAttribute("icon", value);
    });
    this._el.addBtn.addEventListener("click", () => this._addType());
  }

  _renderRows() {
    if (!this._types || this._types.length === 0) {
      this._el.rows.innerHTML = `<div class="empty">No types yet.</div>`;
      return;
    }
    this._el.rows.innerHTML = "";
    for (const t of this._types) {
      const row = document.createElement("div");
      row.className = "row";
      const inUse = t.count > 0;
      row.innerHTML = `
        <ha-icon class="type-icon" icon="${t.icon}"></ha-icon>
        <span class="name">${this._escape(t.name)}</span>
        <span class="count">${
          inUse ? `${t.count} expense${t.count === 1 ? "" : "s"}` : "unused"
        }</span>
        <button class="delete" data-name="${this._escape(t.name)}"
          title="${inUse ? "In use -- can't delete" : "Delete"}"
          ${inUse ? "disabled" : ""}>
          <ha-icon icon="mdi:delete-outline"></ha-icon>
        </button>
      `;
      if (!inUse) {
        row
          .querySelector(".delete")
          .addEventListener("click", () => this._deleteType(t.name));
      }
      this._el.rows.appendChild(row);
    }
  }

  _escape(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  _setStatus(text, kind) {
    this._el.status.textContent = text;
    this._el.status.className = "status" + (kind ? " " + kind : "");
  }

  async _addType() {
    const name = this._el.newName.value.trim();
    const icon = this._el.newIcon.value.trim();
    if (!name) {
      this._setStatus("Enter a name.", "error");
      return;
    }
    if (!icon) {
      this._setStatus("Enter an icon.", "error");
      return;
    }
    this._el.addBtn.disabled = true;
    this._setStatus("", "");
    try {
      await this._hass.callService("expense_tracker", "add_type", { name, icon });
      this._el.newName.value = "";
      this._el.newIcon.value = "mdi:tag";
      this._el.iconPreview.setAttribute("icon", "mdi:tag");
      await this._fetch();
    } catch (err) {
      this._setStatus((err && err.message) || "Failed to add type.", "error");
    } finally {
      this._el.addBtn.disabled = false;
    }
  }

  async _deleteType(name) {
    if (!window.confirm(`Delete type "${name}"?`)) return;
    try {
      await this._hass.callService("expense_tracker", "remove_type", { name });
      await this._fetch();
    } catch (err) {
      window.alert((err && err.message) || "Failed to delete type.");
    }
  }
}

customElements.define("expense-tracker-types-card", ExpenseTrackerTypesCard);
