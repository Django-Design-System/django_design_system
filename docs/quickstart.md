# Quickstart

Full documentation lives at [fukalite.github.io/dj-design-system/](https://fukalite.github.io/dj-design-system/).

## Installation

Add `dj_design_system` to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    "dj_design_system",
    ...
]
```

### Static files (CSS and JS)

To serve co-located `.css` and `.js` files through Django's static files system, add `ComponentsStaticFinder` to `STATICFILES_FINDERS`:

```python
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "dj_design_system.finders.ComponentsStaticFinder",
]
```

This serves `.css` and `.js` files from each installed app's `components/` directory under the URL namespace `{app_label}/components/...`. Python files, HTML templates, and all other file types are never exposed as static assets.

### Template loader (HTML templates)

To use co-located `.html` templates for components, add `ComponentsTemplateLoader` to your `TEMPLATES` loader list. Because Django does not support mixing `APP_DIRS: True` with a custom `loaders` list, you must switch to an explicit loader configuration:

```python
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": False,  # must be False when loaders is set
        "OPTIONS": {
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
                "dj_design_system.loaders.ComponentsTemplateLoader",
            ],
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
```

Component auto-discovery happens automatically when Django starts up (via `AppConfig.ready()`).

## Creating a Tag Component

Tag components render a single HTML fragment. Create a file in your app's `components/` directory.

### Using a co-located HTML template (recommended)

Place a `.html` file next to the `.py` file with the same base name. Django's full template language is available — `{% if %}`, `{% for %}`, `{% load %}`, etc.:

```
myapp/components/
    badge.py
    badge.html
```

```python
# myapp/components/badge.py
from dj_design_system.components import TagComponent
from dj_design_system.parameters import StrParam, BoolCSSClassParam


class BadgeComponent(TagComponent):
    """A status badge."""

    label = StrParam("The badge text.")
    bold = BoolCSSClassParam(required=False, default=False)
```

```htmldjango
{# myapp/components/badge.html #}
<span class="badge {{ classes }}">{{ label }}</span>
```

### Using an inline format string

For simple components you can skip the HTML file and use `template_format_str` directly on the class. This uses Python's `format_html` rather than the Django template engine, so template tags are not available:

```python
class BadgeComponent(TagComponent):
    """A status badge."""

    template_format_str = "<span class='badge {classes}'>{label}</span>"
    label = StrParam("The badge text.")
    bold = BoolCSSClassParam(required=False, default=False)
```

Use it in a template:

```htmldjango
{% load design_components %}
{% badge label="New" %}
{% badge label="Active" bold=True %}
```

### Positional Arguments

Declare `Meta.positional_args` to allow positional syntax in the template tag:

```python
class BadgeComponent(TagComponent):
    label = StrParam("The badge text.")

    class Meta:
        positional_args = ["label"]
```

Now you can write:

```html
{% badge "New" %}
```

Instead of:

```html
{% badge label="New" %}
```

## Creating a Block Component

Block components wrap nested template content. The block body is automatically available as `content` in the template context — you do NOT need to declare it as a parameter.

```
myapp/components/
    card.py
    card.html
```

```python
# myapp/components/card.py
from dj_design_system.components import BlockComponent
from dj_design_system.parameters import StrParam


class CardComponent(BlockComponent):
    """A content card."""

    title = StrParam("Card heading.")

    class Meta:
        positional_args = ["title"]
```

```htmldjango
{# myapp/components/card.html #}
<div class="card {{ classes }}">
  <h3>{{ title }}</h3>
  {{ content }}
</div>
```

Use it in a template:

```htmldjango
{% load design_components %}
{% card "My Title" %}
  <p>This is the card body.</p>
{% endcard %}
```

## Loading Template Tags

There are two ways to load component template tags:

### Central library (all components from all apps)

```html
{% load design_components %}
```

### Per-app library

Create a `templatetags/components.py` in your app:

```python
from django import template
from dj_design_system import component_registry

register = template.Library()
component_registry.register_templatetags(register, app_label="myapp")
```

Then in templates:

```html
{% load design_components %}
```

## Component Discovery

Components are automatically discovered in any installed app that has a `components` module or package. The discovery rules are:

- Looks for `{app}.components` (a single file) or `{app}/components/` (a package)
- Recursively walks sub-packages within `components/`
- Registers any concrete `BaseComponent` subclass (via `TagComponent` or `BlockComponent`)
- Skips classes with `class Meta: abstract = True`
- Skips classes imported from other modules (only registers classes defined in that file)
