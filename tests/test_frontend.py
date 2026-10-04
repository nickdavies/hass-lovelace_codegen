"""Cards are served by the component that owns them."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.lovelace_codegen import async_serve_card
from custom_components.lovelace_codegen.frontend import (
    CARD,
    FLOORPLAN_ACTIONS,
    FLOORPLAN_ACTIONS_URL,
    URL,
)


async def test_the_card_is_served(integration: HomeAssistant, hass_client: Any) -> None:
    client = await hass_client()
    response = await client.get(URL)

    assert response.status == 200
    assert await response.text() == CARD.read_text()


async def test_the_floorplan_actions_are_served(
    integration: HomeAssistant, hass_client: Any
) -> None:
    client = await hass_client()
    response = await client.get(FLOORPLAN_ACTIONS_URL)

    assert response.status == 200
    assert await response.text() == FLOORPLAN_ACTIONS.read_text()


async def test_another_component_serves_its_own_card(
    integration: HomeAssistant, hass_client: Any, tmp_path: Path
) -> None:
    card = tmp_path / "my-card.js"
    card.write_text("customElements.define('my-card', class {});")
    await async_serve_card(integration, "/my_component/my-card.js", card)

    client = await hass_client()
    response = await client.get("/my_component/my-card.js")

    assert response.status == 200
    assert await response.text() == card.read_text()
