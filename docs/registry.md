# Registry API

## Overview

The component registry is a module-level singleton at `dj_design_system.component_registry`. It stores metadata about all discovered components and provides lookup and registration methods.

```python
from dj_design_system import component_registry
```

## Discovery

Discovery is triggered automatically by `DjangoDesignSystemConfig.ready()`. For each installed Django app, the registry imports `{app}.components` and walks any sub-packages, registering all concrete `BaseComponent` subclasses.

### Discovery Rules

- Looks for `{app}.components` as a module or package
- Recursively walks sub-packages within `components/`
- Registers classes that are subclasses of `BaseComponent`
- **Skips** classes with `Meta.abstract = True`
- **Skips** classes imported from other modules (only classes where `cls.__module__` matches the inspected module)
- **Skips** `BaseComponent`, `TagComponent`, and `BlockComponent` themselves (they are abstract)

## ComponentInfo

Each discovered component is stored as a `ComponentInfo` dataclass.

### Fields

| Field             | Type   | Description                                                         |
| ----------------- | ------ | ------------------------------------------------------------------- |
| `component_class` | `Type` | The component class itself                                          |
| `name`            | `str`  | Short name (auto-derived or from `Meta.name`)                       |
| `app_label`       | `str`  | The Django app label where the component was discovered             |
| `relative_path`   | `str`  | Dotted directory path within `components/` (e.g. `"cards.layouts"`) |

### Properties

| Property         | Type      | Description                                                                                                                     |
| ---------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `qualified_name` | `str`     | Fully qualified name: `{app_label}__{path}__{name}`                                                                             |
| `tag_type`       | `TagType` | `TagType.TAG` for TagComponent, `TagType.BLOCK` for BlockComponent. Raises `InvalidTagType` for direct BaseComponent subclasses |

## Lookup Methods

### `component_registry.list_all() -> list[ComponentInfo]`

Return all discovered components.

### `component_registry.list_by_app(app_label: str) -> list[ComponentInfo]`

Return all components belonging to the given app.

### `component_registry.get_by_name(name: str, app_label: str | None = None) -> ComponentInfo`

Look up a component by its short name. If `app_label` is provided, the search is scoped to that app.

Raises:

- `ComponentDoesNotExist` if no match is found
- `MultipleComponentsFound` if the name is ambiguous (use `app_label` to disambiguate)

### `component_registry.get_info(component_class: Type) -> ComponentInfo`

Look up the `ComponentInfo` for a given component class.

Raises `ComponentDoesNotExist` if the class is not registered.

## Template Tag Registration

### `component_registry.register_templatetags(library, app_label=None)`

Register discovered components as template tags on a Django `template.Library`.

- `library`: A `django.template.Library` instance
- `app_label`: When provided, only registers components from this app, and uniqueness is evaluated within this app's scope

See [Template Tag Auto-Registration](templatetags.md) for full details on naming and ambiguity handling.

## Exceptions

| Exception                 | When                                                         |
| ------------------------- | ------------------------------------------------------------ |
| `ComponentDoesNotExist`   | `get_by_name()` or `get_info()` finds no match               |
| `MultipleComponentsFound` | `get_by_name()` finds multiple components with the same name |

Both are importable from `dj_design_system.component_registry`.
