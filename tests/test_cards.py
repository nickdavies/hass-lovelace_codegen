"""Each card renders to the dict its YAML equivalent would parse to."""

from __future__ import annotations

import pytest

from custom_components.lovelace_codegen import (
    ENTITY,
    ButtonCard,
    ICON,
    NAME,
    Dashboard,
    EntitiesCard,
    FloorplanCard,
    GridCard,
    HistoryGraphCard,
    HorizontalStackCard,
    MarkdownCard,
    TileCard,
    VerticalStackCard,
    View,
    divider,
    floorplan_on_state,
    floorplan_style_set,
    floorplan_tap,
    floorplan_text_set,
    navigate,
)


class TestEntitiesCard:
    def test_bare_ids_become_entity_rows(self) -> None:
        card = EntitiesCard(["light.a", {ENTITY: "light.b", NAME: "B"}])
        assert card.render() == {
            "type": "entities",
            "entities": [{ENTITY: "light.a"}, {ENTITY: "light.b", NAME: "B"}],
        }

    def test_title_only_when_given(self) -> None:
        assert EntitiesCard([], title="T").render()["title"] == "T"
        assert "title" not in EntitiesCard([]).render()

    def test_divider_is_a_row(self) -> None:
        card = EntitiesCard(["light.a", divider(), "light.b"])
        assert card.render()["entities"][1] == {"type": "divider"}


class TestHistoryGraphCard:
    def test_renders_with_default_window(self) -> None:
        card = HistoryGraphCard(["sensor.a", {ENTITY: "sensor.b", NAME: "B"}])
        assert card.render() == {
            "type": "history-graph",
            "hours_to_show": 24,
            "entities": [{ENTITY: "sensor.a"}, {ENTITY: "sensor.b", NAME: "B"}],
        }

    def test_window_and_title(self) -> None:
        rendered = HistoryGraphCard(["sensor.a"], title="T", hours_to_show=6).render()
        assert rendered["hours_to_show"] == 6
        assert rendered["title"] == "T"


class TestMarkdownCard:
    def test_renders(self) -> None:
        assert MarkdownCard("hi").render() == {"type": "markdown", "content": "hi"}
        assert MarkdownCard("hi", title="T").render()["title"] == "T"


class TestStacks:
    def test_vertical_and_horizontal_nest_their_cards(self) -> None:
        inner = MarkdownCard("x")
        assert VerticalStackCard([inner]).render() == {
            "type": "vertical-stack",
            "cards": [inner.render()],
        }
        assert HorizontalStackCard([inner]).render() == {
            "type": "horizontal-stack",
            "cards": [inner.render()],
        }


class TestView:
    def test_defaults_to_a_panel_view(self) -> None:
        assert View("T", [MarkdownCard("x")]).render() == {
            "panel": True,
            "title": "T",
            "cards": [{"type": "markdown", "content": "x"}],
        }

    def test_optional_fields_only_when_given(self) -> None:
        rendered = View("T", [], panel=False, path="p", icon="mdi:x").render()
        assert rendered["panel"] is False
        assert rendered["path"] == "p"
        assert rendered[ICON] == "mdi:x"

    def test_a_subview_is_marked_and_can_name_its_back_path(self) -> None:
        rendered = View("T", [], path="p", subview=True, back_path="/d/main").render()
        assert rendered["subview"] is True
        assert rendered["back_path"] == "/d/main"

    def test_a_plain_view_says_nothing_about_subviews(self) -> None:
        rendered = View("T", []).render()
        assert "subview" not in rendered
        assert "back_path" not in rendered

    def test_back_path_needs_a_subview(self) -> None:
        with pytest.raises(ValueError, match="subview"):
            View("T", [], back_path="/d/main")


class TestGridCard:
    def test_renders_its_cards_in_columns(self) -> None:
        inner = MarkdownCard("x")
        assert GridCard([inner, inner], columns=4).render() == {
            "type": "grid",
            "columns": 4,
            "square": False,
            "cards": [inner.render(), inner.render()],
        }

    def test_title_only_when_given(self) -> None:
        assert GridCard([], title="T").render()["title"] == "T"
        assert "title" not in GridCard([]).render()


class TestButtonCard:
    def test_needs_no_entity(self) -> None:
        card = ButtonCard("Kitchen", "mdi:stove", tap_action=navigate("/d/kitchen"))
        assert card.render() == {
            "type": "button",
            NAME: "Kitchen",
            ICON: "mdi:stove",
            "tap_action": {"action": "navigate", "navigation_path": "/d/kitchen"},
        }

    def test_entity_only_when_given(self) -> None:
        assert ButtonCard("A", "mdi:x", entity="light.a").render()[ENTITY] == "light.a"
        assert ENTITY not in ButtonCard("A", "mdi:x").render()


class TestFloorplanCard:
    def test_a_plan_with_rules_and_startup_actions(self) -> None:
        card = FloorplanCard(
            "/local/plan.svg",
            rules=[floorplan_tap("area-kitchen", navigate("/d/kitchen"))],
            startup_actions=[
                floorplan_style_set(["area-pantry"], "--area-fill: grey"),
                floorplan_text_set("area-pantry-value", "empty"),
            ],
            title="Plan",
        )
        assert card.render() == {
            "type": "custom:floorplan-card",
            "full_height": False,
            "title": "Plan",
            "config": {
                "image": {"location": "/local/plan.svg", "cache": False},
                "rules": [
                    {
                        "element": "area-kitchen",
                        "tap_action": {
                            "action": "navigate",
                            "navigation_path": "/d/kitchen",
                        },
                    }
                ],
                "startup_action": [
                    {
                        "action": "call-service",
                        "service": "floorplan.style_set",
                        "service_data": {
                            "elements": ["area-pantry"],
                            "style": "--area-fill: grey",
                        },
                    },
                    {
                        "action": "call-service",
                        "service": "floorplan.text_set",
                        "service_data": {
                            "element": "area-pantry-value",
                            "text": "empty",
                        },
                    },
                ],
            },
        }

    def test_no_startup_actions_or_title_unless_given(self) -> None:
        card = FloorplanCard("/local/plan.svg").render()
        assert "title" not in card
        assert "startup_action" not in card["config"]
        assert "functions" not in card["config"]
        assert card["config"]["rules"] == []

    def test_state_rules_template_with_the_cards_functions(self) -> None:
        card = FloorplanCard(
            "/local/plan.svg",
            rules=[
                floorplan_on_state(
                    ["light.a", "light.b"],
                    [
                        floorplan_style_set(
                            ["area-a"], "${functions.fill(entities['light.a'])}"
                        )
                    ],
                )
            ],
            functions="return { fill: (s) => '' };",
        ).render()
        assert card["config"]["functions"] == ">\nreturn { fill: (s) => '' };"
        assert card["config"]["rules"] == [
            {
                "entities": ["light.a", "light.b"],
                "state_action": [
                    {
                        "action": "call-service",
                        "service": "floorplan.style_set",
                        "service_data": {
                            "elements": ["area-a"],
                            "style": "${functions.fill(entities['light.a'])}",
                        },
                    }
                ],
            }
        ]


class TestTileCard:
    def test_bare_tile_is_just_the_entity(self) -> None:
        assert TileCard("sensor.a").render() == {"type": "tile", ENTITY: "sensor.a"}

    def test_every_option(self) -> None:
        card = TileCard(
            "sensor.a",
            name="A",
            icon="mdi:x",
            vertical=True,
            tap_action=navigate("/d/a"),
        )
        assert card.render() == {
            "type": "tile",
            ENTITY: "sensor.a",
            NAME: "A",
            ICON: "mdi:x",
            "vertical": True,
            "tap_action": {"action": "navigate", "navigation_path": "/d/a"},
        }


class TestDashboard:
    def test_renders_its_views(self) -> None:
        assert Dashboard([View("A", []), View("B", [])]).render() == {
            "views": [
                {"panel": True, "title": "A", "cards": []},
                {"panel": True, "title": "B", "cards": []},
            ]
        }
