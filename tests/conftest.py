"""Fixtures — a real Home Assistant, via pytest-homeassistant-custom-component.

The cards are plain data and would test fine without it, but everything imports
Home Assistant's lovelace internals, and those are exactly what a Home Assistant
upgrade breaks. Better to find out here than in both components using this.
"""

from __future__ import annotations

import pathlib

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.loader import DATA_CUSTOM_COMPONENTS
from homeassistant.setup import async_setup_component

DOMAIN = "lovelace_codegen"


def _ensure_custom_components_path() -> None:
    """Put this project's custom_components on the namespace path.

    pytest-homeassistant-custom-component points the `custom_components`
    namespace package at its own testing_config directory, so without this the
    component under test is invisible.
    """
    import custom_components

    project_cc = str(pathlib.Path(__file__).parent.parent / "custom_components")
    if project_cc not in custom_components.__path__:
        custom_components.__path__.insert(0, project_cc)


@pytest.fixture
async def integration(hass: HomeAssistant) -> HomeAssistant:
    """Set up the component the way a dependent one would: with no config."""
    hass.data.pop(DATA_CUSTOM_COMPONENTS, None)
    _ensure_custom_components_path()

    assert await async_setup_component(hass, DOMAIN, {}), "setup failed"
    await hass.async_block_till_done()
    return hass
