"""The `custom:codegen-fragment` card is served by the component itself."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.lovelace_codegen.frontend import CARD, URL


async def test_the_card_is_served(integration: HomeAssistant, hass_client: Any) -> None:
    client = await hass_client()
    response = await client.get(URL)

    assert response.status == 200
    assert await response.text() == CARD.read_text()
