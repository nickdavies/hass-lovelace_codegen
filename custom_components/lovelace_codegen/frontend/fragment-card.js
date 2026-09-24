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

if (!customElements.get(TAG)) {
  customElements.define(TAG, CodegenFragmentCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: TAG,
    name: "Generated fragment",
    description: "A card built by a component through lovelace_codegen.",
  });
}
