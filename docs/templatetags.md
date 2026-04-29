# Template Tag Auto-Registration

## How It Works

When Django starts, `dj_design_system`'s `AppConfig.ready()` triggers `component_registry.autodiscover()`, which imports the `components` module from every installed app and registers all discovered `BaseComponent` subclasses (via `TagComponent` or `BlockComponent`).

Template tag registration happens when a templatetag library file calls `component_registry.register_templatetags(register)`. This is a lazy step — the components are already discovered, but they are registered on a specific `template.Library` at load time.

## Tag Naming

Each component gets two names:

### Short Name

Derived automatically from the class name, or set explicitly via `Meta.name`.

| Class Name          | Derived Short Name |
| ------------------- | ------------------ |
| `IconComponent`     | `icon`             |
| `MyFancyButton`     | `my_fancy_button`  |
| `HeroCardComponent` | `hero_card`        |

Override with `Meta.name`:

```python
class HeroCardComponent(TagComponent):
    class Meta:
        name = "hero"
```

### Qualified Name

Always of the form `{app_label}__{relative_path}__{name}`, using `__` as separator. The relative path is the dotted directory path within the app's `components/` package.

| Component Location                                                                | Qualified Name                |
| --------------------------------------------------------------------------------- | ----------------------------- |
| `myapp/components/icon.py` → `IconComponent`                                      | `myapp__icon`                 |
| `myapp/components/cards/info_card.py` → `InfoCardComponent`                       | `myapp__cards__info_card`     |
| `myapp/components/cards/layouts/hero.py` → `HeroCardComponent` (Meta.name="hero") | `myapp__cards__layouts__hero` |

Qualified names are always unique and always registered, regardless of ambiguity.

## Template Tag Libraries

### Central Library: `design_components`

Contains ALL components from ALL installed apps.

```html
{% load design_components %} {% icon "check" %} {% callout type="info" %}Hello{%
endcallout %} {% myapp__cards__layouts__hero %} {# qualified name always works
#}
```

### Per-App Libraries

Create a per-app library when you want scoped component access. Uniqueness is evaluated within the app's components only.

```python
# myapp/templatetags/components.py
from django import template
from dj_design_system import component_registry

register = template.Library()
component_registry.register_templatetags(register, app_label="myapp")
```

```html
{% load design_components %} {% icon "check" %}
```

**Scoping example**: If both `app_a` and `app_b` define a `ButtonComponent`, the global `design_components` library will register the one from whichever app appears last in `INSTALLED_APPS` as `{% button %}`. Both are always available via their qualified names: `{% app_a__button %}` and `{% app_b__button %}`.

## Name Clashes and Overriding

When two or more components share the same short name within a library's scope:

1. Each component is still registered with its **qualified name** (always works).
2. The short name is assigned to the **last-discovered component** — i.e. the one from the app that appears latest in `INSTALLED_APPS`.

This means you can intentionally override a component from an earlier app by defining a component with the same name in a later app. The qualified name is always available as an escape hatch.

### Controlling Override Order

Discovery order follows `INSTALLED_APPS` order. To override a component, place your app **after** the app you want to override:

```python
INSTALLED_APPS = [
    # ...
    "design_system_defaults",   # defines ButtonComponent
    "my_project_components",    # also defines ButtonComponent — this one wins
]
```

With the above, `{% button %}` resolves to `my_project_components`'s version, while `{% design_system_defaults__button %}` still reaches the original.

## Registration Types

| Component Base Class       | Registration Method | Template Syntax                    |
| -------------------------- | ------------------- | ---------------------------------- |
| `TagComponent`             | `simple_tag`        | `{% icon "check" %}`               |
| `BlockComponent`           | `simple_block_tag`  | `{% callout %}...{% endcallout %}` |
| `BaseComponent` (directly) | Not registered      | Python-only usage                  |

---

## Media Tags

The `design_components` library provides four tags for injecting CSS and JS into your base templates. They are split into two groups: **component media** (driven by the component registry) and **global media** (driven by settings).

### `{% component_stylesheets %}`

Renders a `<link rel="stylesheet">` tag for every CSS file declared by any registered component. The list of paths is collected from `ComponentInfo.media.css` across all discovered components and deduplicated (preserving first-appearance order).

Place this tag in `<head>`, after any global stylesheets:

```django
{% load design_components %}
<head>
    {% render_bundle 'main' 'css' %}
    {% component_stylesheets %}
</head>
```

Produces output such as:

```html
<link rel="stylesheet" href="/static/myapp/components/button/button.css" />
<link rel="stylesheet" href="/static/myapp/components/callout/callout.css" />
```

Returns an empty string when no registered component declares any CSS.

### `{% component_scripts %}`

Renders a `<script src="...">` tag for every JS file declared by any registered component. Works identically to `component_stylesheets` but for JS paths from `ComponentInfo.media.js`.

Place this tag just before `</body>`, after any global scripts:

```django
{% load design_components %}
    {% render_bundle 'main' 'js' %}
    {% component_scripts %}
</body>
```

Produces output such as:

```html
<script src="/static/myapp/components/button/button.js"></script>
```

Returns an empty string when no registered component declares any JS.

### How component media is discovered

Each registered component can have CSS and JS files co-located with its Python module. The registry automatically detects files named after the component (e.g. `button.css` and `button.js` next to `button.py`) and records them on `ComponentInfo.media`. Components can also override `get_media()` to return a custom `ComponentMedia` instance.

See [components.md](components.md#component-media) for full details on declaring component media.

### `{% global_stylesheets %}` and `{% global_scripts %}`

These tags inject CSS and JS that is _not_ tied to specific components - for example, a shared webpack bundle or a single global stylesheet. They read from the `GLOBAL_CSS_BUNDLES`, `GLOBAL_CSS`, `GLOBAL_JS_BUNDLES`, and `GLOBAL_JS` keys of the `dj_design_system` settings dict.

| Tag                        | Settings keys read                 | Output          |
| -------------------------- | ---------------------------------- | --------------- |
| `{% global_stylesheets %}` | `GLOBAL_CSS_BUNDLES`, `GLOBAL_CSS` | `<link>` tags   |
| `{% global_scripts %}`     | `GLOBAL_JS_BUNDLES`, `GLOBAL_JS`   | `<script>` tags |

Webpack bundle entries are tuples of `(bundle_name,)` or `(bundle_name, config_name)` passed to `webpack_loader.utils.get_files`. These are silently skipped when `webpack_loader` is not installed.

Example settings:

```python
dj_design_system = {
    "GLOBAL_CSS_BUNDLES": [("main",)],
    "GLOBAL_CSS": ["myapp/extra.css"],
    "GLOBAL_JS_BUNDLES": [("main",)],
    "GLOBAL_JS": [],
}
```

### Recommended base template layout

```django
{% load design_components %}
<head>
    {% global_stylesheets %}
    {% component_stylesheets %}
</head>
<body>
    ...
    {% global_scripts %}
    {% component_scripts %}
</body>
```

## Gallery Library: `dj_design_system_gallery`

Tags used internally by the gallery UI. Load with:

```django
{% load dj_design_system_gallery %}
```

### `{% canvas %}...{% endcanvas %}`

Renders the enclosed content inside an isolated `<iframe>` using the
`srcdoc` attribute. The iframe includes the full CSS cascade (global →
canvas → component) so the rendered component appears exactly as it would
on a real page, without interference from gallery chrome.

```django
{% load design_components dj_design_system_gallery %}
{% canvas %}
    {% icon "check" %}
{% endcanvas %}
```

The tag automatically:

- Loads global CSS via the same logic as `{% global_stylesheets %}`
- Includes `canvas.css` for centering and background styles
- Reads component CSS/JS from the `_canvas_component_css` and
  `_canvas_component_js` context variables, if set
- Applies the `GALLERY_CANVAS_DEFAULT_BACKGROUND` setting
- Applies `GALLERY_CANVAS_HTML_ATTRS` to the `<html>` and `<body>` tags
- Sets `sandbox="allow-same-origin"` on the iframe

### `{{ depth|add_indent }}`

Filter that converts a navigation tree depth to a left-padding value in
pixels. Used by the sidebar navigation template.
