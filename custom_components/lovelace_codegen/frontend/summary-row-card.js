// One row summing up a part of the house: an icon with a count bubble, a name,
// and a few labelled values beside each other, the whole row one tap.
//
//   type: custom:codegen-summary-row
//   name: Laundry
//   icon: mdi:washing-machine
//   badge: sensor.laundry_outstanding_nick
//   tap_action:
//     action: navigate
//     navigation_path: /lovelace-nick/laundry
//   items:
//     - entity: sensor.laundry_washer_nick
//       name: Washer
//     - entity: sensor.plant_outstanding_nick
//       attribute: needs_water
//       name: Need water
//       icon: mdi:watering-can
//       alert: true
//
// `badge` is an entity whose state is a count: above zero, it is a bubble on
// the icon, the way an app shows unread notifications.
//
// Each item shows its entity's state, or one attribute of it, with the entity's
// icon unless `icon` gives another. The entity can say more through two
// attributes of its own, which is how a template sensor dresses its state:
//
//   tone:  idle, active, attention or alert, colouring the item's icon.
//   since: a timestamp, shown after the value as the time since it, kept
//          current while the card is on screen.
//
// An item with `alert: true` takes the alert tone whenever its value is a
// number above zero, for a count that is a problem as soon as it is not zero.
//
// Plain DOM rather than lit, as Home Assistant does not export lit to custom
// cards. Served and loaded by the lovelace_codegen component, so no dashboard
// resource entry is needed.

const TAG = "codegen-summary-row";

const TONES = {
  idle: "var(--secondary-text-color)",
  active: "var(--info-color, var(--primary-color))",
  attention: "var(--warning-color)",
  alert: "var(--error-color)",
};

const escape = (text) =>
  String(text).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

// "4m", "2h 5m", "3d 4h": short enough to sit after a value on a phone.
const elapsed = (since) => {
  const minutes = Math.floor((Date.now() - new Date(since).getTime()) / 60000);
  if (isNaN(minutes)) {
    return undefined;
  }
  if (minutes < 1) {
    return "just now";
  }
  if (minutes < 60) {
    return `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return minutes % 60 ? `${hours}h ${minutes % 60}m` : `${hours}h`;
  }
  return hours % 24 ? `${Math.floor(hours / 24)}d ${hours % 24}h` : `${hours / 24}d`;
};

class CodegenSummaryRowCard extends HTMLElement {
  setConfig(config) {
    if (!config.name || !Array.isArray(config.items)) {
      throw new Error("name and items are both required");
    }
    for (const item of config.items) {
      if (!item.entity) {
        throw new Error("every item needs an entity");
      }
    }
    this._config = config;
    this._states = undefined;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", () => this._tap());
      this.shadowRoot.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          this._tap();
        }
      });
    }
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    // Every state change anywhere in the house sets `hass`; only redraw when
    // one of this card's own entities moved.
    const states = this._entities().map((id) => hass.states[id]);
    if (this._states && states.every((s, i) => s === this._states[i])) {
      return;
    }
    this._states = states;
    this._render();
  }

  connectedCallback() {
    // The time since a `since` moves with no state change to redraw on.
    this._timer = setInterval(() => this._render(), 60000);
    this._render();
  }

  disconnectedCallback() {
    clearInterval(this._timer);
  }

  _entities() {
    return [this._config.badge, ...this._config.items.map((i) => i.entity)].filter(
      Boolean
    );
  }

  // Through Home Assistant's own action handler, as a built-in card's tap is,
  // so a navigate records the history a subview's back arrow reads.
  _tap() {
    if (!this._config.tap_action) {
      return;
    }
    this.dispatchEvent(
      new CustomEvent("hass-action", {
        bubbles: true,
        composed: true,
        detail: { config: { tap_action: this._config.tap_action }, action: "tap" },
      })
    );
  }

  _badge() {
    const stateObj = this._config.badge && this._hass.states[this._config.badge];
    const count = parseFloat(stateObj?.state);
    if (!(count > 0)) {
      return "";
    }
    return `<span class="badge">${escape(count > 99 ? "99+" : count)}</span>`;
  }

  _item(item) {
    const stateObj = this._hass.states[item.entity];
    if (!stateObj) {
      return `
        <div class="item">
          <span class="label">${escape(item.name ?? item.entity)}</span>
          <span class="value missing">missing</span>
        </div>`;
    }
    const attrs = stateObj.attributes;
    const raw = item.attribute ? attrs[item.attribute] : stateObj.state;
    let value = item.attribute
      ? this._hass.formatEntityAttributeValue(stateObj, item.attribute)
      : this._hass.formatEntityState(stateObj);
    const ago = attrs.since && elapsed(attrs.since);
    if (ago) {
      value = `${value} · ${ago}`;
    }
    const tone = item.alert && parseFloat(raw) > 0 ? "alert" : attrs.tone;
    const icon = item.icon ?? attrs.icon;
    return `
      <div class="item">
        <span class="label">
          ${icon ? `<ha-icon icon="${escape(icon)}" style="color: ${TONES[tone] ?? TONES.idle}"></ha-icon>` : ""}
          ${escape(item.name ?? attrs.friendly_name ?? item.entity)}
        </span>
        <span class="value">${escape(value)}</span>
      </div>`;
  }

  _render() {
    if (!this._config || !this._hass || !this.shadowRoot) {
      return;
    }
    const { name, icon, tap_action } = this._config;
    const tappable = tap_action && tap_action.action !== "none";
    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 12px;
          height: 100%;
          box-sizing: border-box;
        }
        ha-card.tappable { cursor: pointer; }
        .icon {
          position: relative;
          flex: none;
          display: flex;
          align-items: center;
          justify-content: center;
          width: 40px;
          height: 40px;
          border-radius: 50%;
          color: var(--primary-color);
          background: color-mix(in srgb, var(--primary-color) 20%, transparent);
        }
        .badge {
          position: absolute;
          top: -4px;
          right: -6px;
          min-width: 18px;
          height: 18px;
          padding: 0 5px;
          box-sizing: border-box;
          border-radius: 9px;
          background: var(--error-color);
          color: var(--text-primary-color, #fff);
          font-size: 11px;
          font-weight: 600;
          line-height: 18px;
          text-align: center;
        }
        .body { flex: 1; min-width: 0; }
        .name { font-weight: 500; line-height: 20px; }
        .items {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
          gap: 2px 12px;
        }
        .item { display: flex; flex-direction: column; min-width: 0; }
        .label {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 12px;
          color: var(--secondary-text-color);
        }
        .label ha-icon { --mdc-icon-size: 14px; flex: none; }
        .value, .label {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .value { font-size: 14px; font-variant-numeric: tabular-nums; }
        .missing { color: var(--error-color); }
      </style>
      <ha-card class="${tappable ? "tappable" : ""}"
        ${tappable ? `role="button" tabindex="0"` : ""}>
        <div class="icon">
          ${icon ? `<ha-icon icon="${escape(icon)}"></ha-icon>` : ""}
          ${this._badge()}
        </div>
        <div class="body">
          <div class="name">${escape(name)}</div>
          <div class="items">${this._config.items.map((i) => this._item(i)).join("")}</div>
        </div>
      </ha-card>`;
  }

  getCardSize() {
    return 2;
  }

  // A full row in a sections view.
  getGridOptions() {
    return { columns: 12, rows: 2, min_columns: 6 };
  }
}

// Home Assistant's app replaces `window.customElements` with a scoped-registry
// polyfill as it boots, and the polyfill cannot see anything defined on the
// registry it replaced. This module loads alongside the app rather than after
// it, so it registers only once the app's root element exists, which is
// defined right after the swap, and on whichever registry is current then.
customElements.whenDefined("home-assistant").then(() => {
  if (customElements.get(TAG)) {
    return;
  }
  customElements.define(TAG, CodegenSummaryRowCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: TAG,
    name: "Summary row",
    description: "A count bubble, a name and a few values, as one tappable row.",
  });
});
