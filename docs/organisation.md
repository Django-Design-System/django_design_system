# Organising components

Django Design System places very few constraints on how you structure your component library. The rules that do exist are driven by Python's own module system: components live inside an app's `components` module (either a package or a single file), and sub-packages must have an `__init__.py` to be traversed.

Everything else is up to you.

---

## Principle: start as simple as you can

You do not need folders, sub-packages, or abstract bases to get started. The simplest valid setup is a single file:

```
myapp/
    components.py   ← all your components live here
```

The [`demo_single`](https://github.com/Django-Design-System/django_design_system/tree/main/example_project/demo_single) app in the example project uses this pattern. Both `PillComponent` and `ChipComponent` live in one `components.py`:

```python
# demo_single/components.py

class PillComponent(TagComponent):
    """A pill-shaped label."""
    text = StrParam("The pill text.")
    class Meta:
        positional_args = ["text"]

class ChipComponent(TagComponent):
    """A compact chip label."""
    text = StrParam("The chip text.")
    class Meta:
        positional_args = ["text"]
```

The gallery shows both components under the `demo_single` app with no extra configuration.

---

## Principle: grow into folders naturally

When a single file becomes unwieldy, split into a package. Each sub-module becomes a folder in the gallery navigation automatically:

```
myapp/
    components/
        __init__.py
        button.py       → gallery: myapp / Button
        badge.py        → gallery: myapp / Badge
        card/
            __init__.py
            info_card.py  → gallery: myapp / Card / Info card
            hero_card.py  → gallery: myapp / Card / Hero card
```

The [`demo_components`](https://github.com/Django-Design-System/django_design_system/tree/main/example_project/demo_components) app demonstrates this. `ButtonComponent` and `AlertComponent` sit at the top level; `InfoCardComponent` and `HeroCardComponent` live inside `components/card/`.

There is no required depth — use as many or as few levels as makes sense for your library.

---

## Principle: leaf-folder collapsing keeps things tidy

When the deepest folder name matches the component name inside it, the folder is automatically collapsed. The component appears directly under the parent rather than inside a redundant nested node.

For example, if you have:

```
components/
    icon/
        __init__.py
        icon.py   ← defines IconComponent
```

The gallery shows _Icon_ under the app root, not _Icon → Icon_. This lets you co-locate a component's file alongside its CSS and JS without polluting the navigation.

The [`demo_nav`](https://github.com/Django-Design-System/django_design_system/tree/main/example_project/demo_nav) app uses this pattern for its `elements/icon/` component.

---

## Principle: abstract bases share structure without cluttering the gallery

Declare `Meta.abstract = True` on any class you want excluded from discovery:

```python
# demo_components/components/card/abstract_card.py

class AbstractCardComponent(TagComponent):
    """Abstract base for all card components."""
    class Meta:
        abstract = True
```

Concrete subclasses inherit from it and appear in the gallery normally. The abstract base is invisible to users browsing the gallery.

---

## Principle: multiple apps are first-class

There is no "main" app. Every installed Django app is treated equally. The gallery groups components by app label, and the navigation tree has one root node per app.

The [`demo_extra`](https://github.com/Django-Design-System/django_design_system/tree/main/example_project/demo_extra) app demonstrates what happens when two apps define a component with the same name (`button`). Both appear in the gallery under their respective apps. In templates, you disambiguate with the app-qualified syntax:

```html
{% demo_components:button "Primary action" %} {% demo_extra:button "Secondary
action" %}
```

---

## Principle: markdown documentation lives with the code

Place `.md` files anywhere inside your `components/` directory. They are discovered alongside components and appear as document nodes in the navigation:

- `index.md` — attaches to the parent folder or component as its documentation page.
- Any other `.md` file — appears as a standalone document node.

The [`demo_nav`](https://github.com/Django-Design-System/django_design_system/tree/main/example_project/demo_nav) app uses both patterns:

```
demo_nav/components/
    design_guidelines.md   → standalone doc at the app root
    elements/
        index.md           → attached to the Elements folder
        icon/
            accessibility.md  → standalone doc inside the icon folder
```

This means narrative documentation lives next to the components it describes, in version control, without any separate docs infrastructure.

---

## Principle: co-locate CSS and JS with the component

Place `.css` and `.js` files in the same directory as the component module. They are automatically discovered and served by `ComponentsStaticFinder` under `{app_label}/components/...`.

For additional assets that are not co-located (e.g. a shared vendor library), declare a standard Django `Media` class:

```python
class RichButtonComponent(TagComponent):
    class Media:
        css = ["demo_components/components/rich_button_extras.css"]
```

Both auto-discovered and explicitly declared assets are merged — one does not suppress the other.

---

## Summary

| Pattern                         | When to use                                                           |
| ------------------------------- | --------------------------------------------------------------------- |
| Single `components.py`          | Small apps, prototyping, simple component sets                        |
| Flat `components/` package      | Medium libraries, no sub-grouping needed                              |
| Nested sub-packages             | Large libraries, logical groupings (forms, navigation, data display…) |
| Abstract base classes           | Shared structure across related components                            |
| Markdown files in `components/` | Narrative docs, design guidelines, accessibility notes                |
| Multiple apps                   | Separate teams, design system layers, versioned sub-libraries         |
