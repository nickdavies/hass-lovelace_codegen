// Runs a FloorplanCard's tap actions through Home Assistant's own action
// handler, the one every built-in card uses.
//
// ha-floorplan performs a `navigate` itself, by pushing the new URL onto
// history without the state Home Assistant's own navigation records there. A
// subview's back arrow reads that state to go back in history, so without it
// the arrow falls back to the dashboard's first view: a room opened from a plan
// on one dashboard went "back" to another. `floorplan_tap` therefore wraps each
// action in ha-floorplan's `fire-dom-event`, which it fires as an `ll-custom`
// event with the action as its detail, and this hands the action inside,
// `codegen_action`, to Home Assistant as a `hass-action`, the event custom
// cards use for their own actions.
//
// Served and loaded on every page by the lovelace_codegen component.

window.addEventListener("ll-custom", (event) => {
  const action = event.detail?.codegen_action;
  if (!action) {
    return;
  }
  // From inside the card, so it reaches Home Assistant's handler the way a
  // card's own event would.
  event.composedPath()[0].dispatchEvent(
    new CustomEvent("hass-action", {
      bubbles: true,
      composed: true,
      detail: { config: { tap_action: action }, action: "tap" },
    }),
  );
});
