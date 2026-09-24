"""Registering a generated dashboard with a running Home Assistant.

This half leans on Home Assistant internals (`_register_panel`, `LovelaceConfig`,
the shape of `hass.data["lovelace"]`), so it is the half a Home Assistant
upgrade is likely to break.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.lovelace_codegen import (
    DBT,
    Dashboard,
    GeneratedDashboard,
    MarkdownCard,
    View,
)


class CountingDashboard(GeneratedDashboard):
    def __init__(self) -> None:
        self.renders = 0

    @property
    def title(self) -> str:
        return "Generated"

    @property
    def url_path(self) -> str:
        return "generated"

    async def render(self) -> DBT:
        self.renders += 1
        return Dashboard([View("Only", [MarkdownCard("hello")])]).render()


async def test_the_component_sets_up_with_no_config(
    integration: HomeAssistant,
) -> None:
    assert "lovelace_codegen" in integration.config.components
    assert "lovelace" in integration.config.components


async def test_a_registered_dashboard_serves_its_render(
    integration: HomeAssistant,
) -> None:
    dashboard = CountingDashboard()
    dashboard.add_to_hass(integration)

    lovelace = integration.data["lovelace"].dashboards["generated"]
    config = await lovelace.async_load(False)

    assert config == {
        "views": [
            {
                "panel": True,
                "title": "Only",
                "cards": [{"type": "markdown", "content": "hello"}],
            }
        ]
    }
    assert await lovelace.async_get_info() == {"mode": "yaml", "views": 1}


async def test_it_renders_once_and_serves_the_cache(
    integration: HomeAssistant,
) -> None:
    dashboard = CountingDashboard()
    dashboard.add_to_hass(integration)
    lovelace = integration.data["lovelace"].dashboards["generated"]

    await lovelace.async_load(False)
    await lovelace.async_json(False)

    assert dashboard.renders == 1


async def test_it_appears_in_the_sidebar(integration: HomeAssistant) -> None:
    CountingDashboard().add_to_hass(integration)

    panels = integration.data["frontend_panels"]
    assert panels["generated"].sidebar_title == "Generated"
