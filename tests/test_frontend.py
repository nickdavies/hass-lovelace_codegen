"""Cards are served, and listed as dashboard resources, by the component that
owns them."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.loader import DATA_CUSTOM_COMPONENTS
from homeassistant.setup import async_setup_component

from custom_components.lovelace_codegen import async_serve_card
from custom_components.lovelace_codegen.frontend import (
    CARD,
    FLOORPLAN_ACTIONS,
    FLOORPLAN_ACTIONS_URL,
    URL,
)

from .conftest import DOMAIN, _ensure_custom_components_path


def _versioned(url: str, path: Path) -> str:
    return f"{url}?v={hashlib.sha256(path.read_bytes()).hexdigest()[:12]}"


async def _resources(hass: HomeAssistant, ws_client: Any, command: str) -> list[Any]:
    client = await ws_client(hass)
    await client.send_json_auto_id({"type": command})
    msg = await client.receive_json()
    assert msg["success"], msg
    return msg["result"]


def _urls(resources: list[dict[str, str]]) -> list[str]:
    return [resource["url"] for resource in resources]


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


@pytest.mark.parametrize("command", ["lovelace/resources", "lovelace/resources/list"])
async def test_the_cards_are_dashboard_resources(
    integration: HomeAssistant, hass_ws_client: Any, command: str
) -> None:
    """Listed with their content hashes, which is how the frontend finds them:
    a phone's cached app page cannot hold back a list it fetches on every
    start."""
    resources = await _resources(integration, hass_ws_client, command)

    assert {"type": "module", "url": _versioned(URL, CARD)} in [
        {"type": r["type"], "url": r["url"]} for r in resources
    ]
    assert _versioned(FLOORPLAN_ACTIONS_URL, FLOORPLAN_ACTIONS) in _urls(resources)


async def test_another_component_serves_its_own_card(
    integration: HomeAssistant, hass_client: Any, hass_ws_client: Any, tmp_path: Path
) -> None:
    card = tmp_path / "my-card.js"
    card.write_text("customElements.define('my-card', class {});")
    await async_serve_card(integration, "/my_component/my-card.js", card)

    client = await hass_client()
    response = await client.get("/my_component/my-card.js")

    assert response.status == 200
    assert await response.text() == card.read_text()
    assert _versioned("/my_component/my-card.js", card) in _urls(
        await _resources(integration, hass_ws_client, "lovelace/resources")
    )


def _lovelace_yaml(*urls: str) -> dict[str, Any]:
    return {
        "lovelace": {
            "resource_mode": "yaml",
            "resources": [{"url": url, "type": "module"} for url in urls],
        }
    }


@pytest.fixture
async def yaml_resources(hass: HomeAssistant) -> HomeAssistant:
    """The component, with dashboard resources in YAML, as hass-configs has."""
    hass.data.pop(DATA_CUSTOM_COMPONENTS, None)
    _ensure_custom_components_path()

    assert await async_setup_component(
        hass, "lovelace", _lovelace_yaml("/local/a.js?v=1")
    )
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    return hass


async def test_yaml_resources_come_first(
    yaml_resources: HomeAssistant, hass_ws_client: Any
) -> None:
    urls = _urls(await _resources(yaml_resources, hass_ws_client, "lovelace/resources"))

    assert urls[0] == "/local/a.js?v=1"
    assert _versioned(URL, CARD) in urls


async def test_reloading_yaml_resources_keeps_the_cards(
    yaml_resources: HomeAssistant, hass_ws_client: Any
) -> None:
    """Reloading replaces Home Assistant's resource list with the YAML's."""
    with patch(
        "homeassistant.components.lovelace.async_hass_config_yaml",
        return_value=_lovelace_yaml("/local/b.js?v=2"),
    ):
        await yaml_resources.services.async_call(
            "lovelace", "reload_resources", blocking=True
        )

    urls = _urls(await _resources(yaml_resources, hass_ws_client, "lovelace/resources"))

    assert urls[0] == "/local/b.js?v=2"
    assert "/local/a.js?v=1" not in urls
    assert _versioned(URL, CARD) in urls
