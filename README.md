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

### Fragments: cards for other dashboards

A generated dashboard is all or nothing. To put one of its cards on a
hand-written dashboard too, register the function that builds it as a
fragment:

```python
import probatio

from custom_components.lovelace_codegen import (
    EntitiesCard, Fragment, FragmentError, Params, register_fragments,
)


def killswitches(params: Params) -> EntitiesCard:
    if params["owner"] not in OWNERS:
        raise FragmentError(f"no owner {params['owner']!r}")
    ...


# in async_setup, after loading config:
register_fragments(hass, DOMAIN, [
    Fragment(
        "killswitches",
        killswitches,
        description="Motion killswitch per light",
        schema=probatio.Schema({probatio.Required("owner"): str}),
    ),
])
```

Build the component's own `GeneratedDashboard` from the same functions, so the
full page and the embedded pieces cannot disagree.

Two websocket commands serve them:

- `lovelace_codegen/fragment` with `source`, `name` and optional `params`
  returns the rendered card config. Nothing is cached, so it is always current.
  An unknown fragment is a `not_found` error that lists what the source offers.
  Parameters the schema rejects, or a `FragmentError` from the builder, are an
  `invalid_format` error with the reason.
- `lovelace_codegen/fragments` lists every fragment by source, with its
  parameters in the field-list shape Home Assistant uses for config flow forms
  (`probatio.to_field_list`), so a dashboard repo can check its references in
  CI.

The schema defaults to accepting no parameters, so a misspelt one is an error
rather than being ignored. Registering a source again replaces everything it
offered before.

### The fragment card

This component serves a card that shows a fragment, and lists it as a dashboard
resource itself, so a dashboard needs no resource entry for it:

```yaml
type: custom:codegen-fragment
source: light_motion_profiles
fragment: light_config
params:
  light: dining
```

It fetches the card config over `lovelace_codegen/fragment` once, then hands it
to Home Assistant's own card factory. A failed fetch shows the error in place of
the card.

### Floor plan taps

`floorplan_tap` runs its action through Home Assistant's own action handler
rather than ha-floorplan's, the way a built-in card's tap is run. ha-floorplan
navigates without the history state a subview's back arrow reads, so a page
opened from a plan would go "back" to its dashboard's first view instead of to
the plan. The tap is fired as ha-floorplan's `fire-dom-event`, and a script
this component lists as a dashboard resource hands it to Home Assistant.

### A component's own cards

The cards here model Home Assistant's own. A component that needs a custom card
keeps it: the JS, and a `Renderable` subclass that renders its config. That
nests in stacks, views and fragments like any card here. To load the JS, serve
it from the component's setup:

```python
from pathlib import Path

from custom_components.lovelace_codegen import async_serve_card

await async_serve_card(hass, f"/{DOMAIN}/my-card.js", Path(__file__).parent / "my-card.js")
```

It is served, and listed among the dashboard resources with a content hash in
its URL, so a dashboard needs no resource entry and always gets the version that
matches the component.

The list is Home Assistant's own: this component answers `lovelace/resources`,
the websocket command the frontend fetches resources with, with Home Assistant's
resources and then the served cards. In YAML or storage resource mode alike, and
"Reload resources" keeps them. A card is not added to the frontend page's own
list of modules (`add_extra_js_url`) instead: that list is in the HTML page,
which the service worker and the companion app cache, so a phone reopening on a
cached page loads the cards that page listed, at the versions it listed. The
resource list is fetched afresh every time the app starts.

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
