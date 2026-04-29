# Django Design System

**A reusable Django app for building, documenting, and shipping component libraries.**

Write your UI components as Django-native classes that look and work like Models or Forms. Django Design System auto-discovers them, renders live interactive previews in sandboxed iframes, generates templatetag usage examples from your parameter definitions, and builds a fully-searchable navigation gallery — all from your existing code and docstrings, with no configuration required.

---

## What a component looks like

A component is a Python class. Declare its parameters, its HTML template, and its docstring — that's it.

```python
# myapp/components/button.py
from dj_design_system.components import TagComponent
from dj_design_system.parameters import StrParam, StrCSSClassParam, BoolCSSClassParam


class ButtonComponent(TagComponent):
    """A configurable button with size and variant modifiers."""
    label = StrParam("The button label.")
    variant = StrCSSClassParam(
        "Visual variant.",
        required=False,
        default="primary",
        choices=["primary", "secondary", "danger"],
    )
    disabled = BoolCSSClassParam("Renders the button as disabled.", required=False)

    template_format_str = "<button class='btn {classes}'>{label}</button>"

    class Meta:
        positional_args = ["label"]
```

Use it in any Django template — no manual registration, no YAML:

```html
{% load design_components %} {% button "Save changes" %} {% button "Delete"
variant="danger" disabled=True %}
```

The gallery generates the templatetag syntax automatically and shows a live preview:

![Gallery preview showing the button component with its live iframe preview and generated tag signature](https://github.com/Django-Design-System/django_design_system/raw/main/docs/assets/gallery-preview.png)

**[Browse the demo gallery →](https://django-design-system.github.io/django_design_system/gallery/)**

---

## Key features

**Auto-discovery** — components are found and registered automatically when Django starts. No registration calls, no config files.

**Inline HTML templates** — components use a `template_format_str` string rather than separate template files. CSS classes from `StrCSSClassParam` and `BoolCSSClassParam` parameters are injected automatically into the `{classes}` slot.

**Rich parameter types** — `StrParam`, `BoolParam`, `StrCSSClassParam`, `BoolCSSClassParam`, `ModelParam`, `UserParam`. Parameters are self-documenting: their descriptions, types, defaults, and choices feed directly into the gallery.

**Block components** — use `BlockComponent` for components that wrap arbitrary template content.

**Media co-location** — place `.css` and `.js` files next to a component module and they are automatically discovered and served. Declare additional assets via a standard Django `Media` class.

**Flexible organisation** — nest components in sub-packages, share abstract bases, use a single-file `components.py` for small apps, or spread across deeply nested folders. See [Organising components](organisation.md).

**Multi-app** — register components across multiple Django apps. When a name is ambiguous, templates use an app-qualified syntax: `{% myapp:button "Click" %}`.

**Markdown documentation** — place `index.md` or any other `.md` file alongside your components for narrative documentation that appears in the gallery.

---

## Where to go next

| I want to…                                       | Go to                                                                                                  |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| See components in action                         | [Demo gallery](https://django-design-system.github.io/django_design_system/gallery/)                   |
| Install and create my first component            | [Quickstart](quickstart.md)                                                                            |
| Learn all parameter types                        | [Components & parameters](components.md)                                                               |
| Understand how discovery works                   | [Registry](registry.md)                                                                                |
| Configure the gallery UI                         | [Gallery](gallery.md)                                                                                  |
| Use components in templates                      | [Templatetags](templatetags.md)                                                                        |
| Understand how to structure my component library | [Organising components](organisation.md)                                                               |
| Browse the full API reference                    | [Parameters](api/parameters.md) · [Components](api/components.md)                                      |
| Contribute to the project                        | [Contributing](https://github.com/Django-Design-System/django_design_system/blob/main/CONTRIBUTING.md) |
