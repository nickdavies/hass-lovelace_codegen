"""Building a Lovelace dashboard from code.

A tree of `Renderable`s renders to the same dict a YAML dashboard would parse
to. `GeneratedDashboard` registers one with Home Assistant as a YAML-mode
dashboard whose config comes from `render()` rather than from a file.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote

from homeassistant.components.lovelace import _register_panel
from homeassistant.components.lovelace.const import MODE_YAML
from homeassistant.components.lovelace.dashboard import LovelaceConfig
from homeassistant.helpers.json import json_bytes, json_fragment

DBT = Mapping[str, Any]

ENTITY = "entity"
NAME = "name"
ICON = "icon"


class Renderable(ABC):
    @abstractmethod
    def render(self) -> DBT:
        pass


class View(Renderable):
    def __init__(
        self,
        title: str,
        cards: Sequence[Renderable],
        panel: bool = True,
        path: str | None = None,
        icon: str | None = None,
        subview: bool = False,
        back_path: str | None = None,
    ) -> None:
        """A view, or with `subview` one left out of the tab bar.

        A subview is reached only by navigating to its `path`, and shows a back
        arrow in place of the tabs. The arrow goes back in browser history
        unless `back_path` names where it goes.
        """
        if back_path is not None and not subview:
            raise ValueError("back_path only applies to a subview")
        self.title = title
        self.cards = cards
        self.panel = panel
        self.path = path
        self.icon = icon
        self.subview = subview
        self.back_path = back_path

    def render(self) -> DBT:
        config: dict[str, Any] = {
            "panel": self.panel,
            "title": self.title,
            "cards": [card.render() for card in self.cards],
        }
        if self.path is not None:
            config["path"] = self.path
        if self.icon is not None:
            config["icon"] = self.icon
        if self.subview:
            config["subview"] = True
        if self.back_path is not None:
            config["back_path"] = self.back_path
        return config


class VerticalStackCard(Renderable):
    def __init__(self, cards: Sequence[Renderable]) -> None:
        self.cards = cards

    def render(self) -> DBT:
        return {
            "type": "vertical-stack",
            "cards": [card.render() for card in self.cards],
        }


class HorizontalStackCard(Renderable):
    def __init__(self, cards: Sequence[Renderable]) -> None:
        self.cards = cards

    def render(self) -> DBT:
        return {
            "type": "horizontal-stack",
            "cards": [card.render() for card in self.cards],
        }


class GridCard(Renderable):
    """Cards laid out `columns` across, in as many rows as they need."""

    def __init__(
        self,
        cards: Sequence[Renderable],
        columns: int = 3,
        square: bool = False,
        title: str | None = None,
    ) -> None:
        self.cards = cards
        self.columns = columns
        self.square = square
        self.title = title

    def render(self) -> DBT:
        config: dict[str, Any] = {
            "type": "grid",
            "columns": self.columns,
            "square": self.square,
            "cards": [card.render() for card in self.cards],
        }
        if self.title is not None:
            config["title"] = self.title
        return config


def navigate(path: str) -> dict[str, str]:
    """A tap action that opens `path`, such as a subview's."""
    return {"action": "navigate", "navigation_path": path}


class TileCard(Renderable):
    """One entity as a tile: its icon, name and state.

    With no `icon`, the tile shows the entity's own, so an entity whose icon
    follows its state shows that state at a glance.
    """

    def __init__(
        self,
        entity: str,
        name: str | None = None,
        icon: str | None = None,
        vertical: bool = False,
        tap_action: Mapping[str, Any] | None = None,
    ) -> None:
        self.entity = entity
        self.name = name
        self.icon = icon
        self.vertical = vertical
        self.tap_action = tap_action

    def render(self) -> DBT:
        config: dict[str, Any] = {"type": "tile", ENTITY: self.entity}
        if self.name is not None:
            config[NAME] = self.name
        if self.icon is not None:
            config[ICON] = self.icon
        if self.vertical:
            config["vertical"] = True
        if self.tap_action is not None:
            config["tap_action"] = dict(self.tap_action)
        return config


class ButtonCard(Renderable):
    """A labelled icon to tap, with or without an entity behind it.

    For something with no entity of its own to show, such as a room leading to
    its own page, where a tile would need one.
    """

    def __init__(
        self,
        name: str,
        icon: str,
        tap_action: Mapping[str, Any] | None = None,
        entity: str | None = None,
    ) -> None:
        self.name = name
        self.icon = icon
        self.tap_action = tap_action
        self.entity = entity

    def render(self) -> DBT:
        config: dict[str, Any] = {"type": "button", NAME: self.name, ICON: self.icon}
        if self.entity is not None:
            config[ENTITY] = self.entity
        if self.tap_action is not None:
            config["tap_action"] = dict(self.tap_action)
        return config


class EntitiesCard(Renderable):
    def __init__(
        self,
        entities: Sequence[str | dict[str, str]],
        title: str | None = None,
    ) -> None:
        self.title = title
        self.entities: list[dict[str, str]] = []
        for entity in entities:
            if isinstance(entity, dict):
                self.entities.append(entity)
            else:
                self.entities.append({ENTITY: entity})

    def render(self) -> DBT:
        config: dict[str, Any] = {
            "type": "entities",
            "entities": self.entities,
        }

        if self.title is not None:
            config["title"] = self.title

        return config


def divider() -> dict[str, str]:
    """A separator row inside an EntitiesCard."""
    return {"type": "divider"}


class MarkdownCard(Renderable):
    """Free text, for a card that needs to explain itself."""

    def __init__(self, content: str, title: str | None = None) -> None:
        self.content = content
        self.title = title

    def render(self) -> DBT:
        config: dict[str, Any] = {"type": "markdown", "content": self.content}
        if self.title is not None:
            config["title"] = self.title
        return config


class HistoryGraphCard(Renderable):
    def __init__(
        self,
        entities: Sequence[str | dict[str, str]],
        title: str | None = None,
        hours_to_show: int = 24,
    ) -> None:
        self.title = title
        self.hours_to_show = hours_to_show
        self.entities: list[dict[str, str]] = []
        for entity in entities:
            if isinstance(entity, dict):
                self.entities.append(entity)
            else:
                self.entities.append({ENTITY: entity})

    def render(self) -> DBT:
        config: dict[str, Any] = {
            "type": "history-graph",
            "hours_to_show": self.hours_to_show,
            "entities": self.entities,
        }
        if self.title is not None:
            config["title"] = self.title
        return config


def _percent(value: float) -> str:
    return f"{round(value, 2):g}%"


class PictureElement(Renderable):
    """One thing placed over a `PictureElementsCard`'s image.

    `left` and `top` place the element's centre, as percentages of the image's
    width and height, so it stays put however large the image is drawn. `style`
    adds CSS to the element, over the position.
    """

    def __init__(
        self,
        left: float,
        top: float,
        tap_action: Mapping[str, Any] | None = None,
        style: Mapping[str, str] | None = None,
    ) -> None:
        self.left = left
        self.top = top
        self.tap_action = tap_action
        self.style = style

    @abstractmethod
    def _config(self) -> dict[str, Any]:
        pass

    def render(self) -> DBT:
        config = self._config()
        if self.tap_action is not None:
            config["tap_action"] = dict(self.tap_action)
        config["style"] = {
            "left": _percent(self.left),
            "top": _percent(self.top),
            **(self.style or {}),
        }
        return config


class IconElement(PictureElement):
    """An icon on the image. It takes taps on and just around the icon."""

    def __init__(self, icon: str, left: float, top: float, **kwargs: Any) -> None:
        super().__init__(left, top, **kwargs)
        self.icon = icon

    def _config(self) -> dict[str, Any]:
        return {"type": "icon", ICON: self.icon}


class ImageElement(PictureElement):
    """A picture on the image, `width` percent of the image's width across.

    Its height follows from `aspect_ratio` (such as "16:9") when given, and
    from the picture's own proportions otherwise. The whole picture takes a tap.
    """

    def __init__(
        self,
        image: str,
        left: float,
        top: float,
        width: float,
        aspect_ratio: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(left, top, **kwargs)
        self.image = image
        self.width = width
        self.aspect_ratio = aspect_ratio

    def _config(self) -> dict[str, Any]:
        config: dict[str, Any] = {"type": "image", "image": self.image}
        if self.aspect_ratio is not None:
            config["aspect_ratio"] = self.aspect_ratio
        return config

    def render(self) -> DBT:
        config = super().render()
        config["style"] = {"width": _percent(self.width), **config["style"]}
        return config


# A picture with nothing in it.
TRANSPARENT = "data:image/svg+xml," + quote(
    "<svg xmlns='http://www.w3.org/2000/svg' width='1' height='1'/>"
)


def tap_area(
    left: float,
    top: float,
    width: float,
    height: float,
    aspect: float,
    tap_action: Mapping[str, Any],
) -> ImageElement:
    """An invisible rectangle to tap, centred at `left`, `top`, and `width` by
    `height` percent of the image. `aspect` is the image's width over its height.

    An icon takes taps only near itself, where a picture takes them anywhere on
    it, so a larger target is a transparent picture of the rectangle's shape.
    """
    return ImageElement(
        TRANSPARENT,
        left,
        top,
        width,
        aspect_ratio=f"{width * aspect / height:.4f}:1",
        tap_action=tap_action,
    )


class PictureElementsCard(Renderable):
    """An image with `elements` placed over it."""

    def __init__(
        self,
        image: str,
        elements: Sequence[Renderable],
        title: str | None = None,
    ) -> None:
        self.image = image
        self.elements = elements
        self.title = title

    def render(self) -> DBT:
        config: dict[str, Any] = {
            "type": "picture-elements",
            "image": self.image,
            "elements": [element.render() for element in self.elements],
        }
        if self.title is not None:
            config["title"] = self.title
        return config


class Dashboard(Renderable):
    def __init__(self, views: Sequence[View]) -> None:
        self.views = views

    def render(self) -> DBT:
        return {
            "views": [view.render() for view in self.views],
        }


class GeneratedDashboard(ABC):
    @property
    def mode(self) -> str:
        """Return mode of the lovelace config."""
        return str(MODE_YAML)

    @property
    @abstractmethod
    def title(self) -> str:
        """The title of the dashboard displayed on the sidebar"""

    @property
    @abstractmethod
    def url_path(self) -> str:
        """The url slug for the dashboard"""

    @property
    def show_in_sidebar(self) -> bool:
        return True

    @property
    def require_admin(self) -> bool:
        return False

    @property
    def config(self) -> Mapping[str, str | bool]:
        return {
            "mode": self.mode,
            "title": self.title,
            "show_in_sidebar": self.show_in_sidebar,
            "require_admin": self.require_admin,
        }

    @abstractmethod
    async def render(self) -> DBT:
        """Build the YAML for the dashboard"""

    def add_to_hass(self, hass: Any) -> None:
        url = self.url_path
        dashboard_config = self.config

        hass.data["lovelace"].dashboards[url] = ManualLovelaceYAML(
            hass,
            self.url_path,
            dashboard_config,
            self,
        )
        _register_panel(hass, url, dashboard_config["mode"], dashboard_config, False)


class ManualLovelaceYAML(LovelaceConfig):
    def __init__(
        self, hass: Any, url_path: str, config: Any, dashboard: GeneratedDashboard
    ) -> None:
        super().__init__(hass, url_path, config)
        self._dashboard = dashboard
        self._cache: DBT | None = None

    @property
    def mode(self) -> str:
        return str(self.config["mode"])

    async def async_get_info(self) -> Mapping[str, str | int]:
        config = await self.async_load(False)
        return {"mode": self.mode, "views": len(config["views"])}

    async def async_load(self, force: bool) -> Mapping[str, Any]:
        is_updated, config = await self._load_config(force)
        if is_updated:
            self._config_updated()
        return config

    async def async_json(self, force: bool) -> json_fragment:
        config = await self.async_load(force)
        return json_fragment(json_bytes(config))

    async def _load_config(self, force: bool) -> tuple[bool, DBT]:
        if self._cache is not None:
            return False, self._cache

        config = await self._dashboard.render()
        self._cache = config
        return True, config
