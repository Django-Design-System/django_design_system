# Component Gallery

The gallery provides a browsable UI for all registered components, with a
tree-view navigation sidebar built from the filesystem structure.

> **See it live:** A static snapshot of the example component gallery is deployed at
> [django-design-system.github.io/django_design_system/gallery/](https://django-design-system.github.io/django_design_system/gallery/).
> Note that HTMX-powered interactions (live canvas previews) are not available in the
> static snapshot — run the example project locally with `just demo` for the full
> interactive experience.

## Setup

Include the gallery URLs in your project:

```python
from django.urls import include, path

urlpatterns = [
    path("dds/", include("dj_design_system.urls")),
]
```

## URL Structure

All gallery pages live under a single prefix:

| URL                  | Description                           |
| -------------------- | ------------------------------------- |
| `/dds/`              | Gallery index                         |
| `/dds/<app>/`        | App root (folder listing or index.md) |
| `/dds/<app>/<path>/` | Component, document, or folder        |

The gallery determines the type of page to render (component, markdown
document, or folder listing) by looking up the path in the navigation tree —
no URL prefixes are needed to distinguish node types.

## Navigation Tree

The sidebar navigation is built automatically from:

1. **Registered components** — discovered from each app's `components/` package.
2. **Markdown files** — discovered from the same directories.

**Important:** every directory under `components/` must be a proper Python
package (contain an `__init__.py` file) for component auto-discovery to
traverse into it. Without `__init__.py`, `pkgutil.walk_packages` will skip
the directory and components inside it will not appear in the gallery.

### Leaf-folder collapsing

When the deepest folder name matches the component name, the folder is
collapsed. For example, `elements/icon/component.py` appears as _Icon_ under
_Elements_, not _Elements → Icon → Icon_.

### Markdown conventions

| File            | Behaviour                                          |
| --------------- | -------------------------------------------------- |
| `index.md`      | Attached to the parent folder or component node.   |
| Any other `.md` | Appears as a standalone document node in the tree. |

Case is ignored for `index.md` (e.g. `INDEX.MD` works too).

### Labels

Node labels are derived from the slug using sentence case:
`info_card` → _Info card_, `hero-banner` → _Hero banner_. App labels follow
the same rule but are rendered uppercase in the sidebar via CSS.

#### Overriding labels with `verbose_name`

Both apps and components can declare an explicit display label that takes
precedence over the auto-derived one:

**Apps** — set `verbose_name` on the `AppConfig`:

```python
class MyAppConfig(AppConfig):
    name = "my_app"
    verbose_name = "My design system"
```

**Components** — set `verbose_name` on the inner `Meta` class:

```python
class ButtonComponent(TagComponent):
    template_format_str = "<button>{label}</button>"
    label = StrParam("The button label")

    class Meta:
        verbose_name = "Action button"
```

The `verbose_name` is used in the sidebar navigation, breadcrumbs, and
all other display contexts. In the sidebar, app labels are rendered
uppercase via CSS regardless of the `verbose_name`.

### Icons

The navigation sidebar displays SVG icons for node types:

- **Components** — a 3D box/package icon
- **Documents** — a page-with-lines icon
- **Folders** — a disclosure chevron (via `<details>`)

Icons are rendered via CSS `mask-image` with inline SVG data URIs (no
external dependencies or icon libraries).

## Component Pages

A component page has two panes:

### Documentation pane (primary)

Rendered in this order:

1. **Docstring** — the component class docstring, if present.
2. **Usage examples** — minimal and bigger (maximal) template tag usage
   with syntax-highlighted code blocks. Each example includes a small live
   preview iframe so the rendered result is visible inline.
3. **Parameters table** — name, type, required, default, choices, and
   description for each parameter.
4. **Markdown** — content from `index.md` in the component's directory, if
   present.

Each usage preview has a subtle link icon that switches to the sandbox
pane. URLs with the `#pane-sandbox` hash fragment open the sandbox
directly; the fragment stays in sync when switching panes via the header
toggle on narrow viewports.

### Sandbox pane

A live preview of the component rendered inside an **iframe canvas**. The
iframe provides full CSS/JS isolation from the gallery chrome — the
component is rendered in its own HTML document with the correct cascade:

1. Global CSS (`{% global_stylesheets %}`)
2. Canvas layout CSS (centering, padding, backgrounds)
3. Component-specific CSS

A **toolbar** above the canvas provides:

- **Background picker** — choose from all configured background colours.
- **Viewport** — constrain the canvas to a preset width (Small mobile 320 px,
  Large mobile 414 px, Tablet 768 px, Desktop 1024 px, Full HD 1920 px,
  Ultrawide 2560 px) or leave it responsive. Viewports wider than the pane are scaled down to fit, just like
  browser DevTools responsive mode, so media queries still fire at the true
  width.
- **Zoom control** — scale the canvas from 25 % to 200 %.
- **Box model outline** — toggle a colour-coded outline that visualises
  element boundaries (orange outlines), padding areas (green tint), and
  the component root content area (blue tint).
- **Measure** — hover over any element to see its margin (orange), padding
  (green), and content area (blue) dimensions with pixel labels.
- **RTL** — toggle right-to-left text direction on the canvas to test
  bidirectional layout support.

Default parameter values are chosen automatically:

- If the parameter has a `default`, that value is used.
- If the parameter has `choices`, the first choice is used.
- For required string parameters without a default, the parameter name is
  used as placeholder text.
- `BlockComponent` subclasses receive `"Sample content"` as their content.

#### Canvas backgrounds

The canvas background defaults to the value of
`GALLERY_CANVAS_DEFAULT_BACKGROUND` (default: `"light-grey"`). Users can
switch backgrounds via the toolbar in the sandbox pane or via the `bg`
query parameter (e.g. `?bg=dark-grey`).

Built-in backgrounds: `white`, `light-grey`, `dark-grey`, `black`,
`checkerboard`.

To add project-specific backgrounds without replacing the built-in set,
use `GALLERY_CANVAS_EXTRA_BACKGROUNDS`. Each entry is a dict with
`value`, `color`, and optionally `label`:

```python
dj_design_system = {
    "GALLERY_CANVAS_EXTRA_BACKGROUNDS": {
        "brand-blue": {"color": "#e6ebf0", "label": "Brand Blue"},
    },
    "GALLERY_CANVAS_DEFAULT_BACKGROUND": "brand-blue",
}
```

Extra backgrounds are merged into the built-in set in the toolbar.
If a key in `GALLERY_CANVAS_EXTRA_BACKGROUNDS` matches a built-in key,
it will override the built-in entry.

To replace the built-in set entirely, set `GALLERY_CANVAS_BACKGROUNDS`
to a dict of `{slug: {"label": ..., "color": ...}}` entries.

#### Canvas HTML attributes

Some CSS frameworks (e.g. GOV.UK Frontend) scope their styles to specific
classes on the `<html>` or `<body>` element. Use
`GALLERY_CANVAS_HTML_ATTRS` to add these attributes to the canvas iframe's
document:

```python
dj_design_system = {
    "GALLERY_CANVAS_HTML_ATTRS": {
        "html": {"class": "govuk-template"},
        "body": {"class": "govuk-template__body"},
    },
}
```

## Live Demos in Markdown

Markdown files (e.g. `index.md` in a component folder) can embed live
component previews using fenced `canvas` blocks:

````markdown
```canvas
{% icon "check" size="large" %}
```
````

Block components work too — put the content between the opening and
closing tags:

````markdown
```canvas
{% callout type="warning" %}Watch out!{% endcallout %}
```
````

The syntax inside the block is identical to the template tag syntax shown
in the Usage section of each component page — you can copy and paste
directly.

Each canvas block renders as a widget with:

- A **live preview** iframe (basic mode, auto-height).
- A **syntax-highlighted code block** showing the template tag.
- A small icon toggle in the bottom-right corner to switch between
  preview only, code only, or both (default).

Invalid syntax renders as a red error message. When `DEBUG = True`, the
original source is shown alongside the error.

## Syntax Highlighting

All fenced code blocks in documentation pages receive Pygments syntax
highlighting with a dark (Monokai) theme. The gallery automatically
detects Django template syntax (`{%` or `{{`) in untagged or
`py`/`python`-tagged fenced blocks and highlights them using the
`html+django` lexer.

To explicitly request Django template highlighting, use the
`html+django` language tag:

````markdown
```html+django
{% icon "check" size="large" %}
```
````

### Customising the highlight style

The Pygments style can be changed via the `GALLERY_CODEHILITE_STYLE`
setting. Set it to any [Pygments style name](https://pygments.org/styles/)
or to an empty string to disable highlighting entirely:

```python
dj_design_system = {
    "GALLERY_CODEHILITE_STYLE": "dracula",  # or "" to disable
}
```

Highlight colours are defined as CSS custom properties in
`gallery-highlight.css`. Override the `--hl-palette-*` variables for
palette changes, or the `--hl-*` semantic variables for finer control:

```css
:root {
  --hl-palette-keyword: #569cd6; /* change keyword colour */
  --hl-string: #ce9178; /* override just the string token */
}
```

## Settings

All settings are configured via the `dj_design_system` dictionary in
your Django settings module:

```python
from dj_design_system.types import NodeType

dj_design_system = {
    "ENABLE_GALLERY": True,
    "GALLERY_IS_PUBLIC": True,
    "DESIGN_SYSTEM_NAME": "Django Design System",
    "GALLERY_NAV_ORDER": [NodeType.FOLDER, NodeType.COMPONENT, NodeType.DOCUMENT],
}
```

| Setting                             | Type                      | Default                                                    | Description                                                 |
| ----------------------------------- | ------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------- |
| `ENABLE_GALLERY`                    | `bool`                    | `True`                                                     | Enable or disable the gallery entirely.                     |
| `GALLERY_IS_PUBLIC`                 | `bool`                    | `True`                                                     | When `False`, requires the `can_view_gallery` perm.         |
| `DESIGN_SYSTEM_NAME`                | `str`                     | `"Django Design System"`                                   | Display name shown in the gallery header.                   |
| `GALLERY_NAV_ORDER`                 | `list[NodeType]` or `str` | `[NodeType.FOLDER, NodeType.COMPONENT, NodeType.DOCUMENT]` | Controls the sort order of nodes in the sidebar.            |
| `GALLERY_CANVAS_DEFAULT_BACKGROUND` | `str`                     | `"light-grey"`                                             | Default background for the sandbox canvas.                  |
| `GALLERY_CANVAS_BACKGROUNDS`        | `dict`                    | `BUILTIN_CANVAS_BACKGROUNDS`                               | Dict of canvas backgrounds (replaces built-ins).            |
| `GALLERY_CANVAS_EXTRA_BACKGROUNDS`  | `dict`                    | `{}`                                                       | Extra backgrounds merged into the built-in set.             |
| `GALLERY_CANVAS_HTML_ATTRS`         | `dict`                    | `{}`                                                       | Extra attributes for the canvas `<html>` and `<body>` tags. |
| `GALLERY_CODEHILITE_STYLE`          | `str`                     | `"monokai"`                                                | Pygments style for code highlighting. `""` to disable.      |

### Navigation sort order

Within each level of the navigation tree, children are grouped by type
and then sorted alphabetically within each group. The `GALLERY_NAV_ORDER`
setting controls the order of those type groups.

The default value `[NodeType.FOLDER, NodeType.COMPONENT, NodeType.DOCUMENT]`
puts folders first, then components, then documents — matching the
convention used by most IDEs and file browsers.

Any permutation of the three `NodeType` values is valid:

```python
from dj_design_system.types import NodeType

# Documents first, then components, then folders
dj_design_system = {
    "GALLERY_NAV_ORDER": [NodeType.DOCUMENT, NodeType.COMPONENT, NodeType.FOLDER],
}
```

To ignore type grouping entirely and sort all nodes alphabetically by
label, use the string `"alphabetical"`:

```python
dj_design_system = {
    "GALLERY_NAV_ORDER": "alphabetical",
}
```

### Access control

By default, the gallery is public. To restrict access, set
`GALLERY_IS_PUBLIC = False` and assign the
`dj_design_system.can_view_gallery` permission to appropriate users.
