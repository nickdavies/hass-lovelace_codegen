# Lovelace codegen

Build Home Assistant Lovelace dashboards from Python instead of YAML. A custom
component can then generate its dashboard from its own config, so adding
something to the config doesn't also need a dashboard edit.

Used by [plant_care](https://github.com/nickdavies/hass-plant_care) and
[light_motion_profiles](https://github.com/nickdavies/hass-light_motion_profiles).

## Using it from another component

This is a custom component that does nothing on its own. It exists so that
several components can share one copy of the code.

1. Install it next to the component that uses it, as
   `custom_components/lovelace_codegen`.
2. List it in that component's `manifest.json`:

   ```json
   "dependencies": ["lovelace_codegen"]
   ```

3. Import from it:

   ```python
   from custom_components.lovelace_codegen import (
       DBT, Dashboard, EntitiesCard, GeneratedDashboard, View,
   )


   class MyDashboard(GeneratedDashboard):
       title = "Mine"
       url_path = "mine"

       async def render(self) -> DBT:
           return Dashboard([View("Main", [EntitiesCard(["light.kitchen"])])]).render()


   # in async_setup:
   MyDashboard().add_to_hass(hass)
   ```

The dashboard is rendered the first time it is opened and then cached until
Home Assistant restarts.

### Versions

Home Assistant loads exactly one copy of a custom component. Every component
that depends on this one runs against whichever version is installed, so a
breaking change here has to land in all of them together.

`GeneratedDashboard.add_to_hass` uses Home Assistant's private
`homeassistant.components.lovelace._register_panel`. The tests run it against
a real Home Assistant, so a release that changes it shows up here first.

## Development

Needs Python 3.14.2 or later: the tests run against the Home Assistant release
homelab deploys, pinned in `.github/workflows/ci.yml`.

```sh
pip install pytest pytest-homeassistant-custom-component==0.13.365 ruff==0.16.8
python -m pytest tests/ -c tests/pytest.ini
ruff check custom_components/ tests/ && ruff format --check custom_components/ tests/
```
