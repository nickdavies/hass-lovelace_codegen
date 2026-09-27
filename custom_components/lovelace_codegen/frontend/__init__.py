"""Serving custom cards to the frontend.

A component that brings its own card, beside the `Renderable` that models it,
serves the card's JS with `async_serve_card`. It is served and added to every
page by the component itself, so a dashboard using it needs no resource entry,
and the card is always the version that matches the component rendering it.

This component serves its own `custom:codegen-fragment` card the same way.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD = Path(__file__).parent / "fragment-card.js"
URL = f"/{DOMAIN}/fragment-card.js"


async def async_serve_card(hass: HomeAssistant, url: str, path: Path) -> None:
    """Serve the card at `path` on `url`, and load it on every frontend page.

    `url` should start with the serving component's domain, so two components'
    cards cannot collide. The calling component needs `frontend` in its
    manifest's `after_dependencies` for the card to be loaded, not just served.
    """
    # The content hash in the URL makes browsers fetch a new card after an
    # upgrade, while letting them cache it forever in between.
    content = await hass.async_add_executor_job(path.read_bytes)
    version = hashlib.sha256(content).hexdigest()[:12]

    await hass.http.async_register_static_paths(
        [StaticPathConfig(url, str(path), cache_headers=True)]
    )
    # `frontend` is an after-dependency rather than a dependency: Home
    # Assistant always loads it, but it needs the hass_frontend package, which a
    # test install does not have. Loading after it is enough to find it here.
    if "frontend" not in hass.config.components:
        _LOGGER.debug("frontend is not loaded; %s is served only", url)
        return
    add_extra_js_url(hass, f"{url}?v={version}")


async def async_setup_frontend(hass: HomeAssistant) -> None:
    await async_serve_card(hass, URL, CARD)
