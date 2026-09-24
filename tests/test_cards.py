"""Each card renders to the dict its YAML equivalent would parse to."""

from __future__ import annotations

from custom_components.lovelace_codegen import (
    ENTITY,
    ICON,
    NAME,
    Dashboard,
    EntitiesCard,
    HistoryGraphCard,
    HorizontalStackCard,
    MarkdownCard,
    VerticalStackCard,
    View,
    divider,
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


class TestDashboard:
    def test_renders_its_views(self) -> None:
        assert Dashboard([View("A", []), View("B", [])]).render() == {
            "views": [
                {"panel": True, "title": "A", "cards": []},
                {"panel": True, "title": "B", "cards": []},
            ]
        }
