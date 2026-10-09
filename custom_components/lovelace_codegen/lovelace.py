"""Building a Lovelace dashboard from code.

A tree of `Renderable`s renders to the same dict a YAML dashboard would parse
to. `GeneratedDashboard` registers one with Home Assistant as a YAML-mode
dashboard whose config comes from `render()` rather than from a file.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any

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


def floorplan_style_set(elements: Sequence[str], style: str) -> dict[str, Any]:
    """An action setting CSS on elements of a `FloorplanCard`'s plan, by id."""
    return {
        "action": "call-service",
        "service": "floorplan.style_set",
        "service_data": {"elements": list(elements), "style": style},
    }


def floorplan_text_set(element: str, text: str) -> dict[str, Any]:
    """An action writing text into an element of a `FloorplanCard`'s plan."""
    return {
        "action": "call-service",
        "service": "floorplan.text_set",
        "service_data": {"element": element, "text": text},
    }


def floorplan_on_state(
    entities: Sequence[str], actions: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """A rule running actions whenever any of entities changes state, and once
    the plan loads.

    The actions' service data can be ha-floorplan templates, `${...}`, which
    read the entities' states as `entities['<entity id>']` and the card's
    `functions` as `functions`.
    """
    return {
        "entities": list(entities),
        "state_action": [dict(action) for action in actions],
    }


def floorplan_tap(element: str, tap_action: Mapping[str, Any]) -> dict[str, Any]:
    """A rule making an element of a `FloorplanCard`'s plan, and everything in
    it, tappable.

    `tap_action` is any card action, such as `navigate`'s, and ha-floorplan
    runs it. Its `navigate` leaves out the history state a subview's back arrow
    reads, so the arrow would go to the dashboard's first view instead of back.
    A `navigate` is therefore followed by a `fire-dom-event`, on which this
    component's frontend adds that state (frontend/fragment-card.js). A page
    without that script still navigates; only its back arrow is off.
    """
    action = dict(tap_action)
    if action.get("action") != "navigate" or action.get("navigation_replace"):
        return {"element": element, "tap_action": action}
    return {
        "element": element,
        "tap_action": [action, {"action": "fire-dom-event", "codegen_navigated": True}],
    }


class FloorplanCard(Renderable):
    """An SVG plan that rules draw on, by the ids of its elements.

    The custom card is ha-floorplan (github.com/ExperienceLovelace/ha-floorplan),
    which has to be installed for this to show. `rules` are its rules, as built
    by `floorplan_tap`, `floorplan_on_state` or by hand; `startup_actions` run
    once, when the plan has loaded, such as `floorplan_style_set` to colour
    elements that no entity's state decides. `functions` is JavaScript, the body
    of a function returning an object of helpers for the rules' templates. The
    plan is fetched afresh on every load rather than cached, so a regenerated one
    shows straight away.
    """

    def __init__(
        self,
        image: str,
        rules: Sequence[Mapping[str, Any]] = (),
        startup_actions: Sequence[Mapping[str, Any]] = (),
        title: str | None = None,
        functions: str | None = None,
    ) -> None:
        self.image = image
        self.rules = rules
        self.startup_actions = startup_actions
        self.title = title
        self.functions = functions

    def render(self) -> DBT:
        config: dict[str, Any] = {
            "image": {"location": self.image, "cache": False},
            "rules": [dict(rule) for rule in self.rules],
        }
        if self.functions is not None:
            # ha-floorplan runs a string starting `>` as code.
            config["functions"] = f">\n{self.functions}"
        if self.startup_actions:
            config["startup_action"] = [dict(a) for a in self.startup_actions]
        card: dict[str, Any] = {
            "type": "custom:floorplan-card",
            "full_height": False,
            "config": config,
        }
        if self.title is not None:
            card["title"] = self.title
        return card


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
