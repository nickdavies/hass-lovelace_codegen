"""Named pieces of a generated dashboard, for embedding in other dashboards.

A component registers fragments under its own name, its "source". Each one is a
function from a few parameters to a card. The frontend asks for one over the
websocket:

    {"type": "lovelace_codegen/fragment",
     "source": "light_motion_profiles", "name": "killswitches",
     "params": {"owner": "nick"}}

and gets back the rendered card config, the same dict the card would be in a
YAML dashboard. Nothing is cached: a fragment is a pure function of the
component's config and its parameters, cheap to build, and building it on every
request means a hand-written dashboard can never show a stale copy.

A component's own generated dashboard should be built from the same functions,
so the embedded pieces and the full page cannot drift apart.

`lovelace_codegen/fragments` lists everything registered with its parameters, so
a dashboard repo can check its references without a browser.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

import probatio
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN
from .lovelace import DBT, Renderable

Params = Mapping[str, Any]


class FragmentError(Exception):
    """A fragment cannot be built from these parameters.

    For a failure the caller can fix, such as naming a light that does not
    exist. The message is sent to the frontend as is, so it should say what was
    asked for and what would have been accepted.
    """


@dataclass(frozen=True)
class Fragment:
    """One card a component offers for embedding.

    `schema` validates the parameters before `build` sees them. The default
    accepts no parameters at all, so a misspelt one is an error rather than
    being silently ignored.
    """

    name: str
    build: Callable[[Params], Renderable]
    description: str = ""
    schema: probatio.Schema = field(default_factory=lambda: probatio.Schema({}))

    def render(self, params: Params | None = None) -> DBT:
        """Validate `params` and build the card.

        Raises `probatio.Invalid` for parameters the schema rejects and
        `FragmentError` for ones the builder does.
        """
        return self.build(self.schema(dict(params or {}))).render()

    def describe(self) -> dict[str, Any]:
        """The fragment and its params, in the field-list shape Home Assistant
        sends the frontend for a config flow's form."""
        return {
            "name": self.name,
            "description": self.description,
            "params": probatio.to_field_list(
                self.schema, custom_serializer=cv.custom_serializer
            ),
        }


class FragmentRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, dict[str, Fragment]] = {}

    def register(self, source: str, fragments: Iterable[Fragment]) -> None:
        """Set everything `source` offers, replacing what it offered before.

        Replacing rather than adding means a component that sets up again, on a
        reload, leaves no fragment behind that it no longer builds.
        """
        by_name: dict[str, Fragment] = {}
        for fragment in fragments:
            if fragment.name in by_name:
                raise ValueError(f"{source} registers {fragment.name!r} twice")
            by_name[fragment.name] = fragment
        self._sources[source] = by_name

    def get(self, source: str, name: str) -> Fragment | None:
        return self._sources.get(source, {}).get(name)

    def names(self, source: str) -> list[str]:
        return sorted(self._sources.get(source, {}))

    def describe(self) -> dict[str, list[dict[str, Any]]]:
        return {
            source: [by_name[name].describe() for name in sorted(by_name)]
            for source, by_name in sorted(self._sources.items())
        }


DATA_FRAGMENTS: HassKey[FragmentRegistry] = HassKey(f"{DOMAIN}_fragments")


def register_fragments(
    hass: HomeAssistant, source: str, fragments: Iterable[Fragment]
) -> None:
    """Offer `fragments` for embedding, under `source` (normally the domain)."""
    registry = hass.data.get(DATA_FRAGMENTS)
    if registry is None:
        raise RuntimeError(
            f"{source} registered fragments before lovelace_codegen was set up; "
            'list "lovelace_codegen" in its manifest\'s "dependencies"'
        )
    registry.register(source, fragments)


@callback
def async_setup_fragments(hass: HomeAssistant) -> None:
    hass.data[DATA_FRAGMENTS] = FragmentRegistry()
    websocket_api.async_register_command(hass, websocket_fragment)
    websocket_api.async_register_command(hass, websocket_fragments)


@websocket_api.websocket_command(
    {
        probatio.Required("type"): f"{DOMAIN}/fragment",
        probatio.Required("source"): str,
        probatio.Required("name"): str,
        probatio.Optional("params", default={}): dict,
    }
)
@callback
def websocket_fragment(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Send one rendered fragment."""
    registry = hass.data[DATA_FRAGMENTS]
    source, name = msg["source"], msg["name"]

    fragment = registry.get(source, name)
    if fragment is None:
        offered = ", ".join(registry.names(source)) or "nothing"
        connection.send_error(
            msg["id"],
            websocket_api.ERR_NOT_FOUND,
            f"No fragment {source}/{name}; {source} offers {offered}",
        )
        return

    try:
        config = fragment.render(msg["params"])
    except probatio.Invalid as err:
        connection.send_error(
            msg["id"],
            websocket_api.ERR_INVALID_FORMAT,
            f"Bad params for {source}/{name}: {err}",
        )
        return
    except FragmentError as err:
        connection.send_error(
            msg["id"], websocket_api.ERR_INVALID_FORMAT, f"{source}/{name}: {err}"
        )
        return

    connection.send_result(msg["id"], config)


@websocket_api.websocket_command({probatio.Required("type"): f"{DOMAIN}/fragments"})
@callback
def websocket_fragments(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Send every registered fragment with its parameters, by source."""
    connection.send_result(msg["id"], hass.data[DATA_FRAGMENTS].describe())
