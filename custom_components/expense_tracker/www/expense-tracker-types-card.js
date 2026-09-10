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
 *
 * The icon field uses <ha-icon-picker>, a global custom element the HA
 * frontend itself uses for every native icon selector -- confirmed live
 * (2026.9.1) to render with no .hass set, expose a `value` property, and
 * fire `value-changed` with `{value}` on selection. It wraps a searchable
 * combo box over the full MDI set but keeps `allow-custom-value`, so an
 * icon name typed directly still works.
 *
 * Row order is drag-and-drop reorderable via a grip handle, using Pointer
 * Events (not the HTML5 Drag-and-Drop API) specifically so this works on
 * touch -- native HTML5 drag-and-drop has no touch support on iOS/Android,
 * which would silently break this on a phone dashboard, the single most
 * common way to reach a Home Assistant UI. Persisted via
 * expense_tracker.reorder_types (full-list replace, validated server-side
 * against TypeSetMismatchError).
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
      if (this._el) this._el.newIcon.hass = hass;
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
        .row.dragging {
          opacity: 0.6;
          background: var(--secondary-background-color);
        }
        .row ha-icon.grip {
          color: var(--secondary-text-color);
          flex-shrink: 0;
          cursor: grab;
          touch-action: none;
        }
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
        .icon-field { display: flex; }
        .icon-field ha-icon-picker { width: 100%; }
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
            <ha-icon-picker id="newIcon" label="Icon"></ha-icon-picker>
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
      addBtn: root.getElementById("addBtn"),
      status: root.getElementById("status"),
    };

    this._el.newIcon.value = "mdi:tag";
    if (this._hass) this._el.newIcon.hass = this._hass;
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
      row.dataset.name = t.name;
      const inUse = t.count > 0;
      row.innerHTML = `
        <ha-icon class="grip" icon="mdi:drag"></ha-icon>
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
      this._wireDrag(row.querySelector(".grip"), row);
      this._el.rows.appendChild(row);
    }
  }

  // ---- drag-to-reorder (Pointer Events, not HTML5 DnD -- see the file
  // header comment for why: HTML5 drag-and-drop doesn't work on touch) ----

  _wireDrag(grip, row) {
    grip.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      grip.setPointerCapture(e.pointerId);
      row.classList.add("dragging");
      this._drag = { pointerId: e.pointerId };
    });

    grip.addEventListener("pointermove", (e) => {
      if (!this._drag || this._drag.pointerId !== e.pointerId) return;
      const children = Array.from(this._el.rows.children);
      const currentIndex = children.indexOf(row);
      for (let i = 0; i < children.length; i++) {
        if (i === currentIndex) continue;
        const rect = children[i].getBoundingClientRect();
        const midpoint = rect.top + rect.height / 2;
        const movingDown = i > currentIndex;
        if (movingDown && e.clientY >= midpoint) {
          this._el.rows.insertBefore(row, children[i].nextSibling);
          break;
        }
        if (!movingDown && e.clientY < midpoint) {
          this._el.rows.insertBefore(row, children[i]);
          break;
        }
      }
    });

    const finishDrag = (e) => {
      if (!this._drag || this._drag.pointerId !== e.pointerId) return;
      this._drag = null;
      row.classList.remove("dragging");
      this._persistOrder();
    };
    grip.addEventListener("pointerup", finishDrag);
    grip.addEventListener("pointercancel", finishDrag);
  }

  async _persistOrder() {
    const names = Array.from(this._el.rows.children)
      .map((r) => r.dataset.name)
      .filter(Boolean);
    if (names.length < 2) return;
    try {
      await this._hass.callService("expense_tracker", "reorder_types", {
        names,
      });
    } catch (err) {
      this._setStatus((err && err.message) || "Failed to save order.", "error");
    } finally {
      // Resync this._types to the server's actual order either way -- on
      // success this just confirms it; on failure it reverts the DOM's
      // now-wrong order back to whatever the server still has, instead of
      // leaving a locally-reordered view that doesn't match what was
      // actually persisted.
      await this._fetch();
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
    const icon = (this._el.newIcon.value || "").trim();
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
