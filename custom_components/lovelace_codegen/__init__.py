"""Lovelace dashboards generated from code, shared by other custom components.

Not an integration anyone configures. Another component lists `lovelace_codegen`
in its manifest's `dependencies`, which makes Home Assistant load this one first,
and then imports the building blocks from here:

    from custom_components.lovelace_codegen import EntitiesCard, View

Being a custom component rather than a pip package means it deploys the way the
components using it do. The cost is that Home Assistant loads exactly one copy,
so every component using it runs against the same version.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .lovelace import (
    DBT,
    ENTITY,
    ICON,
    NAME,
    Dashboard,
    EntitiesCard,
    GeneratedDashboard,
    HistoryGraphCard,
    HorizontalStackCard,
    ManualLovelaceYAML,
    MarkdownCard,
    Renderable,
    VerticalStackCard,
    View,
    divider,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

DOMAIN = "lovelace_codegen"

__all__ = [
    "DBT",
    "ENTITY",
    "ICON",
    "NAME",
    "Dashboard",
    "EntitiesCard",
    "GeneratedDashboard",
    "HistoryGraphCard",
    "HorizontalStackCard",
    "ManualLovelaceYAML",
    "MarkdownCard",
    "Renderable",
    "VerticalStackCard",
    "View",
    "divider",
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Nothing to set up: the dashboards belong to the components using this."""
    return True
