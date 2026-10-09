// A card that shows a fragment: one card a component builds in Python and
// offers through lovelace_codegen's registry.
//
//   type: custom:codegen-fragment
//   source: light_motion_profiles
//   fragment: light_config
//   params:
//     light: dining
//
// It asks Home Assistant for the card config over the websocket and hands it to
// Home Assistant's own card factory, so the result is exactly the card the
// component would have put on its own dashboard. Served and loaded by the
// lovelace_codegen component, so no dashboard resource entry is needed.

const TAG = "codegen-fragment";

class CodegenFragmentCard extends HTMLElement {
  setConfig(config) {
    if (!config.source || !config.fragment) {
      throw new Error("source and fragment are both required");
    }
    const key = JSON.stringify([config.source, config.fragment, config.params ?? {}]);
    if (key === this._key) {
      return;
    }
    this._key = key;
    this._config = config;
    this._card = undefined;
    this._loading = undefined;
    if (this._hass) {
      this._loading = this._load();
    }
  }

  set hass(hass) {
    this._hass = hass;
    if (this._card) {
      this._card.hass = hass;
    } else if (this._config && !this._loading) {
      this._loading = this._load();
    }
  }

  async _load() {
    const key = this._key;
    const { source, fragment, params = {} } = this._config;
    let config;
    try {
      config = await this._hass.callWS({
        type: "lovelace_codegen/fragment",
        source,
        name: fragment,
        params,
      });
    } catch (err) {
      config = {
        type: "markdown",
        content: `**Fragment ${source}/${fragment} failed**\n\n${err?.message ?? err}`,
      };
    }
    const helpers = await window.loadCardHelpers();
    if (key !== this._key) {
      // The config changed while this one was loading; the newer load wins.
      return;
    }
    const card = helpers.createCardElement(config);
    card.hass = this._hass;
    this._card = card;
    this.replaceChildren(card);
  }

  async getCardSize() {
    await this._loading;
    return this._card?.getCardSize ? await this._card.getCardSize() : 1;
  }
}

// Gives a FloorplanCard tap's navigation the history state Home Assistant's
// own navigation records, so a subview opened from a floor plan goes back to it.
//
// ha-floorplan navigates by pushing the new URL onto history without that
// state. A subview's back arrow reads `from` there to go back in history, so
// without it the arrow fell back to the dashboard's first view: a room opened
// from a plan on one dashboard went "back" to another. `floorplan_tap` follows
// its `navigate` with a `fire-dom-event`, which ha-floorplan fires as an
// `ll-custom` event right after navigating, and this then records where the
// tap was as the new entry's `from`.
//
// ha-floorplan still does the navigating, so a tap works even on a page that
// has not loaded this file: an app shell cached from before a change lists the
// modules it had then, at the versions it had then. Only the back arrow
// depends on this.
let pathAtTap;
window.addEventListener(
  "click",
  () => {
    pathAtTap = location.pathname;
  },
  { capture: true },
);
window.addEventListener("ll-custom", (event) => {
  if (!event.detail?.codegen_navigated) {
    return;
  }
  event.stopPropagation();
  const from = pathAtTap;
  pathAtTap = undefined;
  if (from === undefined || from === location.pathname || history.state?.from !== undefined) {
    return;
  }
  history.replaceState({ ...history.state, from }, "");
});

// Home Assistant's app replaces `window.customElements` with a scoped-registry
// polyfill as it boots, and the polyfill cannot see anything defined on the
// registry it replaced. This module loads alongside the app rather than after
// it, so it registers only once the app's root element exists, which is
// defined right after the swap, and on whichever registry is current then.
customElements.whenDefined("home-assistant").then(() => {
  if (customElements.get(TAG)) {
    return;
  }
  customElements.define(TAG, CodegenFragmentCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: TAG,
    name: "Generated fragment",
    description: "A card built by a component through lovelace_codegen.",
  });
});
