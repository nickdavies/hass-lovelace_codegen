"""Serving custom cards to the frontend.

A component that brings its own card, beside the `Renderable` that models it,
serves the card's JS with `async_serve_card`. The card is served and listed as a
dashboard resource by the component itself, so a dashboard using it needs no
resource entry, and the card is always the version that matches the component
rendering it.

This component serves its own `custom:codegen-fragment` card the same way, and
the script that runs `FloorplanCard` taps through Home Assistant's action
handler.

The cards are dashboard resources rather than `add_extra_js_url` modules because
of where each list lives. An extra module is written into the app's HTML page,
which the frontend's service worker and the companion app cache: a phone that
reopens on a cached page loads the modules that page listed, at the versions it
listed, however long ago it was cached. Dashboard resources are fetched over the
websocket each time the app starts, so a card added or changed here reaches
every page on its next start.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.websocket import (
    websocket_lovelace_resources_impl,
)
from homeassistant.core import HomeAssistant
from homeassistant.util.hass_dict import HassKey

from ..const import DOMAIN

CARD = Path(__file__).parent / "fragment-card.js"
URL = f"/{DOMAIN}/fragment-card.js"
FLOORPLAN_ACTIONS = Path(__file__).parent / "floorplan-actions.js"
FLOORPLAN_ACTIONS_URL = f"/{DOMAIN}/floorplan-actions.js"

# Each served card's URL, to its URL with the content hash.
DATA_CARDS: HassKey[dict[str, str]] = HassKey(f"{DOMAIN}_cards")

# The commands the frontend lists dashboard resources with: Home Assistant
# registers both, in YAML and in storage resource mode alike.
RESOURCES_COMMANDS = ("lovelace/resources", "lovelace/resources/list")


async def async_serve_card(hass: HomeAssistant, url: str, path: Path) -> None:
    """Serve the card at `path` on `url`, and list it as a dashboard resource.

    `url` should start with the serving component's domain, so two components'
    cards cannot collide. The calling component needs `lovelace_codegen` in its
    manifest's `dependencies`, which it has to import this anyway.
    """
    # The content hash in the URL makes browsers fetch a new card after an
    # upgrade, while letting them cache it forever in between.
    content = await hass.async_add_executor_job(path.read_bytes)
    version = hashlib.sha256(content).hexdigest()[:12]

    await hass.http.async_register_static_paths(
        [StaticPathConfig(url, str(path), cache_headers=True)]
    )
    hass.data.setdefault(DATA_CARDS, {})[url] = f"{url}?v={version}"


def served_resources(hass: HomeAssistant) -> list[dict[str, str]]:
    """The served cards, as the dashboard resources the frontend loads."""
    return [
        {"id": f"{DOMAIN}:{url}", "type": "module", "url": versioned}
        for url, versioned in hass.data.get(DATA_CARDS, {}).items()
    ]


class _WithServedCards:
    """A websocket connection whose result has the served cards added to it."""

    def __init__(
        self, hass: HomeAssistant, connection: websocket_api.ActiveConnection
    ) -> None:
        self._hass = hass
        self._connection = connection

    def send_result(self, msg_id: int, result: Any = None) -> None:
        self._connection.send_result(msg_id, [*result, *served_resources(self._hass)])

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)


@websocket_api.async_response
async def websocket_resources(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Home Assistant's dashboard resources, then the cards served here.

    Answers in place of Home Assistant's own handler, by running the function
    behind it, which loads the resources in either resource mode and sends
    them, and adding the served cards to what it sends. Home Assistant decides
    what its resources are, and the cards are added on every call, so reloading
    YAML resources, which replaces Home Assistant's list, cannot drop them.
    """
    await websocket_lovelace_resources_impl(
        hass, _WithServedCards(hass, connection), msg
    )


async def async_setup_frontend(hass: HomeAssistant) -> None:
    await async_serve_card(hass, URL, CARD)
    await async_serve_card(hass, FLOORPLAN_ACTIONS_URL, FLOORPLAN_ACTIONS)
    # `lovelace` is a dependency, so its own handlers are registered by now;
    # registering a command again replaces its handler.
    for command in RESOURCES_COMMANDS:
        websocket_api.async_register_command(
            hass,
            command,
            websocket_resources,
            websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({"type": command}),
        )
