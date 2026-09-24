"""Fragments: named cards a component offers for embedding elsewhere.

The websocket half runs against a real Home Assistant and a real client, since
the frontend card will only ever see what comes over that connection.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant

from custom_components.lovelace_codegen import (
    ENTITY,
    NAME,
    EntitiesCard,
    Fragment,
    FragmentError,
    MarkdownCard,
    Params,
    register_fragments,
)
from custom_components.lovelace_codegen.fragments import FragmentRegistry

LIGHTS = {"dining": "switch.ks_dining", "study": "switch.ks_study"}


def killswitches(params: Params) -> EntitiesCard:
    names = [params["light"]] if "light" in params else sorted(LIGHTS)
    for name in names:
        if name not in LIGHTS:
            raise FragmentError(
                f"no light {name!r}; lights are {', '.join(sorted(LIGHTS))}"
            )
    return EntitiesCard(
        [{ENTITY: LIGHTS[name], NAME: name} for name in names], title="Killswitches"
    )


KILLSWITCHES = Fragment(
    "killswitches",
    killswitches,
    description="Motion killswitch per light",
    schema=vol.Schema({vol.Optional("light"): str}),
)
HELLO = Fragment("hello", lambda params: MarkdownCard("hello"))


class TestFragment:
    def test_renders_with_no_params(self) -> None:
        assert HELLO.render() == {"type": "markdown", "content": "hello"}

    def test_params_reach_the_builder(self) -> None:
        assert KILLSWITCHES.render({"light": "study"})["entities"] == [
            {ENTITY: "switch.ks_study", NAME: "study"}
        ]

    def test_default_schema_rejects_any_param(self) -> None:
        with pytest.raises(vol.Invalid):
            HELLO.render({"typo": 1})

    def test_schema_rejects_unknown_param(self) -> None:
        with pytest.raises(vol.Invalid):
            KILLSWITCHES.render({"lihgt": "study"})

    def test_builder_rejects_unknown_value(self) -> None:
        with pytest.raises(FragmentError, match="dining, study"):
            KILLSWITCHES.render({"light": "attic"})

    def test_describe_lists_params(self) -> None:
        assert KILLSWITCHES.describe() == {
            "name": "killswitches",
            "description": "Motion killswitch per light",
            "params": [{"name": "light", "required": False, "type": "str"}],
        }

    def test_describe_lists_enum_options(self) -> None:
        fragment = Fragment(
            "x",
            lambda params: MarkdownCard(""),
            schema=vol.Schema({vol.Required("light"): vol.In(["b", "a"])}),
        )
        assert fragment.describe()["params"] == [
            {"name": "light", "required": True, "type": "enum", "options": ["a", "b"]}
        ]


class TestFragmentRegistry:
    def test_registering_again_replaces_the_source(self) -> None:
        registry = FragmentRegistry()
        registry.register("motion", [HELLO, KILLSWITCHES])
        registry.register("motion", [KILLSWITCHES])

        assert registry.get("motion", "hello") is None
        assert registry.names("motion") == ["killswitches"]

    def test_sources_are_separate(self) -> None:
        registry = FragmentRegistry()
        registry.register("motion", [HELLO])
        registry.register("plants", [KILLSWITCHES])

        assert registry.get("plants", "hello") is None
        assert registry.get("motion", "hello") is HELLO

    def test_a_name_twice_is_an_error(self) -> None:
        with pytest.raises(ValueError, match="twice"):
            FragmentRegistry().register("motion", [HELLO, HELLO])


async def test_registering_without_setup_says_what_to_do(hass: HomeAssistant) -> None:
    with pytest.raises(RuntimeError, match="dependencies"):
        register_fragments(hass, "motion", [HELLO])


Send = Callable[..., Awaitable[dict[str, Any]]]


@pytest.fixture
async def send(integration: HomeAssistant, hass_ws_client: Any) -> Send:
    register_fragments(integration, "motion", [KILLSWITCHES, HELLO])
    client = await hass_ws_client(integration)

    async def _send(type_: str, **payload: Any) -> dict[str, Any]:
        await client.send_json_auto_id({"type": f"lovelace_codegen/{type_}", **payload})
        return await client.receive_json()

    return _send


class TestWebsocket:
    async def test_sends_the_rendered_card(self, send: Send) -> None:
        msg = await send(
            "fragment", source="motion", name="killswitches", params={"light": "dining"}
        )

        assert msg["success"]
        assert msg["result"] == {
            "type": "entities",
            "title": "Killswitches",
            "entities": [{ENTITY: "switch.ks_dining", NAME: "dining"}],
        }

    async def test_params_are_optional(self, send: Send) -> None:
        msg = await send("fragment", source="motion", name="hello")
        assert msg["result"] == {"type": "markdown", "content": "hello"}

    async def test_unknown_name_lists_what_exists(self, send: Send) -> None:
        msg = await send("fragment", source="motion", name="nope")

        assert not msg["success"]
        assert msg["error"]["code"] == "not_found"
        assert "hello, killswitches" in msg["error"]["message"]

    async def test_unknown_source(self, send: Send) -> None:
        msg = await send("fragment", source="plants", name="hello")

        assert msg["error"]["code"] == "not_found"
        assert "plants offers nothing" in msg["error"]["message"]

    async def test_bad_params(self, send: Send) -> None:
        msg = await send(
            "fragment", source="motion", name="killswitches", params={"lihgt": "x"}
        )

        assert msg["error"]["code"] == "invalid_format"
        assert "motion/killswitches" in msg["error"]["message"]

    async def test_builder_error(self, send: Send) -> None:
        msg = await send(
            "fragment", source="motion", name="killswitches", params={"light": "attic"}
        )

        assert msg["error"]["code"] == "invalid_format"
        assert "no light 'attic'" in msg["error"]["message"]

    async def test_lists_the_catalogue(self, send: Send) -> None:
        msg = await send("fragments")

        assert msg["success"]
        assert [f["name"] for f in msg["result"]["motion"]] == [
            "hello",
            "killswitches",
        ]
        assert msg["result"]["motion"][0]["params"] == []
