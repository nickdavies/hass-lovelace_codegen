"""Serving the `custom:codegen-fragment` card to the frontend.

The component serves the card and adds it to every page itself, so a dashboard
using fragments needs no resource entry, and the card is always the version
that matches the registry answering it.
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


async def async_setup_frontend(hass: HomeAssistant) -> None:
    # The content hash in the URL makes browsers fetch a new card after an
    # upgrade, while letting them cache it forever in between.
    content = await hass.async_add_executor_job(CARD.read_bytes)
    version = hashlib.sha256(content).hexdigest()[:12]

    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL, str(CARD), cache_headers=True)]
    )
    # `frontend` is an after-dependency rather than a dependency: Home
    # Assistant always loads it, but it needs the hass_frontend package, which a
    # test install does not have. Loading after it is enough to find it here.
    if "frontend" not in hass.config.components:
        _LOGGER.debug("frontend is not loaded; the fragment card is served only")
        return
    add_extra_js_url(hass, f"{URL}?v={version}")
