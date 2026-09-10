/**
 * expense-tracker-add-card
 *
 * A real custom Lovelace card for logging expenses: type (with icons,
 * something no native HA form can render), amount, date, note. Reads
 * the live type list straight off sensor.expense_tracker_total's
 * `types` attribute (already kept fresh by the integration) and calls
 * expense_tracker.add_expense directly via hass.callService.
 *
 * `types` is a list of [name, icon] pairs, in display order -- NOT a
 * dict. It has to be, because HA's state machine skips writing a state
 * update when old attributes == new attributes, and plain dict equality
 * ignores key order (see sensor.py). A reorder-only change (same names,
 * same counts) would otherwise never reach this card.
 *
 * Receipt upload: POSTs multipart form data straight to /api/file_upload
 * (the backend contract for this is fully verified against the Python
 * source and an actual working end-to-end test from earlier in this
 * project -- accepts a "file" field, returns {file_id}), authenticated
 * via hass.auth.data.access_token, the standard token location on HA's
 * frontend hass object. That one property path is the single piece not
 * directly verifiable from Python-only source; if upload ever 401s,
 * that's the first thing to check.
 */
class ExpenseTrackerAddCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._render();
    }
    this._refreshTypes();
  }

  getCardSize() {
    return 5;
  }

  // ---- data ----

  _refreshTypes() {
    const state = this._hass.states["sensor.expense_tracker_total"];
    const types = (state && state.attributes && state.attributes.types) || [];
    const key = JSON.stringify(types);
    if (key === this._typesKey) return;
    this._typesKey = key;
    this._types = types; // list of [name, icon] pairs, in display order
    this._renderTypeMenu();
    if (!this._selectedType || !types.some(([name]) => name === this._selectedType)) {
      const first = types.length ? types[0][0] : null;
      if (first) this._selectType(first);
    }
  }

  // ---- rendering (built once; later hass updates patch data only) ----

  _render() {
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `
      <style>
        ha-card { padding: 16px; }
        .content { display: flex; flex-direction: column; gap: 20px; }

        .field { position: relative; }
        .field input[type="number"],
        .field input[type="text"] {
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
        .field input:focus {
          border-bottom-color: var(--primary-color);
        }
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

        .date-field label {
          display: block;
          font-size: 12px;
          color: var(--secondary-text-color);
          margin-bottom: 6px;
        }
        .date-field input[type="date"] {
          width: 100%;
          box-sizing: border-box;
          padding: 10px;
          font-size: 16px;
          font-family: inherit;
          color: var(--primary-text-color);
          background: var(--card-background-color);
          border: none;
          border-bottom: 2px solid var(--divider-color);
          outline: none;
        }
        .date-field input[type="date"]:focus {
          border-bottom-color: var(--primary-color);
        }

        .type-field label.caption {
          display: block;
          font-size: 12px;
          color: var(--secondary-text-color);
          margin-bottom: 6px;
        }
        .type-btn {
          width: 100%;
          box-sizing: border-box;
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px;
          font-size: 16px;
          font-family: inherit;
          color: var(--primary-text-color);
          background: var(--card-background-color);
          border: none;
          border-bottom: 2px solid var(--divider-color);
          cursor: pointer;
          text-align: left;
        }
        .type-btn:focus,
        .type-btn.open {
          border-bottom-color: var(--primary-color);
          outline: none;
        }
        .type-btn ha-icon.chev {
          margin-left: auto;
          color: var(--secondary-text-color);
          transition: transform 0.15s ease;
        }
        .type-btn.open ha-icon.chev {
          transform: rotate(180deg);
        }
        .type-wrap { position: relative; }
        .type-menu {
          display: none;
          position: absolute;
          left: 0;
          right: 0;
          top: calc(100% + 4px);
          z-index: 5;
          background: var(--card-background-color);
          border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.3));
          max-height: 240px;
          overflow-y: auto;
        }
        .type-menu.open { display: block; }
        .type-row {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 12px;
          cursor: pointer;
          color: var(--primary-text-color);
        }
        .type-row:hover { background: var(--secondary-background-color); }
        .type-row.selected { color: var(--primary-color); }

        .file-field label.caption {
          display: block;
          font-size: 12px;
          color: var(--secondary-text-color);
          margin-bottom: 6px;
        }
        .file-btn {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px;
          font-size: 15px;
          font-family: inherit;
          color: var(--primary-text-color);
          border: none;
          border-bottom: 2px solid var(--divider-color);
          cursor: pointer;
        }
        .file-btn .clear {
          margin-left: auto;
          color: var(--secondary-text-color);
          display: none;
        }
        .file-btn.has-file .clear { display: block; }

        .submit {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 12px;
          font-size: 15px;
          font-weight: 500;
          color: var(--text-primary-color, #fff);
          background: var(--primary-color);
          border: none;
          border-radius: var(--ha-card-border-radius, 8px);
          cursor: pointer;
        }
        .submit:disabled { opacity: 0.5; cursor: default; }

        .status {
          min-height: 18px;
          font-size: 13px;
          text-align: center;
        }
        .status.error { color: var(--error-color, #db4437); }
        .status.ok { color: var(--success-color, #43a047); }
      </style>

      <ha-card header="Add expense">
        <div class="content">
          <div class="type-field">
            <label class="caption">Type</label>
            <div class="type-wrap">
              <button type="button" class="type-btn" id="typeBtn">
                <ha-icon id="typeIcon" icon="mdi:help-circle-outline"></ha-icon>
                <span id="typeLabel">No types yet</span>
                <ha-icon class="chev" icon="mdi:chevron-down"></ha-icon>
              </button>
              <div class="type-menu" id="typeMenu"></div>
            </div>
          </div>

          <div class="field">
            <input type="number" id="amount" min="0" step="0.01" inputmode="decimal" placeholder=" ">
            <label for="amount">Amount</label>
          </div>

          <div class="date-field">
            <label for="date">Date</label>
            <input type="date" id="date">
          </div>

          <div class="field">
            <input type="text" id="note" placeholder=" ">
            <label for="note">Note</label>
          </div>

          <div class="file-field">
            <label class="caption">Receipt (optional)</label>
            <label class="file-btn" id="fileBtn">
              <ha-icon icon="mdi:camera-plus"></ha-icon>
              <span id="fileLabel">Add photo</span>
              <ha-icon class="clear" id="fileClear" icon="mdi:close"></ha-icon>
              <input type="file" id="receipt" accept="image/*" capture="environment" hidden>
            </label>
          </div>

          <button type="button" class="submit" id="submitBtn">
            <ha-icon icon="mdi:check"></ha-icon>
            Add expense
          </button>
          <div class="status" id="status"></div>
        </div>
      </ha-card>
    `;

    this._el = {
      typeBtn: root.getElementById("typeBtn"),
      typeIcon: root.getElementById("typeIcon"),
      typeLabel: root.getElementById("typeLabel"),
      typeMenu: root.getElementById("typeMenu"),
      amount: root.getElementById("amount"),
      date: root.getElementById("date"),
      note: root.getElementById("note"),
      fileBtn: root.getElementById("fileBtn"),
      fileLabel: root.getElementById("fileLabel"),
      receipt: root.getElementById("receipt"),
      submitBtn: root.getElementById("submitBtn"),
      status: root.getElementById("status"),
    };

    this._el.date.value = new Date().toISOString().slice(0, 10);

    this._el.typeBtn.addEventListener("click", () => this._toggleTypeMenu());
    document.addEventListener("click", (e) => {
      if (!e.composedPath().includes(this._el.typeBtn) &&
          !e.composedPath().includes(this._el.typeMenu)) {
        this._closeTypeMenu();
      }
    });
    this._el.receipt.addEventListener("change", () => this._onReceiptChosen());
    this._el.fileBtn.querySelector(".clear").addEventListener("click", (e) => {
      e.preventDefault();
      this._clearReceipt();
    });
    this._el.submitBtn.addEventListener("click", () => this._submit());
  }

  _onReceiptChosen() {
    const file = this._el.receipt.files[0];
    this._el.fileLabel.textContent = file ? file.name : "Add photo";
    this._el.fileBtn.classList.toggle("has-file", !!file);
  }

  _clearReceipt() {
    this._el.receipt.value = "";
    this._el.fileLabel.textContent = "Add photo";
    this._el.fileBtn.classList.remove("has-file");
  }

  async _uploadReceipt(file) {
    const formData = new FormData();
    formData.append("file", file);
    const resp = await fetch("/api/file_upload", {
      method: "POST",
      headers: { Authorization: `Bearer ${this._hass.auth.data.access_token}` },
      body: formData,
    });
    if (!resp.ok) {
      throw new Error(`Receipt upload failed (HTTP ${resp.status})`);
    }
    const body = await resp.json();
    return body.file_id;
  }

  _renderTypeMenu() {
    const menu = this._el.typeMenu;
    menu.innerHTML = "";
    for (const [name, icon] of this._types) {
      const row = document.createElement("div");
      row.className = "type-row";
      row.dataset.name = name;
      row.innerHTML = `<ha-icon icon="${icon}"></ha-icon><span>${name}</span>`;
      row.addEventListener("click", () => {
        this._selectType(name);
        this._closeTypeMenu();
      });
      menu.appendChild(row);
    }
  }

  _selectType(name) {
    this._selectedType = name;
    this._el.typeLabel.textContent = name;
    const match = this._types.find(([n]) => n === name);
    this._el.typeIcon.setAttribute(
      "icon",
      (match && match[1]) || "mdi:help-circle-outline"
    );
    for (const row of this._el.typeMenu.children) {
      row.classList.toggle("selected", row.dataset.name === name);
    }
  }

  _toggleTypeMenu() {
    const open = this._el.typeMenu.classList.toggle("open");
    this._el.typeBtn.classList.toggle("open", open);
  }

  _closeTypeMenu() {
    this._el.typeMenu.classList.remove("open");
    this._el.typeBtn.classList.remove("open");
  }

  // ---- submit ----

  async _submit() {
    const amount = this._el.amount.value;
    if (!this._selectedType) {
      this._setStatus("Pick a type first.", "error");
      return;
    }
    if (!amount || Number(amount) <= 0) {
      this._setStatus("Enter an amount.", "error");
      return;
    }

    this._el.submitBtn.disabled = true;
    this._setStatus("", "");

    const data = {
      amount: Number(amount),
      type: this._selectedType,
      date: this._el.date.value,
    };
    const note = this._el.note.value.trim();
    if (note) data.note = note;

    try {
      const file = this._el.receipt.files[0];
      if (file) {
        data.receipt = await this._uploadReceipt(file);
      }
      await this._hass.callService("expense_tracker", "add_expense", data);
      this._setStatus("Added.", "ok");
      this._el.amount.value = "";
      this._el.note.value = "";
      this._el.date.value = new Date().toISOString().slice(0, 10);
      this._clearReceipt();
    } catch (err) {
      this._setStatus((err && err.message) || "Failed to add expense.", "error");
    } finally {
      this._el.submitBtn.disabled = false;
    }
  }

  _setStatus(text, kind) {
    this._el.status.textContent = text;
    this._el.status.className = "status" + (kind ? " " + kind : "");
  }
}

customElements.define("expense-tracker-add-card", ExpenseTrackerAddCard);
