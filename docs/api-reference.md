# API reference

Auto-generated from source docstrings. For narrative usage guides see [Components & parameters](components.md) and [Organising components](organisation.md).

---

## Components

### `BaseComponent`

::: dj_design_system.components.BaseComponent
options:
show_root_heading: true
show_source: false
members: - get_params - get_template_context - validate_params - render - description - docstring

### `TagComponent`

::: dj_design_system.components.TagComponent
options:
show_root_heading: true
show_source: false
show_bases: true

### `BlockComponent`

::: dj_design_system.components.BlockComponent
options:
show_root_heading: true
show_source: false
show_bases: true

---

## Parameters

All parameter classes live in `dj_design_system.parameters` and can be imported from there directly.

```python
from dj_design_system.parameters import (
    StrParam,
    BoolParam,
    StrCSSClassParam,
    BoolCSSClassParam,
    ModelParam,
    UserParam,
)
```

### `BaseParam`

::: dj_design_system.parameters.base.BaseParam
options:
show_root_heading: true
show_source: false
members: - validate - docstring - get_extra_context

### `StrParam`

::: dj_design_system.parameters.base.StrParam
options:
show_root_heading: true
show_source: false
show_bases: true

### `BoolParam`

::: dj_design_system.parameters.base.BoolParam
options:
show_root_heading: true
show_source: false
show_bases: true

### `StrCSSClassParam`

::: dj_design_system.parameters.base.StrCSSClassParam
options:
show_root_heading: true
show_source: false
show_bases: true

### `BoolCSSClassParam`

::: dj_design_system.parameters.base.BoolCSSClassParam
options:
show_root_heading: true
show_source: false
show_bases: true

### `ModelParam`

::: dj_design_system.parameters.model.ModelParam
options:
show_root_heading: true
show_source: false
show_bases: true

### `UserParam`

::: dj_design_system.parameters.user.UserParam
options:
show_root_heading: true
show_source: false
show_bases: true

---

## Registry

### `ComponentRegistry`

::: dj_design_system.services.registry.ComponentRegistry
options:
show_root_heading: true
show_source: false
members: - list_all - list_by_app - get_by_name - autodiscover

### `ComponentInfo`

::: dj_design_system.data.ComponentInfo
options:
show_root_heading: true
show_source: false
members: - qualified_name - tag_type

---

## Exceptions

::: dj_design_system.services.registry.ComponentDoesNotExist
options:
show_root_heading: true
show_source: false

::: dj_design_system.services.registry.MultipleComponentsFound
options:
show_root_heading: true
show_source: false

::: dj_design_system.data.InvalidTagType
options:
show_root_heading: true
show_source: false
