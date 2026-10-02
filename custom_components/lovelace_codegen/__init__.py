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

from .const import DOMAIN
from .fragments import (
    Fragment,
    FragmentError,
    Params,
    async_setup_fragments,
    register_fragments,
)
from .frontend import async_serve_card, async_setup_frontend
from .lovelace import (
    DBT,
    ButtonCard,
    ENTITY,
    ICON,
    NAME,
    Dashboard,
    EntitiesCard,
    GeneratedDashboard,
    GridCard,
    HistoryGraphCard,
    HorizontalStackCard,
    IconElement,
    ImageElement,
    ManualLovelaceYAML,
    MarkdownCard,
    PictureElement,
    PictureElementsCard,
    Renderable,
    TileCard,
    VerticalStackCard,
    View,
    divider,
    navigate,
    tap_area,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

__all__ = [
    "DBT",
    "ButtonCard",
    "DOMAIN",
    "ENTITY",
    "ICON",
    "NAME",
    "Dashboard",
    "EntitiesCard",
    "Fragment",
    "FragmentError",
    "GeneratedDashboard",
    "GridCard",
    "HistoryGraphCard",
    "HorizontalStackCard",
    "IconElement",
    "ImageElement",
    "ManualLovelaceYAML",
    "MarkdownCard",
    "Params",
    "PictureElement",
    "PictureElementsCard",
    "Renderable",
    "TileCard",
    "VerticalStackCard",
    "View",
    "async_serve_card",
    "divider",
    "navigate",
    "register_fragments",
    "tap_area",
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """The fragment registry and its card: the dashboards belong to the components."""
    async_setup_fragments(hass)
    await async_setup_frontend(hass)
    return True
